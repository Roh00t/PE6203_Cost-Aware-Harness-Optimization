#!/usr/bin/env python3
"""Deterministic stratified sampling of the TUA-Bench evaluation subset.

Within each task family, tasks are ranked by sha256("<salt>:<seed>:<task_id>").
Ranks 1..per_family form the eval split, the next dev_per_family form the dev
split (harness development and model pilots only), and the rest are reserves,
consumed in rank order if an eval task fails the oracle gate.

Hash ranking is used instead of random.sample because Python only guarantees
reproducibility of random.random() across versions, not of sample(); it also
leaves every other task's rank unchanged if upstream adds or removes a task.

Usage:
    python3 scripts/sample_tasks.py            # defaults: seed 42, 8 eval + 2 dev per family
"""

import argparse
import hashlib
import json
import subprocess
import sys
import tomllib
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SALT = "tua-subset-v1"
PINNED_TUA_SHA = "3497fd320abcafaf4797424192c891a593fd7964"
EXPECTED_N_TASKS = 120
GLOB_CHARS = set("*?[]")


def git(tua_root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(tua_root), *args], capture_output=True, text=True, check=True
    ).stdout.strip()


def rank_key(seed: int, task_id: str) -> str:
    return hashlib.sha256(f"{SALT}:{seed}:{task_id}".encode()).hexdigest()


def fingerprint(task_ids: list[str]) -> str:
    return hashlib.sha256("\n".join(sorted(task_ids)).encode()).hexdigest()


def load_task_meta(task_dir: Path) -> dict:
    with (task_dir / "task.toml").open("rb") as f:
        cfg = tomllib.load(f)
    env = cfg.get("environment", {})
    meta = cfg.get("metadata", {})
    return {
        "category": meta.get("category"),
        "difficulty": meta.get("difficulty"),
        "cpus": env.get("cpus"),
        "memory_mb": env.get("memory_mb"),
        "storage_mb": env.get("storage_mb"),
        "agent_timeout_sec": cfg.get("agent", {}).get("timeout_sec"),
    }


def write_args(path: Path, task_ids: list[str]) -> None:
    # One `-i <task-id>` per line; usable as `harbor run -p tasks $(cat <file>)`.
    path.write_text("".join(f"-i {t}\n" for t in task_ids))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--tua-root", type=Path, default=REPO_ROOT / "data" / "TUA-Bench")
    ap.add_argument("--families", type=Path, default=REPO_ROOT / "configs" / "task_families.json")
    ap.add_argument("--out-dir", type=Path, default=REPO_ROOT / "configs")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--per-family", type=int, default=8)
    ap.add_argument("--dev-per-family", type=int, default=2)
    ap.add_argument("--expect-sha", default=PINNED_TUA_SHA,
                    help="required TUA-Bench commit; pass '' to skip the check")
    ap.add_argument("--allow-dirty", action="store_true",
                    help="permit local modifications in the TUA-Bench checkout")
    args = ap.parse_args()

    tua_sha = git(args.tua_root, "rev-parse", "HEAD")
    if args.expect_sha and tua_sha != args.expect_sha:
        sys.exit(f"TUA-Bench is at {tua_sha}, expected {args.expect_sha}. "
                 f"Run: git -C {args.tua_root} checkout {args.expect_sha}")
    # Tracked-file changes would mean modified tasks or verifiers.
    dirty = git(args.tua_root, "status", "--porcelain", "--untracked-files=no", "--", "tasks", "dataset.toml")
    if dirty and not args.allow_dirty:
        sys.exit(f"TUA-Bench tasks have local modifications (verifiers must be unmodified):\n{dirty}")

    with (args.tua_root / "dataset.toml").open("rb") as f:
        dataset = tomllib.load(f)
    digests = {t["name"].removeprefix("local/"): t["digest"] for t in dataset["tasks"]}
    task_ids = sorted(digests)
    families = json.loads(args.families.read_text())["tasks"]

    # Integrity checks: any drift must stop the run, never silently re-sample.
    if len(task_ids) != EXPECTED_N_TASKS:
        sys.exit(f"dataset.toml lists {len(task_ids)} tasks, expected {EXPECTED_N_TASKS}")
    if set(task_ids) != set(families):
        sys.exit(f"dataset.toml and {args.families} disagree: "
                 f"{sorted(set(task_ids) ^ set(families))}")
    missing_dirs = [t for t in task_ids if not (args.tua_root / "tasks" / t / "task.toml").is_file()]
    if missing_dirs:
        sys.exit(f"No tasks/<id>/task.toml for: {missing_dirs}")
    globby = [t for t in task_ids if GLOB_CHARS & set(t)]
    if globby:
        sys.exit(f"Task IDs contain glob characters and would mis-filter in Harbor: {globby}")

    by_family: dict[str, list[str]] = {}
    for t in task_ids:
        by_family.setdefault(families[t]["family"], []).append(t)

    need = args.per_family + args.dev_per_family
    splits: dict[str, dict[str, list[str]]] = {}
    for family in sorted(by_family):
        members = by_family[family]
        if len(members) < need:
            sys.exit(f"{family} has {len(members)} tasks, need {need}")
        ranked = sorted(members, key=lambda t: rank_key(args.seed, t))
        splits[family] = {
            "eval": sorted(ranked[: args.per_family]),
            "dev": sorted(ranked[args.per_family : need]),
            "reserve": ranked[need:],  # kept in rank order: substitution order
        }

    eval_ids = sorted(t for s in splits.values() for t in s["eval"])
    dev_ids = sorted(t for s in splits.values() for t in s["dev"])
    assert not set(eval_ids) & set(dev_ids)
    assert len(set(eval_ids)) == args.per_family * len(splits)

    tasks_meta = {
        t: {**families[t], **load_task_meta(args.tua_root / "tasks" / t), "digest": digests[t]}
        for t in task_ids
    }
    subset = {
        "tua_bench_commit": tua_sha,
        "seed": args.seed,
        "salt": SALT,
        "per_family": args.per_family,
        "dev_per_family": args.dev_per_family,
        "eval_fingerprint": fingerprint(eval_ids),
        "dev_fingerprint": fingerprint(dev_ids),
        "family_population": {f: len(m) for f, m in sorted(by_family.items())},
        "eval_task_ids": eval_ids,
        "dev_task_ids": dev_ids,
        "families": splits,
        "tasks": tasks_meta,
    }

    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "task_subset.json").write_text(json.dumps(subset, indent=2) + "\n")
    write_args(args.out_dir / "eval_tasks.args", eval_ids)
    write_args(args.out_dir / "dev_tasks.args", dev_ids)

    print(f"TUA-Bench {tua_sha[:12]}  seed={args.seed}  salt={SALT}")
    print(f"eval fingerprint {subset['eval_fingerprint']}")
    for family, s in splits.items():
        diff = Counter(tasks_meta[t]["difficulty"] for t in s["eval"])
        subs = Counter(tasks_meta[t]["subcategory"] for t in s["eval"])
        print(f"\n{family}  (population {len(by_family[family])}; "
              f"difficulty {dict(sorted(diff.items()))}; {len(subs)} subcategories)")
        for t in s["eval"]:
            m = tasks_meta[t]
            print(f"  {t:<34} {m['subcategory']:<34} {m['difficulty']:<7} "
                  f"{m['cpus']}cpu {m['memory_mb'] // 1024}GB")
        print(f"  dev: {', '.join(s['dev'])}")


if __name__ == "__main__":
    main()
