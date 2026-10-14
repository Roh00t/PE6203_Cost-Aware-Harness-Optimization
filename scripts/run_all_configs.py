#!/usr/bin/env python3
"""Run several configurations on the same tasks, one trial at a time, through harbor_run.sh.

    uv run --frozen python scripts/run_all_configs.py --split dev \
        --task-id 106-create-charles-ssh-user --configs B0,H0 \
        --run-name smoke-b0-h0 --job-budget-usd 0.05 --dry-run

Order is task-major (architecture §10.3): every requested configuration runs on task t, then
task t+1, so live websites drift within a task's comparison rather than across configurations.
Trials run strictly one after another; harbor_run.sh keeps --n-concurrent 1 unless N_CONCURRENT
is set. Each (configuration, task) pair is its own harbor_run.sh call, so all of its checks
(TUA-Bench commit, task filter, assets, Docker memory, free disk, leak check, paid-run gates)
run every time, and a rerun with the same --run-name resumes: finished pairs are skipped.

Layout: jobs/<run-name>/<config>/<task>/ (Harbor output), jobs/<run-name>/runner.jsonl (one
line per pair, appended and flushed as it happens), jobs/<run-name>/ledger.sqlite (the per-run
spend kill switch shared by every harness trial; B0 and E keep stock defaults and have no cap).

Configurations: B0, E (stock mini-swe-agent 2.4.6 with the frozen model file), H0, H0+C0 ...
H0+C5, V, V-E (our harness; C0..C5 are accepted as short names), ALL (the 11 in report order),
or a path to any YAML under configs/harness/. Paid runs need CONFIRM_PAID=1, and the eval
split also CONFIRM_EVAL=1, exactly as for harbor_run.sh; this script never sets them.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MINI_SWE_AGENT_VERSION = "2.4.6"
HARNESS_AGENT = "harness.agent:CostAwareAgent"

STOCK = {"B0": "configs/models/base.yaml", "E": "configs/models/expensive.yaml"}
HARNESS = {
    "H0": "configs/harness/h0.yaml",
    "H0+C0": "configs/harness/c0.yaml",
    "H0+C1": "configs/harness/c1.yaml",
    "H0+C2": "configs/harness/c2.yaml",
    "H0+C3": "configs/harness/c3.yaml",
    "H0+C4": "configs/harness/c4.yaml",
    "H0+C5": "configs/harness/c5.yaml",
    "V": "configs/harness/V.yaml",
    "V-E": "configs/harness/V-E.yaml",
}
ALL = ["B0", "E", "H0", "H0+C0", "H0+C1", "H0+C2", "H0+C3", "H0+C4", "H0+C5", "V", "V-E"]


class Config:
    def __init__(self, name: str, kind: str, path: str):
        self.name, self.kind, self.path = name, kind, path

    @property
    def slug(self) -> str:
        """Directory-safe name: 'H0+C1' -> 'h0-c1', 'V-E' -> 'v-e'."""
        return re.sub(r"[^a-z0-9]+", "-", self.name.lower()).strip("-")


def resolve_configs(spec: str) -> list[Config]:
    names = [s.strip() for s in spec.split(",") if s.strip()]
    if names == ["ALL"]:
        names = list(ALL)
    configs, seen = [], set()
    for raw in names:
        name = f"H0+{raw}" if re.fullmatch(r"C[0-5]", raw) else raw
        if name in STOCK:
            config = Config(name, "stock", STOCK[name])
        elif name in HARNESS:
            config = Config(name, "harness", HARNESS[name])
        elif raw.endswith((".yaml", ".yml")):
            path = Path(raw)
            path = (path if path.is_absolute() else ROOT / path).resolve()
            if (ROOT / "configs" / "harness") not in path.parents or not path.is_file():
                sys.exit(f"run_all_configs: {raw} is not a file under configs/harness/")
            from harness.config import load_config
            config_id = load_config(path)[0].config_id
            config = Config(config_id, "harness", str(path.relative_to(ROOT)))
        else:
            sys.exit(f"run_all_configs: unknown configuration '{raw}'. Known: {', '.join(ALL)}, "
                     "C0..C5, ALL, or a configs/harness/*.yaml path")
        if config.name in seen:
            sys.exit(f"run_all_configs: configuration '{config.name}' listed twice")
        seen.add(config.name)
        configs.append(config)
    if not configs:
        sys.exit("run_all_configs: --configs is empty")
    return configs


def split_tasks(split: str) -> list[str]:
    out = subprocess.run([sys.executable, str(ROOT / "scripts" / "task_list.py"), split],
                         capture_output=True, text=True, check=True, cwd=ROOT)
    return out.stdout.split()


def resolve_tasks(split: str, task_ids: list[str]) -> list[str]:
    available = split_tasks(split)
    if not task_ids:
        return available
    wanted = [t.strip() for group in task_ids for t in group.split(",") if t.strip()]
    unknown = [t for t in wanted if t not in available]
    if unknown:
        sys.exit(f"run_all_configs: not in the {split} split: {', '.join(unknown)}")
    return list(dict.fromkeys(wanted))


def preflight(configs: list[Config]) -> list[str]:
    """Load every harness config offline; return problems (missing plugins etc.)."""
    problems = []
    for config in configs:
        if config.kind == "stock":
            if not (ROOT / config.path).is_file():
                problems.append(f"{config.name}: missing {config.path}")
            continue
        try:
            from harness.agent import factory
            from harness.config import load_config
            from harness.prompts import render_templates

            harness_config, stock = load_config(config.path)
            render_templates(stock, harness_config)
            factory(harness_config.guardrail_factory)
            for plugin in harness_config.plugins:
                factory(plugin)
        except Exception as error:  # report every blocked config, not just the first
            problems.append(f"{config.name} ({config.path}): {error}")
    return problems


def model_name(model_file: str) -> str:
    import yaml

    return yaml.safe_load((ROOT / model_file).read_text(encoding="utf-8"))["model"]["model_name"]


def build_command(config: Config, split: str, task: str, run_name: str,
                  job_budget_usd: float | None, prune_cache: bool) -> list[str]:
    cmd = ["bash", "scripts/harbor_run.sh", "--split", split, "--only", task]
    if prune_cache:
        cmd.append("--prune-cache")
    cmd += ["--", "--job-name", f"{run_name}/{config.slug}"]
    if config.kind == "stock":
        cmd += ["--agent", "mini-swe-agent", "--model", model_name(config.path),
                "--ak", f"version={MINI_SWE_AGENT_VERSION}", "--ak", f"config_file={config.path}"]
    else:
        cmd += ["--agent-import-path", HARNESS_AGENT, "--ak", f"config_path={config.path}"]
        if job_budget_usd is not None:
            ledger = ROOT / "jobs" / run_name / "ledger.sqlite"
            cmd += ["--ak", f"job_budget_usd={job_budget_usd}", "--ak", f"job_ledger_path={ledger}"]
    return cmd


def trial_outcome(job_dir: Path) -> dict:
    """Reward and exception of the newest finished trial in a per-task Harbor job."""
    trials = sorted((p for p in job_dir.glob("*__*/result.json")), key=lambda p: p.stat().st_mtime)
    for path in reversed(trials):
        result = json.loads(path.read_text())
        if result.get("finished_at"):
            return {
                "trial": result.get("trial_name"),
                "reward": ((result.get("verifier_result") or {}).get("rewards") or {}).get("reward"),
                "exception": (result.get("exception_info") or {}).get("exception_type"),
                "cost_usd": (result.get("agent_result") or {}).get("cost_usd"),
            }
    return {"trial": None, "reward": None, "exception": "no finished trial", "cost_usd": None}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    ap.add_argument("--split", choices=["dev", "eval"], required=True)
    ap.add_argument("--task-id", action="append", default=[],
                    help="task ID(s), comma-separated or repeated; default: the whole split")
    ap.add_argument("--configs", required=True, help="comma-separated, e.g. B0,H0,C1,V or ALL")
    ap.add_argument("--run-name", required=True, help="jobs/<run-name>/; reuse it to resume")
    ap.add_argument("--job-budget-usd", type=float,
                    help="spend cap shared by every harness trial in this run (agreed estimate + 20%%)")
    ap.add_argument("--keep-going", action="store_true",
                    help="continue after a harbor_run.sh failure instead of stopping")
    ap.add_argument("--prune-cache", action="store_true",
                    help="trim Docker's build cache after the last configuration of each task")
    ap.add_argument("--dry-run", action="store_true", help="print the commands, run nothing")
    args = ap.parse_args()

    if not re.fullmatch(r"[A-Za-z0-9._-]+", args.run_name):
        sys.exit("run_all_configs: --run-name may use letters, digits, '.', '_' and '-' only")
    sys.path.insert(0, str(ROOT))
    configs = resolve_configs(args.configs)
    tasks = resolve_tasks(args.split, args.task_id)
    uses_harness = any(c.kind == "harness" for c in configs)

    problems = preflight(configs)
    if uses_harness and args.job_budget_usd is None and not args.dry_run:
        problems.append("harness configurations need --job-budget-usd (the per-run kill switch)")
    if args.job_budget_usd is not None and args.job_budget_usd <= 0:
        problems.append("--job-budget-usd must be positive")
    if not args.dry_run:
        if os.environ.get("CONFIRM_PAID") != "1":
            problems.append("every configuration calls a paid model: set CONFIRM_PAID=1 once the "
                            "run and its cost are agreed")
        if args.split == "eval" and os.environ.get("CONFIRM_EVAL") != "1":
            problems.append("the eval split is for recorded results only: set CONFIRM_EVAL=1")
    if problems:
        print("run_all_configs: not starting:", *problems, sep="\n  - ", file=sys.stderr)
        return 2

    env = dict(os.environ)
    if uses_harness:  # Harbor imports harness.agent from the uninstalled repo package
        env["PYTHONPATH"] = os.pathsep.join(filter(None, [str(ROOT), env.get("PYTHONPATH")]))
    run_dir = ROOT / "jobs" / args.run_name
    pairs = [(task, config) for task in tasks for config in configs]
    print(f"run_all_configs: run={args.run_name} split={args.split} tasks={len(tasks)} "
          f"configs={','.join(c.name for c in configs)} trials={len(pairs)} "
          f"job_budget_usd={args.job_budget_usd}")

    log = None
    if not args.dry_run:
        run_dir.mkdir(parents=True, exist_ok=True)
        log = (run_dir / "runner.jsonl").open("a", encoding="utf-8")
    failures = 0
    try:
        for n, (task, config) in enumerate(pairs, 1):
            last_for_task = config is configs[-1]
            cmd = build_command(config, args.split, task, args.run_name, args.job_budget_usd,
                                args.prune_cache and last_for_task)
            print(f"\n[{n}/{len(pairs)}] {task} x {config.name}\n  " + " ".join(cmd), flush=True)
            if args.dry_run:
                continue
            started = time.monotonic()
            try:
                code = subprocess.run(cmd, cwd=ROOT, env=env).returncode
            except KeyboardInterrupt:
                code = 130
            record = {
                "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "run": args.run_name, "split": args.split, "task": task,
                "config": config.name, "config_path": config.path, "exit_code": code,
                "wall_s": round(time.monotonic() - started, 1),
                **trial_outcome(run_dir / config.slug / task),
            }
            log.write(json.dumps(record) + "\n")
            log.flush()
            print(f"  -> exit {code}, reward {record['reward']}, exception {record['exception']}")
            if code == 130:
                print("run_all_configs: interrupted; rerun the same command to resume")
                return 130
            if code != 0:
                failures += 1
                if not args.keep_going:
                    print("run_all_configs: stopping after a failed harbor_run.sh call "
                          "(use --keep-going to continue)", file=sys.stderr)
                    return code
    finally:
        if log:
            log.close()
    if not args.dry_run:
        print(f"\nrun_all_configs: done, {failures} failed call(s). Per-pair log: {run_dir / 'runner.jsonl'}")
        print(f"Per-configuration tables: python3 scripts/summarize_run.py jobs/{args.run_name}/<config>")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
