"""Archived zero-call attempts and the explicit lower-bound frontier policy (eval pass 1)."""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


analysis = load("analysis_policy_under_test", "analyze.py")
pareto = load("pareto_policy_under_test", "plot_pareto.py")
PRICING = ROOT / "configs/pricing.json"
TABLE = json.loads(PRICING.read_text())


def crashed_stock_trial(root: Path) -> Path:
    """A B0 attempt whose agent crashed before any model call (empty message list)."""
    trial = root / "t1__id"
    (trial / "agent").mkdir(parents=True)
    result = trial / "result.json"
    result.write_text(json.dumps({
        "task_name": "local/t1", "trial_name": "t1__id", "finished_at": "2026-10-25T00:00:00Z",
        "agent_info": {"model_info": {"name": "openai/gpt-oss-20b"}},
        "exception_info": {"exception_type": "NonZeroAgentExitCodeError"},
        "verifier_result": {"rewards": {"reward": 0.0}}}))
    (trial / "agent/mini-swe-agent.trajectory.json").write_text(json.dumps({"messages": []}))
    return result


def test_archived_attempt_without_calls_is_recorded_not_fatal(tmp_path):
    result = crashed_stock_trial(tmp_path / "b0/t1.errored-20261025-235457")
    row = analysis.load_trial(result, TABLE, {"t1": {"family": "A"}}, {"t1"}, None, PRICING)
    assert row["archived"] is True and row["scored"] is False
    assert row["cost_source"] == "archived_no_calls"
    assert row["usage_complete"] is False and row["known_cost_table_usd"] is None


def test_active_trial_without_calls_still_fails_loudly(tmp_path):
    result = crashed_stock_trial(tmp_path / "b0/t1")
    with pytest.raises(ValueError, match="No model calls found"):
        analysis.load_trial(result, TABLE, {"t1": {"family": "A"}}, {"t1"}, None, PRICING)


def summary_row(config, reward, cost, *, complete):
    return {"config_id": config, "n_active_trials": 2, "n_attempted_tasks": 2, "n_scored_tasks": 2,
            "mean_reward_observed": reward, "usage_complete": complete,
            "mean_cost_per_attempted_task_usd": cost if complete else None,
            "known_cost_observed_usd": cost * 2, "n_unknown_calls": 0 if complete else 2,
            "scored_task_ids": ["t1", "t2"], "attempted_task_ids": ["t1", "t2"]}


DATA = {"metadata": {"expected_task_ids": ["t1", "t2"], "split": "eval"},
        "summary": [summary_row("B0", 0.1, 0.0007, complete=True),
                    summary_row("V", 0.16, 0.0012, complete=False),
                    summary_row("E", 0.17, 0.0014, complete=True)]}


def test_default_policy_keeps_lower_bounds_off_the_frontier():
    points, _ = pareto.prepare_points(DATA)
    v = next(p for p in points if p["config_id"] == "V")
    assert v["cost_is_lower_bound"] and not v["frontier_eligible"]
    assert pareto.frontier(points) == ["B0", "E"]


def test_include_policy_admits_lower_bounds_but_keeps_the_label():
    points, _ = pareto.prepare_points(DATA, "include")
    v = next(p for p in points if p["config_id"] == "V")
    assert v["cost_is_lower_bound"] and v["frontier_eligible"]
    assert pareto.frontier(points) == ["B0", "V", "E"]


def test_include_policy_still_excludes_coverage_gaps():
    gap = dict(summary_row("H0", 0.5, 0.0001, complete=False), scored_task_ids=["t1"])
    points, _ = pareto.prepare_points({**DATA, "summary": DATA["summary"] + [gap]}, "include")
    assert next(p for p in points if p["config_id"] == "H0")["frontier_eligible"] is False


def test_unknown_policy_is_rejected():
    with pytest.raises(ValueError, match="policy"):
        pareto.prepare_points(DATA, "assume_zero")
