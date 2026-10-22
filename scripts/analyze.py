#!/usr/bin/env python3
"""Analyze saved Harbor trials without model/API calls.

Example: python scripts/analyze.py --input results/dev/c1-c3-dev --split dev
         --output results/analysis/dev
Missing tasks and null rewards are never converted to failures. Unknown usage
is retained as a lower bound, not as an exact zero-cost observation.
"""
import argparse
import csv
import hashlib
import json
import math
import random
import re
import subprocess
import sys
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from statistics import mean

from collect_costs import summarize

ROOT = Path(__file__).resolve().parents[1]
CONFIGS = ["B0", "E", "H0", "V", "V-E"] + [f"H0+C{k}" for k in range(6)]
ALIASES = {c.lower(): c for c in CONFIGS}
ALIASES.update({f"c{k}": f"H0+C{k}" for k in range(6)})
ALIASES.update({f"h0-c{k}": f"H0+C{k}" for k in range(6)})
ASIDE = re.compile(r"\.(interrupted|errored|rerun)-\d")


def canonical(value: str) -> str:
    return ALIASES.get(value.lower(), value)


def average(values):
    return mean(values) if values else None


def decimal_sum(values):
    return sum((Decimal(str(v)) for v in values if v is not None), Decimal("0"))


def identify_config(path: Path, data: dict, override: str | None) -> str:
    value = ((data.get("agent_result") or {}).get("metadata") or {}).get("config_id")
    if value:
        if override and canonical(value) != canonical(override):
            raise ValueError(f"Config override disagrees with trial metadata: {path}")
        return canonical(value)
    if override:
        return canonical(override)
    for part in reversed(path.parts):
        if part.lower() in ALIASES:
            return ALIASES[part.lower()]
    raise ValueError(f"Cannot identify configuration for {path}; use --config for a single-config input")


def load_trial(path: Path, table: dict, families: dict, expected: set[str],
               override: str | None, pricing: Path) -> dict:
    data = json.loads(path.read_text())
    task = data["task_name"].removeprefix("local/")
    if task not in expected:
        raise ValueError(f"Task outside requested split: {task} in {path}")
    config = identify_config(path, data, override)
    metadata = ((data.get("agent_result") or {}).get("metadata") or {})
    log = path.parent / "agent/calls.jsonl"
    source = "calls.jsonl"
    if not log.is_file():
        log = path.parent / "agent/mini-swe-agent.trajectory.json"
        source = "mini-swe-agent.trajectory.json"
    model = ((data.get("agent_info") or {}).get("model_info") or {}).get("name")
    if not model:
        model = "openai/gpt-oss-120b" if config in {"E", "V-E"} else "openai/gpt-oss-20b"
    model = model.removeprefix("openrouter/")
    if log.is_file():
        report = summarize(log, model=model, provider=table["models"][model]["provider"],
                           pricing=pricing, result_path=path)
    else:
        # A setup failure may have no call log. Metadata cannot independently
        # prove zero spend, or reconstruct a missing HTTP-attempt count.
        source = "missing_log"
        report = {"known_cost_table_usd": metadata.get("known_cost_table_usd"),
                  "cost_table_usd": None, "usage_complete": False,
                  "n_unknown_calls": None, "calls": None,
                  "harness_calls_cost_usd": None,
                  "harness_injected_cost_usd_estimate": None,
                  "overhead_estimate_complete": False}
    reward = ((data.get("verifier_result") or {}).get("rewards") or {}).get("reward")
    if reward is not None and (type(reward) not in (int, float)
                              or not math.isfinite(reward) or not 0 <= reward <= 1):
        raise ValueError(f"Invalid verifier reward in {path}")
    exception = (data.get("exception_info") or {}).get("exception_type")
    finished = bool(data.get("finished_at"))
    archived = bool(ASIDE.search(str(path)))
    scored = finished and reward is not None and not exception and not archived
    return {
        "config_id": config, "task": task, "family": families[task]["family"],
        "trial": data.get("trial_name", path.parent.name), "reward": reward,
        "finished": finished, "archived": archived, "scored": scored,
        "exception": exception, "result_json": str(path), "cost_source": source,
        "model": model, **{k: report.get(k) for k in (
            "calls", "n_unknown_calls", "usage_complete", "known_cost_table_usd",
            "cost_table_usd", "prompt_tokens", "completion_tokens",
            "harness_calls_cost_usd", "harness_injected_cost_usd_estimate",
            "overhead_estimate_complete", "cost_crosscheck_passed")},
    }


