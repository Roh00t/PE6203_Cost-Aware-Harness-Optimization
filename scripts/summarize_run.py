#!/usr/bin/env python3
"""Summarise a harbor_run.sh run (one Harbor job per task) into one table.

    python3 scripts/summarize_run.py jobs/<run>

Prints one row per trial (task, agent, reward, exception, timings) and the mean
reward, and writes <run>/summary.json.
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path


def seconds(block: dict | None) -> float | None:
    if not block or not block.get("started_at") or not block.get("finished_at"):
        return None
    parse = lambda s: datetime.fromisoformat(s.replace("Z", "+00:00"))  # noqa: E731
    return (parse(block["finished_at"]) - parse(block["started_at"])).total_seconds()


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    run = Path(sys.argv[1])
    rows = []
    # Trial dirs are named <task>__<id>; nested one level deeper for per-task jobs.
    # Skip earlier attempts set aside by harbor_run.sh (<task>.<interrupted|errored|rerun>-<time>/).
    aside = re.compile(r"\.(interrupted|errored|rerun)-\d")
    for result in sorted(p for p in run.rglob("result.json")
                         if "__" in p.parent.name and not aside.search(str(p))):
        r = json.loads(result.read_text())
        if not r.get("finished_at"):
            continue
        rows.append({
            "task": r["task_name"].removeprefix("local/"),
            "trial": r["trial_name"],
            "agent": (r.get("agent_info") or {}).get("name"),
            "reward": ((r.get("verifier_result") or {}).get("rewards") or {}).get("reward"),
            "exception": (r.get("exception_info") or {}).get("exception_type"),
            "setup_s": seconds(r.get("environment_setup")),
            "agent_s": seconds(r.get("agent_execution")),
            "verify_s": seconds(r.get("verifier")),
        })
    if not rows:
        sys.exit(f"no finished trials under {run}")

    rewards = [row["reward"] or 0.0 for row in rows]
    mean = sum(rewards) / len(rewards)
    fmt = lambda s: "-" if s is None else f"{s / 60:.1f}m" if s >= 60 else f"{s:.0f}s"  # noqa: E731
    print(f"{'task':36} {'agent':10} {'reward':>6}  {'setup':>6} {'agent':>6} {'verify':>6}  exception")
    for row in rows:
        reward = "-" if row["reward"] is None else f"{row['reward']:.2f}"
        print(f"{row['task']:36} {str(row['agent']):10} {reward:>6}  {fmt(row['setup_s']):>6} "
              f"{fmt(row['agent_s']):>6} {fmt(row['verify_s']):>6}  {row['exception'] or ''}")
    print(f"\n{len(rows)} trials, mean reward {mean:.3f}")
    (run / "summary.json").write_text(json.dumps({"mean_reward": mean, "trials": rows}, indent=2) + "\n")


if __name__ == "__main__":
    main()
