"""Offline regression tests for complete, incomplete and reconciled call costs."""
import json
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
COLLECTOR = ROOT / "scripts/collect_costs.py"
MODEL = "openai/gpt-oss-20b"
PROVIDER = "Darkbloom"


def run_collector(log, *, provider=PROVIDER, extra=()):
    return subprocess.run([
        sys.executable, str(COLLECTOR), str(log), "--model", MODEL,
        "--provider", provider, "--pricing", str(ROOT / "configs/pricing.json"),
        *extra,
    ], capture_output=True, text=True)


def write_jsonl(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(record) + "\n" for record in records))


def known(**overrides):
    return {"model": MODEL, "provider": PROVIDER, "purpose": "agent",
            "prompt_tokens": 100, "completion_tokens": 20, **overrides}


def report(log, **kwargs):
    result = run_collector(log, **kwargs)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_complete_calls_and_harness_overhead(tmp_path):
    log = tmp_path / "calls.jsonl"
    write_jsonl(log, [known(), known(prompt_tokens=200, completion_tokens=10,
                                  provider=None, purpose="harness:repair")])
    data = report(log)
    assert data["calls"] == 2
    assert data["prompt_tokens"] == 300
    assert data["completion_tokens"] == 30
    assert Decimal(data["cost_table_usd"]) == Decimal("0.0000081")
    assert Decimal(data["harness_calls_cost_usd"]) == Decimal("0.0000045")
    assert data["usage_complete"] is True
    assert data["n_unknown_calls"] == 0
    assert data["calls_without_recorded_provider"] == 1


def test_retry_is_not_dropped_or_priced_as_free(tmp_path):
    log = tmp_path / "calls.jsonl"
    write_jsonl(log, [known(call_idx=1), known(call_idx=2, prompt_tokens=None,
                 completion_tokens=None, error="RateLimitError", retries=1),
                 known(call_idx=3, retries=2)])
    data = report(log)
    assert data["calls"] == 3
    assert data["n_known_calls"] == 2
    assert data["n_unknown_calls"] == 1
    assert data["usage_complete"] is False
    assert data["cost_table_usd"] is None
    assert data["cost_is_lower_bound"] is True
    assert Decimal(data["known_cost_table_usd"]) == Decimal("0.0000072")


def test_all_unknown_calls_have_no_exact_total(tmp_path):
    log = tmp_path / "calls.jsonl"
    write_jsonl(log, [known(prompt_tokens=None, completion_tokens=None)])
    data = report(log)
    assert data["n_unknown_calls"] == 1
    assert Decimal(data["known_cost_table_usd"]) == 0
    assert data["cost_table_usd"] is None
    assert data["usage_complete"] is False


@pytest.mark.parametrize("usage", [None, {}, {"prompt_tokens": 100}])
def test_incomplete_stock_usage_is_preserved(tmp_path, usage):
    log = tmp_path / "trajectory.json"
    log.write_text(json.dumps({"messages": [{"role": "assistant", "extra": {
        "response": {"model": MODEL, "usage": usage}}}]}))
    data = report(log)
    assert data["calls"] == 1
    assert data["n_unknown_calls"] == 1
    assert data["cost_table_usd"] is None


def test_stock_format_error_response_is_included(tmp_path):
    log = tmp_path / "trajectory.json"
    log.write_text(json.dumps({"messages": [{"role": "user", "extra": {
        "response": {"model": MODEL, "usage": {"prompt_tokens": 100,
        "completion_tokens": 20, "completion_tokens_details": {
            "reasoning_tokens": 10}, "prompt_tokens_details": {"cached_tokens": 50}}}}}]}))
    data = report(log)
    assert data["calls"] == 1
    assert Decimal(data["cost_table_usd"]) == Decimal("0.0000036")
    assert data["calls_without_recorded_provider"] == 1


def test_missing_saved_assistant_response_is_unknown(tmp_path):
    log = tmp_path / "trajectory.json"
    log.write_text(json.dumps({"messages": [{"role": "system", "content": "test"},
                                           {"role": "assistant", "content": "done"}]}))
    assert report(log)["n_unknown_calls"] == 1


@pytest.mark.parametrize("field,value", [
    ("provider", "Venice"), ("provider_expected", "Venice"),
    ("model", "openai/gpt-oss-120b"),
    ("prompt_tokens", -1), ("completion_tokens", True),
    ("prompt_tokens", "100"), ("cost_table_usd", 1),
])
def test_invalid_identity_usage_or_recorded_cost_rejected(tmp_path, field, value):
    log = tmp_path / "calls.jsonl"
    write_jsonl(log, [known(**{field: value})])
    assert run_collector(log).returncode != 0


def test_provider_must_match_price_table(tmp_path):
    log = tmp_path / "calls.jsonl"
    write_jsonl(log, [known()])
    result = run_collector(log, provider="Venice")
    assert result.returncode != 0
    assert "Provider does not match the price table" in result.stderr


def test_empty_file_is_not_a_free_run(tmp_path):
    log = tmp_path / "calls.jsonl"
    write_jsonl(log, [])
    assert run_collector(log).returncode != 0


def trial_log(tmp_path, metadata):
    log = tmp_path / "task__trial/agent/calls.jsonl"
    write_jsonl(log, [known(), known(prompt_tokens=None, completion_tokens=None)])
    result = {"task_name": "local/example", "trial_name": "example__test",
              "agent_result": {"metadata": metadata},
              "verifier_result": {"rewards": {"reward": 0.5}}}
    (log.parent.parent / "result.json").write_text(json.dumps(result))
    return log


def test_auto_crosscheck_uses_trial_metadata(tmp_path):
    log = trial_log(tmp_path, {"config_id": "H0", "known_cost_table_usd": 0.0000036,
                               "usage_complete": False})
    data = report(log)
    assert data["cost_crosscheck_passed"] is True
    assert Decimal(data["cost_crosscheck_delta_usd"]) == 0
    assert data["usage_complete"] is False
    assert data["config_id"] == "H0"
    assert data["reward"] == 0.5


def test_crosscheck_mismatch_is_an_error(tmp_path):
    log = trial_log(tmp_path, {"known_cost_table_usd": 0.1, "usage_complete": False})
    result = run_collector(log)
    assert result.returncode != 0
    assert "Trial known cost mismatch" in result.stderr


def test_complete_metadata_cannot_hide_unknown_calls(tmp_path):
    log = trial_log(tmp_path, {"known_cost_table_usd": 0.0000036, "usage_complete": True})
    assert run_collector(log).returncode != 0


def test_character_share_overhead_is_input_only(tmp_path):
    log = tmp_path / "calls.jsonl"
    write_jsonl(log, [known(prompt_chars_by_origin={"system": 75, "harness": 25})])
    data = report(log)
    assert Decimal(data["harness_injected_prompt_tokens_estimate"]) == 25
    assert Decimal(data["harness_injected_cost_usd_estimate"]) == Decimal("0.00000045")
    assert data["overhead_estimate_complete"] is True
    assert Decimal(data["harness_calls_cost_usd"]) == 0


def test_missing_attribution_does_not_claim_complete_overhead(tmp_path):
    log = tmp_path / "calls.jsonl"
    write_jsonl(log, [known()])
    data = report(log)
    assert data["calls_without_prompt_attribution"] == 1
    assert data["overhead_estimate_complete"] is False
