#!/usr/bin/env python3
"""Label why each eval trial failed, for the report's failure-classification section.

    uv run --frozen python scripts/classify_failures.py [RUN_DIR] [--out DIR]

RUN_DIR is an exported run laid out as <config>/<task>/<task>__<trial-id>/ (default
results/eval/rohit-eval-pass1). Config folders are discovered, so later passes need no change.
Task folders named <task>.errored-<time>, .interrupted-<time> or .rerun-<time> are archived
infrastructure attempts: listed as "excluded", never scored.

Writes to --out (default results/analysis/<RUN_DIR under results/>/failures):
  trials_classified.csv  one row per trial: primary label, all matching labels, evidence
  summary.csv            primary-label counts and harness/model totals per config
  examples.md            up to 3 candidate example trials per label, with key steps quoted
Output is deterministic: rerunning on the same input gives byte-identical files.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUN = ROOT / "results" / "eval" / "rohit-eval-pass1"
FAMILIES = ROOT / "configs" / "task_families.json"
ARCHIVED = re.compile(r"\.(errored|interrupted|rerun)-\d")
STOCK_TIMEOUT_S = 30  # mini-swe-agent's command timeout; harness trials log theirs in trial_start

# --- Taxonomy (owner: Isha). Edit here; tests/test_classify_failures.py pins the behaviour. ---
# A trial with reward == 1 is "success". Otherwise every rule below is tested against it: the
# first match (table order = precedence) is the primary label, all matches go to all_labels,
# and a trial matching nothing is "unclassified" (listed for manual review).
BUDGET_EXITS = {"LimitsExceeded", "CostCapExceeded", "TimeExceeded"}
# Verifier failure lines that mean the output was never produced (vs produced but wrong).
MISSING_OUTPUT = re.compile(r"missing|not found|no such file|does not exist|is empty|\bempty\b", re.I)

RULES: list[tuple[str, str, Callable[[Trial], bool]]] = [
    # Harness-level. Guardrail blocks are flagged for manual review: some are false positives.
    ("guardrail_blocked", "harness",
     lambda t: t.n_guardrail_blocks > 0 or t.exit_status == "GuardrailLimit"),
    ("unparsable_tool_call", "harness", lambda t: t.exit_status == "RepeatedFormatError"),
    # Harbor's own agent timeout (AgentTimeoutError) is the wall-clock budget running out.
    ("budget_exhausted", "harness",
     lambda t: t.exit_status in BUDGET_EXITS or t.cap_reached or t.exception == "AgentTimeoutError"),
    ("timeout_no_recovery", "harness", lambda t: t.timeout_unrecovered),
    ("premature_submit_missing_output", "harness",
     lambda t: t.exit_status == "Submitted" and t.output_missing),
    # Model-level. wrong_output needs verifier evidence; a silent verifier can't tell
    # "missing" from "wrong", so those trials stay unclassified unless they scored partially.
    ("wrong_output", "model",
     lambda t: t.exit_status == "Submitted" and bool(t.verifier_lines) and not t.output_missing),
    ("partial_credit", "model", lambda t: 0 < t.reward < 1),
]
# ---------------------------------------------------------------------------------------------

LABEL_TYPE = {label: kind for label, kind, _ in RULES} | {"unclassified": "unclassified"}
COLUMNS = ["config", "task", "family", "trial_id", "reward", "exit_status", "primary_label",
           "failure_type", "all_labels", "guardrail_rules", "n_guardrail_blocks",
           "n_format_errors", "n_steps", "evidence", "needs_review", "trial_path"]


@dataclass
class Step:
    command: str
    output: str


@dataclass
class Trial:
    config: str
    task: str
    path: Path
    archived: bool = False
    reward: float | None = None
    exit_status: str = ""
    exception: str = ""
    n_steps: int = 0
    n_format_errors: int = 0
    blocks: list[dict] = field(default_factory=list)
    cap_reached: bool = False
    timeout_unrecovered: bool = False
    verifier_lines: list[str] = field(default_factory=list)
    steps: list[Step] = field(default_factory=list)
    labels: list[str] = field(default_factory=list)

    @property
    def n_guardrail_blocks(self) -> int:
        return len(self.blocks)

    @property
    def output_missing(self) -> bool:
        return any(MISSING_OUTPUT.search(line) for line in self.verifier_lines)

    @property
    def primary(self) -> str:
        if self.archived:
            return "archived_attempt"
        if self.reward is None:
            return "unscored"
        if self.reward >= 1:
            return "success"
        return self.labels[0] if self.labels else "unclassified"

    @property
    def failure_type(self) -> str:
        if self.primary in ("archived_attempt", "unscored"):
            return "excluded"
        return "success" if self.primary == "success" else LABEL_TYPE[self.primary]


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(errors="replace"))
    except (OSError, ValueError):
        return {}


def read_events(path: Path) -> list[dict]:
    """Append-only log; a killed trial may leave a torn last line, which is skipped."""
    events = []
    if path.is_file():
        for line in path.read_text(errors="replace").splitlines():
            try:
                events.append(json.loads(line))
            except ValueError:
                continue
    return events


def verifier_failures(stdout: str) -> list[str]:
    """pytest 'E ' lines, else bare AssertionError/ERROR lines (non-pytest verifiers), else the
    last line printed. Empty only when the verifier printed nothing."""
    lines = [line.strip() for line in stdout.splitlines() if line.strip()]
    pytest_lines = [line[1:].strip() for line in lines if line.startswith("E ") and line[1:].strip()]
    failures = pytest_lines or [line for line in lines
                                if "AssertionError" in line or line.startswith(("ERROR", "FAILED"))]
    return failures or lines[-1:]


def first_line(text: str, width: int) -> str:
    line = next((s for s in str(text).splitlines() if s.strip()), "")
    return line[:width] + ("…" if len(line) > width else "")


def trajectory_steps(messages: list[dict], timeout_s: float = STOCK_TIMEOUT_S) -> tuple[list[Step], int, bool]:
    """One step per model call (command or format error, plus observation), the format-error
    count, and whether the last command timeout was never followed by a successful command."""
    steps: list[Step] = []
    format_errors = 0
    last_timeout = None
    last_success = None
    sent_at = None
    for message in messages:
        extra = message.get("extra") or {}
        role = message.get("role")
        text = str(extra.get("raw_output", message.get("content", "")))
        if role == "assistant":
            sent_at = extra.get("timestamp")
            commands = [str(a["command"]) if "command" in a
                        else f"{a.get('tool')}({json.dumps(a.get('arguments'), sort_keys=True)})"
                        for a in extra.get("actions") or []]
            steps.append(Step(" ; ".join(commands) or "(no valid tool call)", ""))
        elif extra.get("interrupt_type") == "FormatError":
            # The rejected response is not in the history; its text survives in extra.response.
            format_errors += 1
            reply = (((extra.get("response") or {}).get("choices") or [{}])[0].get("message") or {})
            said = first_line(reply.get("content") or "", 100)
            steps.append(Step("(no valid tool call" + (f"; model wrote: {said})" if said else ")"), text))
        elif role in ("tool", "user") and steps:
            steps[-1].output += ("\n" if steps[-1].output else "") + text
            if role == "tool" and "timed out" in str(extra.get("exception_info", "")).lower():
                # The harness reports every rc 124/137 as "timed out or was killed"; a command
                # that killed its own shell (pkill -f) returns at once, so only count long runs.
                took = (extra.get("timestamp") or 0) - (sent_at or 0)
                if not (sent_at and extra.get("timestamp")) or took >= 0.9 * timeout_s:
                    last_timeout = len(steps)
            elif role == "tool" and extra.get("returncode") == 0:
                last_success = len(steps)
    unrecovered = last_timeout is not None and (last_success or 0) <= last_timeout
    return steps, format_errors, unrecovered


def load_trial(config: str, task: str, path: Path, archived: bool) -> Trial:
    trial = Trial(config, task, path, archived)
    result = read_json(path / "result.json")
    reward_file = path / "verifier" / "reward.txt"
    try:
        trial.reward = float(reward_file.read_text().strip())
    except (OSError, ValueError):
        reward = ((result.get("verifier_result") or {}).get("rewards") or {}).get("reward")
        trial.reward = float(reward) if isinstance(reward, (int, float)) else None
    trial.exception = str((result.get("exception_info") or {}).get("exception_type") or "")
    trajectory = read_json(path / "agent" / "mini-swe-agent.trajectory.json")
    info = trajectory.get("info") or {}
    metadata = (result.get("agent_result") or {}).get("metadata") or {}
    trial.exit_status = str(info.get("exit_status") or metadata.get("exit_status") or "")
    trial.n_steps = int((info.get("model_stats") or {}).get("api_calls") or 0)
    events = read_events(path / "agent" / "events.jsonl")
    start = next((e for e in events if e.get("type") == "trial_start"), {})
    trial.steps, trial.n_format_errors, trial.timeout_unrecovered = trajectory_steps(
        trajectory.get("messages") or [], float(start.get("command_timeout") or STOCK_TIMEOUT_S))
    trial.blocks = [e for e in events if e.get("type") == "guardrail_block"]
    trial.cap_reached = any(e.get("type") == "cap_reached" for e in events)
    try:
        stdout = (path / "verifier" / "test-stdout.txt").read_text(errors="replace")
    except OSError:
        stdout = ""
    trial.verifier_lines = verifier_failures(stdout)
    if not archived and trial.reward is not None and trial.reward < 1:
        trial.labels = [label for label, _, test in RULES if test(trial)]
    return trial


def discover(run_dir: Path) -> list[Trial]:
    trials = []
    for config_dir in sorted(p for p in run_dir.iterdir() if p.is_dir()):
        for task_dir in sorted(p for p in config_dir.iterdir() if p.is_dir()):
            archived = bool(ARCHIVED.search(task_dir.name))
            task = ARCHIVED.split(task_dir.name)[0] if archived else task_dir.name
            for trial_dir in sorted(p for p in task_dir.iterdir() if p.is_dir() and "__" in p.name):
                trials.append(load_trial(config_dir.name, task, trial_dir, archived))
    return trials


def guardrail_rules(trial: Trial) -> str:
    counts = Counter(str(e.get("rule_id")) for e in trial.blocks)
    return ";".join(f"{rule}x{n}" for rule, n in sorted(counts.items()))


def evidence(trial: Trial) -> str:
    label = trial.primary
    verifier = trial.verifier_lines[0] if trial.verifier_lines else ""
    if label == "success":
        return ""
    if label == "archived_attempt":
        return f"archived infrastructure attempt ({trial.exception or 'no exception recorded'})"
    if label == "guardrail_blocked":
        first = trial.blocks[0] if trial.blocks else {}
        return (f"{trial.n_guardrail_blocks} guardrail block(s), first {first.get('rule_id')} at step "
                f"{first.get('step')}: {first_line(first.get('command', ''), 120)}")
    if label == "unparsable_tool_call":
        return f"RepeatedFormatError after {trial.n_format_errors} format errors in {trial.n_steps} calls"
    if label == "budget_exhausted":
        return f"exit {trial.exit_status or trial.exception}" + (" (cap_reached event)" if trial.cap_reached else "")
    if label == "timeout_no_recovery":
        return "command timed out; no command succeeded afterwards"
    return verifier[:200] or f"{trial.exit_status or 'no exit status'}; verifier printed nothing"


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def rows(trials: list[Trial], families: dict) -> list[dict]:
    return [{
        "config": t.config,
        "task": t.task,
        "family": (families.get(t.task) or {}).get("family", ""),
        "trial_id": t.path.name,
        "reward": "" if t.reward is None else round(t.reward, 4),
        "exit_status": t.exit_status,
        "primary_label": t.primary,
        "failure_type": t.failure_type,
        "all_labels": ";".join(t.labels),
        "guardrail_rules": guardrail_rules(t),
        "n_guardrail_blocks": t.n_guardrail_blocks,
        "n_format_errors": t.n_format_errors,
        "n_steps": t.n_steps,
        "evidence": evidence(t),
        "needs_review": "yes" if t.primary in ("guardrail_blocked", "unclassified") else "",
        "trial_path": rel(t.path),
    } for t in trials]


SUMMARY_LABELS = ["success", *LABEL_TYPE]


def summary(trials: list[Trial]) -> list[dict]:
    out = []
    for config in sorted({t.config for t in trials}) + ["all"]:
        subset = [t for t in trials if config in ("all", t.config)]
        counts = Counter(t.primary for t in subset)
        kinds = Counter(t.failure_type for t in subset)
        out.append({"config": config,
                    "scored": sum(1 for t in subset if t.failure_type != "excluded"),
                    "excluded": kinds["excluded"],
                    **{label: counts[label] for label in SUMMARY_LABELS},
                    "harness_level": kinds["harness"], "model_level": kinds["model"]})
    return out


def to_csv(records: list[dict]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(records[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(records)
    return buffer.getvalue()


TRIGGERS = {
    "guardrail_blocked": re.compile(r"^(BLOCKED|REJECTED) \[[GU]-", re.M),
    "timeout_no_recovery": re.compile(r"timed out", re.I),
}


def key_steps(trial: Trial, label: str) -> list[tuple[int, Step]]:
    """3-6 steps that show the failure: around the first trigger, else the last steps."""
    numbered = list(enumerate(trial.steps, 1))
    pattern = TRIGGERS.get(label)
    hit = next((i for i, (_, s) in enumerate(numbered) if pattern and pattern.search(s.output)), None)
    if hit is None:
        return numbered[-4:]
    picked = numbered[max(0, hit - 1):hit + 4]
    return picked if numbered[-1] in picked else picked[:5] + numbered[-1:]


def quote(step: Step, lines: int = 3, width: int = 160) -> str:
    command = first_line(step.command, width)
    if len(step.command.splitlines()) > 1:
        command += f"  [+{len(step.command.splitlines()) - 1} lines]"
    output = [line[:width] for line in step.output.splitlines() if line.strip()][:lines]
    return "\n".join(["    $ " + command] + ["    > " + line for line in output or ["(no output)"]])


def clarity(trial: Trial) -> tuple:
    """Fewest competing labels, then fewest format errors (noise, unless that is the label),
    then the shortest trajectory, then a stable name order."""
    noise = 0 if trial.primary == "unparsable_tool_call" else trial.n_format_errors
    return (len(trial.labels), noise, trial.n_steps, trial.config, trial.task)


def examples(trials: list[Trial], row_by_trial: dict[int, dict]) -> str:
    out = ["# Failure classification: candidate example trials", "",
           "Generated by `scripts/classify_failures.py`. Up to 3 candidates per label, ranked by",
           "clarity (fewest competing labels, then fewest format errors, then shortest trajectory),",
           "at most one per task.",
           "Key steps are quoted from `agent/mini-swe-agent.trajectory.json`, truncated.", ""]
    for label in LABEL_TYPE:
        matching = sorted((t for t in trials if t.primary == label), key=clarity)
        out += [f"## {label} ({LABEL_TYPE[label]}, {len(matching)} trials)", ""]
        seen: set[str] = set()
        picked = [t for t in matching if not (t.task in seen or seen.add(t.task))][:3]
        if not picked:
            secondary = [f"{t.config}/{t.task}" for t in trials if label in t.labels[1:]]
            out += [("No trials with this primary label; secondary label in: " + ", ".join(secondary))
                    if secondary else "No trials.", ""]
        for n, trial in enumerate(picked, 1):
            row = row_by_trial[id(trial)]
            out += [f"### {label} {n}: {trial.config} / {trial.task}", "",
                    f"- Path: `{row['trial_path']}`",
                    f"- Reward {row['reward']}, exit `{trial.exit_status or '-'}`, "
                    f"{trial.n_steps} model calls, {trial.n_format_errors} format errors",
                    f"- All labels: {row['all_labels']}",
                    f"- Why: {row['evidence']}", "", "```text"]
            out += [f"step {i}:\n{quote(step)}" for i, step in key_steps(trial, label)]
            out += ["```", ""]
    return "\n".join(out)


def table(summary_rows: list[dict]) -> str:
    configs = [r["config"] for r in summary_rows]
    labels = ["scored", "excluded", *SUMMARY_LABELS, "harness_level", "model_level"]
    lines = [f"{'label':32}" + "".join(f"{c:>7}" for c in configs)]
    for label in labels:
        lines.append(f"{label:32}" + "".join(f"{r[label]:>7}" for r in summary_rows))
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("run_dir", nargs="?", type=Path, default=DEFAULT_RUN)
    ap.add_argument("--out", type=Path, help="output folder (default: mirror RUN_DIR under results/analysis)")
    args = ap.parse_args()
    run_dir = args.run_dir.resolve()
    if not run_dir.is_dir():
        ap.error(f"no such run folder: {args.run_dir}")
    out = args.out
    if out is None:
        try:
            out = ROOT / "results" / "analysis" / run_dir.relative_to(ROOT / "results") / "failures"
        except ValueError:
            ap.error("RUN_DIR is outside results/; pass --out")
    trials = discover(run_dir)
    if not trials:
        ap.error(f"no trials under {run_dir}")
    families = read_json(FAMILIES).get("tasks", {})
    records = rows(trials, families)
    summary_rows = summary(trials)
    out.mkdir(parents=True, exist_ok=True)
    (out / "trials_classified.csv").write_text(to_csv(records))
    (out / "summary.csv").write_text(to_csv(summary_rows))
    (out / "examples.md").write_text(examples(trials, {id(t): r for t, r in zip(trials, records)}))
    print(table(summary_rows))
    review = [r for r in records if r["needs_review"]]
    print(f"\n{len(review)} trial(s) need manual review (guardrail_blocked or unclassified); "
          f"see {rel(out / 'trials_classified.csv')}")


if __name__ == "__main__":
    main()
