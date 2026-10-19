"""Regression tests for pricing saved trajectories and harness call logs."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
COLLECTOR = ROOT / "scripts" / "collect_costs.py"
PRICING = ROOT / "configs" / "pricing.json"
MODEL = "openai/gpt-oss-20b"
PROVIDER = "Darkbloom"


def run_collector(log: Path, *, model: str = MODEL, provider: str = PROVIDER):
    return subprocess.run(
        [
            sys.executable,
            str(COLLECTOR),
            str(log),
            "--model",
            model,
            "--provider",
            provider,
            "--pricing",
            str(PRICING),
        ],
        capture_output=True,
        check=False,
        text=True,
    )


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.write_text("".join(json.dumps(record) + "\n" for record in records), encoding="utf-8")


def test_prices_call_log_and_separates_harness_overhead(tmp_path: Path) -> None:
    log = tmp_path / "calls.jsonl"
    write_jsonl(
        log,
        [
            {
                "prompt_tokens": 100,
                "completion_tokens": 20,
                "provider": PROVIDER,
                "purpose": "agent",
            },
            {
                "prompt_tokens": 200,
                "completion_tokens": 10,
                "provider": None,
                "purpose": "harness:repair",
            },
        ],
    )

    result = run_collector(log)

    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["calls"] == 2
    assert report["prompt_tokens"] == 300
    assert report["completion_tokens"] == 30
    assert report["cost_table_usd"] == "0.0000081"
    assert report["harness_calls_cost_usd"] == "0.0000045"
    assert report["calls_without_recorded_provider"] == 1


def test_prices_saved_mini_swe_trajectory(tmp_path: Path) -> None:
    trajectory = tmp_path / "trajectory.json"
    trajectory.write_text(
        json.dumps(
            {
                "messages": [
                    {
                        "role": "assistant",
                        "extra": {
                            "response": {
                                "model": MODEL,
                                "provider": None,
                                "usage": {"prompt_tokens": 100, "completion_tokens": 20},
                            }
                        },
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    result = run_collector(trajectory)

    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["calls"] == 1
    assert report["cost_table_usd"] == "0.0000036"
    assert report["calls_without_recorded_provider"] == 1


def test_rejects_null_token_usage_in_harness_log(tmp_path: Path) -> None:
    log = tmp_path / "calls.jsonl"
    write_jsonl(
        log,
        [
            {
                "prompt_tokens": None,
                "completion_tokens": None,
                "provider": None,
                "purpose": "agent",
                "error": "RateLimitError",
            }
        ],
    )

    result = run_collector(log)

    assert result.returncode != 0
    assert "Missing or invalid prompt_tokens: None" in result.stderr


def test_rejects_unexpected_recorded_provider(tmp_path: Path) -> None:
    log = tmp_path / "calls.jsonl"
    write_jsonl(
        log,
        [
            {
                "prompt_tokens": 100,
                "completion_tokens": 20,
                "provider": "Venice",
                "purpose": "agent",
            }
        ],
    )

    result = run_collector(log)

    assert result.returncode != 0
    assert "Unexpected provider: Venice" in result.stderr


def test_rejects_provider_that_disagrees_with_price_table(tmp_path: Path) -> None:
    log = tmp_path / "calls.jsonl"
    write_jsonl(log, [{"prompt_tokens": 1, "completion_tokens": 1}])

    result = run_collector(log, provider="Venice")

    assert result.returncode != 0
    assert "Provider does not match the price table" in result.stderr


def test_rejects_empty_call_log_as_not_a_zero_cost_run(tmp_path: Path) -> None:
    log = tmp_path / "calls.jsonl"
    log.write_text("", encoding="utf-8")

    result = run_collector(log)

    assert result.returncode != 0
    assert "No model calls found; this is not a zero-cost model run" in result.stderr


@pytest.mark.parametrize(
    ("bad_usage", "message"),
    [
        (None, "Saved response has no token usage"),
        ({}, "Missing or invalid prompt_tokens: None"),
        ({"prompt_tokens": 1}, "Missing or invalid completion_tokens: None"),
    ],
)
def test_rejects_incomplete_saved_trajectory_usage(tmp_path: Path, bad_usage, message: str) -> None:
    trajectory = tmp_path / "trajectory.json"
    trajectory.write_text(
        json.dumps(
            {
                "messages": [
                    {
                        "role": "assistant",
                        "extra": {
                            "response": {
                                "model": MODEL,
                                "usage": bad_usage,
                            }
                        },
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    result = run_collector(trajectory)

    assert result.returncode != 0
    assert message in result.stderr
