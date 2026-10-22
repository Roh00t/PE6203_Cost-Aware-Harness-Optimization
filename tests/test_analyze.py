"""Analysis policy tests: partial coverage, unknown costs and matched tasks."""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("analysis_under_test", ROOT / "scripts/analyze.py")
analysis = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analysis)


def row(config, task, reward=1.0, **changes):
    return {"config_id": config, "task": task, "family": "A", "trial": task + "__id",
            "reward": reward, "scored": True, "finished": True, "archived": False,
            "exception": None, "cost_source": "calls.jsonl", "usage_complete": True,
            "known_cost_table_usd": "0.001", "n_unknown_calls": 0,
            "harness_calls_cost_usd": "0", "harness_injected_cost_usd_estimate": "0",
            "overhead_estimate_complete": True, **changes}


def summarize(rows, expected=None, population=None, **kwargs):
    return analysis.aggregate(rows, expected or {"t1", "t2"}, population or {"A": 120},
                              samples=100, **kwargs)


def config(data, name):
    return next(r for r in data["summary"] if r["config_id"] == name)


def test_missing_tasks_and_absent_configs_are_not_zero():
    data = summarize([row("B0", "t1")])
    b0 = config(data, "B0")
    assert b0["mean_reward_observed"] == 1
    assert b0["mean_reward_full_split"] is None
    assert b0["status"] == "partial"
    assert b0["missing_or_unscored_task_ids"] == ["t2"]
    assert config(data, "V")["status"] == "not_run"
    assert config(data, "V")["mean_reward_observed"] is None
    assert config(data, "V")["cost_total_usd"] is None


def test_unscored_exception_does_not_lower_reward():
    data = summarize([row("B0", "t1"), row("B0", "t2", 0, scored=False, exception="RateLimitError")])
    assert config(data, "B0")["mean_reward_observed"] == 1
    assert config(data, "B0")["n_exception_trials"] == 1


def test_unknown_cost_remains_a_lower_bound():
    data = summarize([row("B0", "t1", usage_complete=False, n_unknown_calls=2)])
    b0 = config(data, "B0")
    assert b0["known_cost_total_usd"] == "0.001"
    assert b0["cost_total_usd"] is None
    assert b0["cost_is_lower_bound"] is True
    assert b0["n_unknown_calls"] == 2


def test_missing_log_is_not_proof_of_free_execution():
    data = summarize([row("B0", "t1", known_cost_table_usd=None,
                          cost_source="missing_log", usage_complete=False, n_unknown_calls=None)])
    b0 = config(data, "B0")
    assert b0["known_cost_total_usd"] is None
    assert b0["n_missing_call_logs"] == 1
    assert b0["usage_complete"] is False


def test_duplicate_active_tasks_require_explicit_repeat_policy():
    with pytest.raises(ValueError, match="Duplicate"):
        summarize([row("B0", "t1"), row("B0", "t1", 0)])


def test_repeats_are_averaged_within_task():
    data = summarize([row("B0", "t1"), row("B0", "t1", 0), row("B0", "t2", 0)], allow_repeats=True)
    assert config(data, "B0")["mean_reward_full_split"] == 0.25
    assert config(data, "B0")["n_scored_tasks"] == 2


def test_archived_rewards_excluded_but_spend_is_auditable():
    data = summarize([row("B0", "t1", 0), row("B0", "t1", 1, archived=True, scored=False)])
    b0 = config(data, "B0")
    assert b0["mean_reward_observed"] == 0
    assert b0["known_cost_total_usd"] == "0.001"
    assert b0["known_cost_including_archives_usd"] == "0.002"
    assert b0["n_archived_trials"] == 1


def test_paired_comparison_uses_only_common_tasks():
    rewards = {"V": {"t1": 1, "t2": 0, "t3": 0}, "B0": {"t1": 0, "t2": 0}}
    result = analysis.compare("V", "B0", rewards, samples=100, seed=42)
    assert result["n_paired_tasks"] == 2
    assert result["mean_reward_difference"] == 0.5
    assert result["wins"] == 1 and result["ties"] == 1
    assert result == analysis.compare("V", "B0", rewards, samples=100, seed=42)


def test_single_pair_has_no_confidence_interval():
    result = analysis.compare("V", "B0", {"V": {"t": 1}, "B0": {"t": 0}}, samples=100, seed=42)
    assert result["ci95_low"] is None and result["ci95_high"] is None


def test_family_weights_not_renormalized_when_family_missing():
    data = summarize([row("B0", "t1")], population={"A": 90, "B": 30})
    assert config(data, "B0")["family_reweighted_observed"] is None


def test_family_reweighting_uses_population_weights():
    data = summarize([row("B0", "t1", 1), row("B0", "t2", 0, family="B")], population={"A": 90, "B": 30})
    assert config(data, "B0")["mean_reward_full_split"] == 0.5
    assert config(data, "B0")["family_reweighted_observed"] == 0.75


def test_config_id_cannot_be_silently_overridden():
    data = {"agent_result": {"metadata": {"config_id": "H0+C1"}}}
    with pytest.raises(ValueError, match="disagrees"):
        analysis.identify_config(Path("result.json"), data, "B0")
    assert analysis.identify_config(Path("h0-c1/task/trial/result.json"), {}, None) == "H0+C1"


def test_load_trial_reads_complete_stock_trajectory(tmp_path):
    trial = tmp_path / "b0/t1__id"
    (trial / "agent").mkdir(parents=True)
    result_path = trial / "result.json"
    result_path.write_text(json.dumps({"task_name": "local/t1", "trial_name": "t1__id",
        "finished_at": "2026-10-22T00:00:00Z", "agent_info": {"model_info": {"name": "openai/gpt-oss-20b"}},
        "verifier_result": {"rewards": {"reward": 0.5}}}))
    (trial / "agent/mini-swe-agent.trajectory.json").write_text(json.dumps({"messages": [{
        "role": "assistant", "extra": {"response": {"model": "openai/gpt-oss-20b",
        "usage": {"prompt_tokens": 100, "completion_tokens": 20}}}}]}))
    pricing = ROOT / "configs/pricing.json"
    table = json.loads(pricing.read_text())
    loaded = analysis.load_trial(result_path, table, {"t1": {"family": "A"}}, {"t1"}, None, pricing)
    assert loaded["config_id"] == "B0"
    assert loaded["reward"] == 0.5
    assert loaded["usage_complete"] is True
    assert loaded["scored"] is True


def test_ablations_use_h0_not_b0():
    data = summarize([row("H0", "t1", 0), row("H0+C1", "t1", 1)])
    ablation = next(r for r in data["ablations"] if r["config_id"] == "H0+C1")
    assert ablation["reference"] == "H0"
    assert ablation["mean_reward_difference"] == 1