def task_rewards(rows: list[dict]) -> dict[str, float]:
    groups = defaultdict(list)
    for row in rows:
        if row["scored"]:
            groups[row["task"]].append(row["reward"])
    return {task: mean(values) for task, values in groups.items()}


def percentile(values: list[float], probability: float) -> float:
    position = (len(values) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(values) - 1)
    return values[lower] + (values[upper] - values[lower]) * (position - lower)


def compare(left: str, right: str, rewards: dict, *, samples: int, seed: int) -> dict:
    common = sorted(set(rewards.get(left, {})) & set(rewards.get(right, {})))
    differences = [rewards[left][task] - rewards[right][task] for task in common]
    low = high = None
    if len(common) >= 2:
        digest = int.from_bytes(hashlib.sha256(f"{left}:{right}".encode()).digest()[:8], "big")
        rng = random.Random(seed + digest)
        draws = sorted(mean(rng.choices(differences, k=len(differences))) for _ in range(samples))
        low, high = percentile(draws, 0.025), percentile(draws, 0.975)
    return {"config_id": left, "reference": right, "n_paired_tasks": len(common),
            "mean_reward_difference": average(differences), "ci95_low": low, "ci95_high": high,
            "wins": sum(x > 0 for x in differences), "ties": sum(x == 0 for x in differences),
            "losses": sum(x < 0 for x in differences), "paired_task_ids": common}


