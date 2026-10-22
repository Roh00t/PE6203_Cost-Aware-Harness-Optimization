#!/usr/bin/env python3
"""Price saved model calls, preserving unknown usage as incomplete cost.

Every JSONL row is an HTTP attempt, including retries. Known costs are lower
bounds whenever usage is incomplete; they are never silently reported as totals.
The adjacent trial result.json is cross-checked automatically when available.
"""
import argparse
import json
from decimal import Decimal
from pathlib import Path


def token_count(usage: dict, key: str) -> int | None:
    value = usage.get(key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"Invalid {key}: {value!r}")
    return value


def money(value) -> Decimal:
    if isinstance(value, bool):
        raise ValueError("Invalid monetary value")
    amount = Decimal(str(value))
    if not amount.is_finite() or amount < 0:
        raise ValueError("Monetary values must be finite and non-negative")
    return amount


def read_calls(path: Path) -> list[dict]:
    if path.suffix == ".jsonl":
        records = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        if any(not isinstance(record, dict) for record in records):
            raise ValueError("Each call log row must be a JSON object")
        return [{**record, "usage": record} for record in records]

    trajectory = json.loads(path.read_text())
    messages = trajectory.get("messages")
    if not isinstance(messages, list):
        raise ValueError("Expected a mini trajectory with a messages list")
    calls = []
    for message in messages:
        response = (message.get("extra") or {}).get("response")
        if response is None:
            if message.get("role") == "assistant":
                calls.append({"usage": None, "purpose": "agent"})
            continue
        if not isinstance(response, dict):
            raise ValueError("Saved response is not a readable JSON object")
        usage = response.get("usage")
        if usage is not None and not isinstance(usage, dict):
            raise ValueError("Saved usage must be a JSON object or null")
        calls.append({
            "usage": usage,
            "model": response.get("model"),
            "provider": response.get("provider"),
            "purpose": "agent",
        })
    return calls


def find_result(path: Path) -> Path | None:
    # Only inspect the trial next to agent/, never the outer job result.
    if path.parent.name == "agent":
        candidate = path.parent.parent / "result.json"
        if candidate.is_file():
            return candidate
    return None


