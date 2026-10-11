#!/usr/bin/env python3
"""Price one mini-swe-agent trajectory or harness calls.jsonl.

The model and provider arguments identify the expected endpoint.
Missing usage is an error, never silently treated as zero cost.
"""
import argparse
import json
from decimal import Decimal
from pathlib import Path


def token_count(usage, key):
    value = usage.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"Missing or invalid {key}: {value!r}")
    return value


def read_calls(path):
    if path.suffix == ".jsonl":
        calls = []
        for line in path.read_text().splitlines():
            if line.strip():
                record = json.loads(line)
                calls.append({
                    "usage": record,
                    "model": record.get("model"),
                    "provider": record.get("provider"),
                    "purpose": record.get("purpose", "agent"),
                })
        return calls

    trajectory = json.loads(path.read_text())
    messages = trajectory.get("messages")
    if not isinstance(messages, list):
        raise ValueError("Expected a mini trajectory with a messages list")

    calls = []
    for message in messages:
        response = (message.get("extra") or {}).get("response")
        if response is None:
            if message.get("role") == "assistant":
                raise ValueError("Assistant message has no saved response")
            continue
        if not isinstance(response, dict):
            raise ValueError("Saved response is not a readable JSON object")
        usage = response.get("usage")
        if not isinstance(usage, dict):
            raise ValueError("Saved response has no token usage")
        calls.append({
            "usage": usage,
            "model": response.get("model"),
            "provider": response.get("provider"),
            "purpose": "agent",
        })
    return calls


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path)
    parser.add_argument("--model", required=True)
    parser.add_argument("--provider", required=True)
    parser.add_argument("--pricing", type=Path, default=Path("configs/pricing.json"))
    args = parser.parse_args()

    table = json.loads(args.pricing.read_text())
    price = table["models"][args.model]
    if price["provider"] != args.provider:
        raise ValueError("Provider does not match the price table")

    calls = read_calls(args.log)
    if not calls:
        raise ValueError("No model calls found; this is not a zero-cost model run")

    input_total = output_total = 0
    total_cost = harness_calls_cost = Decimal("0")
    providers_missing = 0

    for call in calls:
        # Provider may be absent in the stock trajectory.
        observed_provider = call["provider"]
        if observed_provider and observed_provider != args.provider:
            raise ValueError(f"Unexpected provider: {observed_provider}")
        providers_missing += int(not observed_provider)

        usage = call["usage"]
        prompt = token_count(usage, "prompt_tokens")
        completion = token_count(usage, "completion_tokens")
        cost = (
            prompt * Decimal(str(price["prompt_usd_per_mtok"]))
            + completion * Decimal(str(price["completion_usd_per_mtok"]))
        ) / Decimal("1000000")

        # Reasoning is already included in completion_tokens: do not add it again.
        input_total += prompt
        output_total += completion
        total_cost += cost
        if call["purpose"].startswith("harness:"):
            harness_calls_cost += cost

    print(json.dumps({
        "source_log": str(args.log),
        "model_priced_as": args.model,
        "provider_priced_as": args.provider,
        "calls": len(calls),
        "prompt_tokens": input_total,
        "completion_tokens": output_total,
        "cost_table_usd": str(total_cost),
        "harness_calls_cost_usd": str(harness_calls_cost),
        "calls_without_recorded_provider": providers_missing,
        "pricing_snapshot": table["snapshot_date"],
        "cache_policy": "All prompt tokens charged at listed input rate"
    }, indent=2))


if __name__ == "__main__":
    main()