def aggregate(rows: list[dict], expected: set[str], population: dict,
              *, samples: int = 10000, seed: int = 42, allow_repeats: bool = False):
    grouped = defaultdict(list)
    seen = set()
    for row in rows:
        grouped[row["config_id"]].append(row)
        key = row["config_id"], row["task"]
        if not row["archived"]:
            if key in seen and not allow_repeats:
                raise ValueError(f"Duplicate active config/task {key}; choose one run or use --allow-repeats")
            seen.add(key)
    configs = list(dict.fromkeys(CONFIGS + sorted(grouped)))
    summaries, family_rows, coverage, rewards = [], [], [], {}
    for config in configs:
        all_rows = grouped.get(config, [])
        active = [r for r in all_rows if not r["archived"]]
        reward_map = task_rewards(active)
        rewards[config] = reward_map
        attempted = {r["task"] for r in active}
        known = decimal_sum(r["known_cost_table_usd"] for r in active)
        cost_available = bool(active) and all(r["known_cost_table_usd"] is not None for r in active)
        complete = cost_available and all(r["usage_complete"] for r in active)
        family_means = {}
        for family in population:
            values = [v for task, v in reward_map.items()
                      if any(r["task"] == task and r["family"] == family for r in active)]
            family_means[family] = average(values)
            family_rows.append({"config_id": config, "family": family,
                                "n_scored_tasks": len(values), "mean_reward": average(values)})
        weighted = None
        if all(value is not None for value in family_means.values()):
            weighted = sum(family_means[f] * count for f, count in population.items()) / sum(population.values())
        all_scored = set(reward_map) == expected
        summaries.append({
            "config_id": config, "status": "not_run" if not active else "complete" if all_scored else "partial",
            "n_expected_tasks": len(expected), "n_attempted_tasks": len(attempted),
            "n_active_trials": len(active), "n_archived_trials": len(all_rows) - len(active),
            "n_scored_tasks": len(reward_map), "n_exception_trials": sum(bool(r["exception"]) for r in active),
            "n_unscored_trials": sum(not r["scored"] for r in active),
            "mean_reward_observed": average(list(reward_map.values())),
            "mean_reward_full_split": average(list(reward_map.values())) if all_scored else None,
            "family_reweighted_observed": weighted,
            "known_cost_total_usd": str(known) if cost_available else None,
            "known_cost_observed_usd": str(known) if active else None,
            "mean_known_cost_per_attempted_task_usd": str(known / len(attempted)) if cost_available else None,
            "cost_total_usd": str(known) if complete else None,
            "mean_cost_per_attempted_task_usd": str(known / len(attempted)) if complete else None,
            "usage_complete": complete, "cost_is_lower_bound": bool(active) and not complete,
            "n_unknown_calls": sum(r["n_unknown_calls"] or 0 for r in active) if active else None,
            "n_missing_call_logs": sum(r["cost_source"] == "missing_log" for r in active),
            "known_cost_including_archives_usd": str(decimal_sum(r["known_cost_table_usd"] for r in all_rows)) if all_rows else None,
            "known_harness_calls_cost_usd": str(decimal_sum(r["harness_calls_cost_usd"] for r in active)) if active else None,
            "harness_injected_cost_usd_estimate": str(decimal_sum(r["harness_injected_cost_usd_estimate"] for r in active)) if active else None,
            "overhead_estimate_complete": bool(active) and all(r["overhead_estimate_complete"] for r in active),
            "scored_task_ids": sorted(reward_map), "attempted_task_ids": sorted(attempted),
            "missing_or_unscored_task_ids": sorted(expected - set(reward_map)),
        })
        for task in sorted(expected):
            coverage.append({"config_id": config, "task": task,
                             "attempted": task in attempted, "scored": task in reward_map})
    pairs = [(c, "B0") for c in configs if c != "B0"]
    pairs += [("V", "E"), ("V-E", "E")]
    comparisons = [compare(c, reference, rewards, samples=samples, seed=seed) for c, reference in pairs]
    ablations = [compare(f"H0+C{k}", "H0", rewards, samples=samples, seed=seed) for k in range(6)]
    return {"summary": summaries, "families": family_rows, "coverage": coverage,
            "comparisons": comparisons, "ablations": ablations}


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("")
        return
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        for row in rows:
            writer.writerow({k: json.dumps(v) if isinstance(v, (list, dict)) else v for k, v in row.items()})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, nargs="+", required=True)
    parser.add_argument("--split", choices=["dev", "eval"], required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--config", help="Explicit ID for a single-configuration input")
    parser.add_argument("--pricing", type=Path, default=ROOT / "configs/pricing.json")
    parser.add_argument("--bootstrap-samples", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--allow-repeats", action="store_true",
                        help="Average repeated rewards within each task; cost includes all active repeats")
    args = parser.parse_args()
    if args.bootstrap_samples < 100:
        parser.error("--bootstrap-samples must be at least 100")
    try:
        expected = set(subprocess.check_output([sys.executable, str(ROOT / "scripts/task_list.py"), args.split], text=True).splitlines())
        mapping = json.loads((ROOT / "configs/task_families.json").read_text())
        table = json.loads(args.pricing.read_text())
        results = set()
        for directory in args.input:
            if not directory.is_dir():
                raise ValueError(f"Input directory does not exist: {directory}")
            results.update(p.resolve() for p in directory.rglob("result.json") if "__" in p.parent.name)
        if not results:
            raise ValueError("No trial result.json files found")
        rows = [load_trial(p, table, mapping["tasks"], expected, args.config, args.pricing) for p in sorted(results)]
        data = aggregate(rows, expected, mapping["family_counts"], samples=args.bootstrap_samples,
                         seed=args.seed, allow_repeats=args.allow_repeats)
    except (ValueError, KeyError, OSError, ArithmeticError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Analysis failed: {error}\n")
    args.output.mkdir(parents=True, exist_ok=True)
    write_csv(args.output / "trials.csv", rows)
    for key in ("summary", "comparisons", "ablations", "coverage", "families"):
        write_csv(args.output / f"{key}.csv", data[key])
    data["trials"] = rows
    data["metadata"] = {
        "split": args.split, "expected_task_ids": sorted(expected),
        "input_roots": [str(p) for p in args.input], "bootstrap_samples": args.bootstrap_samples,
        "seed": args.seed, "allow_repeats": args.allow_repeats,
        "policies": [
            "Reward means use only finished, scored, exception-free active tasks; missing tasks are not zero.",
            "Trial exceptions are excluded pending failure classification, rather than silently scored zero.",
            "Unknown usage is a lower bound; exact totals are null when incomplete.",
            "Main costs cover active attempts; archived-attempt known spend is reported separately.",
            "Paired intervals use common scored tasks; fewer than two tasks yields no interval.",
            "Family reweighting is unavailable unless all families have scored tasks.",
            "Dev outputs are pipeline validation, not final evaluation or causal component evidence.",
        ],
    }
    (args.output / "analysis.json").write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")
    print(f"Analysis split: {args.split}; expected tasks: {len(expected)}")
    print(f"Trial records: {len(rows)}")
    for row in data["summary"]:
        if row["n_active_trials"]:
            print(f"{row['config_id']}: scored={row['n_scored_tasks']}/{len(expected)} "
                  f"mean_reward={row['mean_reward_observed']} "
                  f"known_cost=${row['known_cost_observed_usd']} "
                  f"unknown_calls={row['n_unknown_calls']} complete={row['usage_complete']}")
    print(f"Saved tables and analysis.json to: {args.output}")


if __name__ == "__main__":
    main()