def summarize(log: Path, *, model: str, provider: str,
              pricing: Path = Path("configs/pricing.json"),
              result_path: Path | None = None) -> dict:
    model = model.removeprefix("openrouter/")
    table = json.loads(pricing.read_text())
    price = table["models"][model]
    if price["provider"] != provider:
        raise ValueError("Provider does not match the price table")
    input_rate = money(price["prompt_usd_per_mtok"])
    output_rate = money(price["completion_usd_per_mtok"])
    calls = read_calls(log)
    if not calls:
        raise ValueError("No model calls found; this is not a zero-cost model run")

    known = harness_calls = injected_cost = injected_tokens = Decimal("0")
    input_total = output_total = unknown = missing_provider = 0
    attribution_missing = 0
    for call in calls:
        observed_provider = call.get("provider")
        if observed_provider and observed_provider != provider:
            raise ValueError(f"Unexpected provider: {observed_provider}")
        expected_provider = call.get("provider_expected")
        if expected_provider and expected_provider != provider:
            raise ValueError(f"Unexpected expected provider: {expected_provider}")
        observed_model = call.get("model")
        if observed_model and observed_model.removeprefix("openrouter/") != model:
            raise ValueError(f"Unexpected model: {observed_model}")
        missing_provider += int(not observed_provider)
        usage = call.get("usage") or {}
        prompt = token_count(usage, "prompt_tokens")
        completion = token_count(usage, "completion_tokens")
        # Preserve any known token count, but price only complete usage pairs.
        input_total += prompt if prompt is not None else 0
        output_total += completion if completion is not None else 0
        if prompt is None or completion is None:
            unknown += 1
            continue
        cost = (prompt * input_rate + completion * output_rate) / Decimal(1000000)
        recorded = call.get("cost_table_usd")
        if recorded is not None and abs(cost - money(recorded)) > Decimal("0.000000001"):
            raise ValueError("Recorded call cost does not match token pricing")
        known += cost
        purpose = call.get("purpose") or "agent"
        if purpose.startswith("harness:"):
            harness_calls += cost
        origins = call.get("prompt_chars_by_origin")
        if origins is None:
            attribution_missing += 1
        else:
            if not isinstance(origins, dict) or any(
                type(value) is not int or value < 0 for value in origins.values()
            ):
                raise ValueError("Invalid prompt_chars_by_origin")
            total_chars = sum(origins.values())
            if total_chars:
                # Separate from harness call cost: these categories may overlap.
                estimate = Decimal(prompt) * Decimal(origins.get("harness", 0)) / total_chars
                injected_tokens += estimate
                injected_cost += estimate * input_rate / Decimal(1000000)
            elif prompt:
                attribution_missing += 1

    complete = unknown == 0
    result_path = result_path or find_result(log)
    metadata = {}
    trial = {}
    checked = None
    delta = None
    if result_path is not None:
        trial = json.loads(result_path.read_text())
        metadata = (trial.get("agent_result") or {}).get("metadata") or {}
        recorded = metadata.get("known_cost_table_usd")
        if recorded is not None:
            delta = known - money(recorded)
            checked = abs(delta) < Decimal("0.01")
            if not checked:
                raise ValueError(f"Trial known cost mismatch: difference {delta} USD")
        flag = metadata.get("usage_complete")
        if flag is not None and type(flag) is not bool:
            raise ValueError("Invalid usage_complete in trial metadata")
        if flag is True and unknown:
            raise ValueError("Trial says usage is complete but call log contains unknown usage")
        if flag is False:
            complete = False

    return {
        "source_log": str(log),
        "model_priced_as": model,
        "provider_priced_as": provider,
        "calls": len(calls),
        "n_known_calls": len(calls) - unknown,
        "n_unknown_calls": unknown,
        "usage_complete": complete,
        "prompt_tokens": input_total,
        "completion_tokens": output_total,
        "known_cost_table_usd": str(known),
        "cost_table_usd": str(known) if complete else None,
        "cost_is_lower_bound": not complete,
        "harness_calls_cost_usd": str(harness_calls),
        "harness_injected_prompt_tokens_estimate": str(injected_tokens),
        "harness_injected_cost_usd_estimate": str(injected_cost),
        "calls_without_prompt_attribution": attribution_missing,
        "overhead_estimate_complete": complete and attribution_missing == 0,
        "overhead_policy": "Character-share input estimate; do not add overlapping overhead categories",
        "calls_without_recorded_provider": missing_provider,
        "pricing_snapshot": table["snapshot_date"],
        "cache_policy": "All prompt tokens charged at listed input rate",
        "result_json": str(result_path) if result_path else None,
        "result_known_cost_table_usd": metadata.get("known_cost_table_usd"),
        "cost_crosscheck_passed": checked,
        "cost_crosscheck_delta_usd": str(delta) if delta is not None else None,
        "config_id": metadata.get("config_id") or calls[0].get("config_id"),
        "task": trial.get("task_name") or calls[0].get("task_id"),
        "trial": trial.get("trial_name") or calls[0].get("trial_id"),
        "reward": ((trial.get("verifier_result") or {}).get("rewards") or {}).get("reward"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path)
    parser.add_argument("--model", required=True)
    parser.add_argument("--provider", required=True)
    parser.add_argument("--pricing", type=Path, default=Path("configs/pricing.json"))
    parser.add_argument("--result", type=Path, help="Trial result.json; otherwise autodetected next to agent/")
    args = parser.parse_args()
    try:
        report = summarize(args.log, model=args.model, provider=args.provider,
                           pricing=args.pricing, result_path=args.result)
    except (ValueError, KeyError, OSError, ArithmeticError) as error:
        parser.exit(1, f"Cost collection failed: {error}\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
