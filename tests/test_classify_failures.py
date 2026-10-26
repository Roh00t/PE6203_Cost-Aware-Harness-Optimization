"""Failure classification on tiny synthetic trial folders (scripts/classify_failures.py)."""

import csv
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("classify_failures", ROOT / "scripts" / "classify_failures.py")
cf = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = cf  # dataclasses resolve string annotations through sys.modules
spec.loader.exec_module(cf)

SUBMIT = "echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT"


def step(command: str, output: str = "ok", returncode: int = 0, exception: str = "") -> list[dict]:
    return [
        {"role": "assistant", "content": None, "extra": {"actions": [{"command": command}]}},
        {"role": "tool", "content": output,
         "extra": {"raw_output": output, "returncode": returncode, "exception_info": exception}},
    ]


# An accepted submission has no observation: mini-swe-agent raises Submitted before recording one.
SUBMITTED = [{"role": "assistant", "content": None, "extra": {"actions": [{"command": SUBMIT}]}}]

FORMAT_ERROR = {"role": "user", "content": "Tool call error: no tool calls",
                "extra": {"interrupt_type": "FormatError",
                          "response": {"choices": [{"message": {"content": "I cannot do that."}}]}}}


def make_trial(run: Path, *, config: str = "v", task: str = "001-task", trial_id: str = "abc",
               reward: float | None = 0.0, exit_status: str = "Submitted",
               stdout: str = "", messages: list[dict] | None = None,
               events: list[dict] | None = None, task_folder: str | None = None) -> Path:
    """One trial folder; events=None means a stock (B0/E) trial without events.jsonl."""
    trial = run / config / (task_folder or task) / f"{task}__{trial_id}"
    (trial / "agent").mkdir(parents=True)
    (trial / "verifier").mkdir()
    if reward is not None:
        (trial / "verifier" / "reward.txt").write_text(str(reward))
    (trial / "verifier" / "test-stdout.txt").write_text(stdout)
    (trial / "result.json").write_text(json.dumps({"task_name": f"local/{task}", "exception_info": None}))
    if messages is None:
        messages = step("ls /app") + SUBMITTED
    history = [{"role": "system", "content": "sys"}, {"role": "user", "content": "task"}, *messages]
    calls = sum(1 for m in messages if m["role"] == "assistant" or m.get("extra", {}).get("interrupt_type"))
    (trial / "agent" / "mini-swe-agent.trajectory.json").write_text(json.dumps({
        "info": {"exit_status": exit_status, "model_stats": {"api_calls": calls}},
        "messages": history}))
    if events is not None:
        (trial / "agent" / "events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in events))
    return trial


def classify(run: Path) -> dict[str, cf.Trial]:
    return {f"{t.config}/{t.path.parent.name}": t for t in cf.discover(run)}


def only(run: Path) -> cf.Trial:
    (trial,) = cf.discover(run)
    return trial


BLOCK = {"type": "guardrail_block", "rule_id": "U-FMT-03", "step": 1, "command": "cat <<EOF"}
MISSING = "AssertionError: Missing required file: /app/out/result.csv\n"
WRONG = "E       AssertionError: expected 6 rows, got 5\nE       assert 5 == 6\n1 failed\n"
TIMEOUT = step("sleep 999", "", 137, "Command timed out or was killed")

# label -> (trial that must get it as primary, similar trial that must not get it at all)
CASES = {
    "guardrail_blocked": (dict(events=[BLOCK, BLOCK]),
                          dict(events=[{**BLOCK, "type": "guardrail_log", "rule_id": "U-INT-05"}],
                               stdout=WRONG)),
    "unparsable_tool_call": (dict(exit_status="RepeatedFormatError", messages=[FORMAT_ERROR] * 3),
                             dict(exit_status="Submitted", stdout=WRONG)),
    "budget_exhausted": (dict(exit_status="LimitsExceeded", events=[{"type": "cap_reached", "limit": "steps"}]),
                         dict(exit_status="Submitted", stdout=WRONG, events=[])),
    "timeout_no_recovery": (dict(exit_status="Submitted", messages=TIMEOUT + SUBMITTED),
                            dict(exit_status="Submitted", stdout=WRONG,
                                 messages=TIMEOUT + step("ls", "out.csv") + SUBMITTED)),
    "premature_submit_missing_output": (dict(stdout=MISSING), dict(stdout=WRONG)),
    "wrong_output": (dict(stdout=WRONG), dict(stdout="")),
    "partial_credit": (dict(reward=0.33, stdout=""), dict(reward=0.0, stdout="")),
}


@pytest.mark.parametrize("label", list(CASES))
def test_each_label_has_a_positive_and_a_negative_case(tmp_path, label):
    positive, negative = CASES[label]
    make_trial(tmp_path / "pos", **positive)
    make_trial(tmp_path / "neg", **negative)
    hit, miss = only(tmp_path / "pos"), only(tmp_path / "neg")
    assert hit.primary == label
    assert label not in miss.labels
    assert hit.failure_type == dict((n, k) for n, k, _ in cf.RULES)[label]


def test_rule_table_covers_the_agreed_taxonomy_in_precedence_order():
    assert [label for label, _, _ in cf.RULES] == [
        "guardrail_blocked", "unparsable_tool_call", "budget_exhausted", "timeout_no_recovery",
        "premature_submit_missing_output", "wrong_output", "partial_credit"]
    assert {kind for _, kind, _ in cf.RULES} == {"harness", "model"}


def test_success_and_unclassified(tmp_path):
    make_trial(tmp_path, task="001-solved", reward=1.0, exit_status="RepeatedFormatError")
    make_trial(tmp_path, task="002-silent", reward=0.0, stdout="")
    trials = classify(tmp_path)
    solved, silent = trials["v/001-solved"], trials["v/002-silent"]
    assert (solved.primary, solved.failure_type, solved.labels) == ("success", "success", [])
    assert (silent.primary, silent.failure_type) == ("unclassified", "unclassified")
    assert "verifier printed nothing" in cf.evidence(silent)


def test_precedence_keeps_every_matching_label(tmp_path):
    make_trial(tmp_path, reward=0.5, exit_status="RepeatedFormatError", events=[BLOCK],
               messages=TIMEOUT + [FORMAT_ERROR] * 3)
    trial = only(tmp_path)
    assert trial.labels == ["guardrail_blocked", "unparsable_tool_call", "timeout_no_recovery", "partial_credit"]
    row = cf.rows([trial], {})[0]
    assert row["primary_label"] == "guardrail_blocked"
    assert row["all_labels"] == "guardrail_blocked;unparsable_tool_call;timeout_no_recovery;partial_credit"
    assert row["guardrail_rules"] == "U-FMT-03x1"
    assert row["needs_review"] == "yes"


def test_archived_attempts_are_counted_but_never_scored(tmp_path):
    make_trial(tmp_path, task_folder="001-task.errored-20261026-000759", trial_id="old", reward=None)
    make_trial(tmp_path, task_folder="001-task.interrupted-20261026-014159", trial_id="old2")
    make_trial(tmp_path, stdout=WRONG)
    trials = cf.discover(tmp_path)
    assert sorted(t.primary for t in trials) == ["archived_attempt", "archived_attempt", "wrong_output"]
    assert {t.task for t in trials} == {"001-task"}
    (row,) = [r for r in cf.summary(trials) if r["config"] == "v"]
    assert (row["scored"], row["excluded"], row["wrong_output"], row["model_level"]) == (1, 2, 1, 1)


def test_stock_trial_without_events_counts_format_errors_from_the_trajectory(tmp_path):
    trial_dir = make_trial(tmp_path, config="b0", exit_status="RepeatedFormatError",
                           messages=step("ls") + [FORMAT_ERROR] * 3, events=None)
    assert not (trial_dir / "agent" / "events.jsonl").exists()
    trial = only(tmp_path)
    assert (trial.primary, trial.n_format_errors, trial.n_steps, trial.n_guardrail_blocks) == (
        "unparsable_tool_call", 3, 4, 0)
    assert "model wrote: I cannot do that." in trial.steps[1].command


def test_stock_timeout_message_counts_and_torn_event_line_is_skipped(tmp_path):
    stock_timeout = step("sleep 60", "", -1, "Command 'sleep 60' timed out after 30 seconds")
    trial_dir = make_trial(tmp_path, messages=stock_timeout + SUBMITTED, events=[BLOCK])
    with (trial_dir / "agent" / "events.jsonl").open("a") as log:
        log.write('{"type": "guardrail_bl')  # killed mid-write
    trial = only(tmp_path)
    assert trial.timeout_unrecovered and trial.n_guardrail_blocks == 1


def test_verifier_evidence_prefers_pytest_lines_then_assertions_then_last_line():
    assert cf.verifier_failures(WRONG) == ["AssertionError: expected 6 rows, got 5", "assert 5 == 6"]
    assert cf.verifier_failures("log\n" + MISSING + "done\n") == [MISSING.strip()]
    assert cf.verifier_failures("INFO: loaded result file\n\n") == ["INFO: loaded result file"]
    assert cf.verifier_failures("") == []


def test_new_config_folders_are_discovered_and_families_attached(tmp_path):
    make_trial(tmp_path, config="h0+c5", task="000-count-nuclei", stdout=MISSING)
    (row,) = cf.rows(cf.discover(tmp_path), {"000-count-nuclei": {"family": "Scientific"}})
    assert (row["config"], row["family"], row["primary_label"]) == (
        "h0+c5", "Scientific", "premature_submit_missing_output")


def test_key_steps_centre_on_the_guardrail_block(tmp_path):
    blocked = step("cat <<EOF", "REJECTED [U-FMT-03]: heredoc 'EOF' is never closed.", -1)
    messages = step("ls") * 5 + blocked + step("pwd") * 5 + SUBMITTED
    make_trial(tmp_path, events=[BLOCK], messages=messages)
    picked = [n for n, _ in cf.key_steps(only(tmp_path), "guardrail_blocked")]
    assert picked[:2] == [5, 6] and picked[-1] == 12 and 3 <= len(picked) <= 6


def test_cli_outputs_are_byte_identical_on_rerun(tmp_path):
    run = tmp_path / "run"
    make_trial(run, config="b0", task="001-a", exit_status="RepeatedFormatError", messages=[FORMAT_ERROR] * 3)
    make_trial(run, config="v", task="001-a", events=[BLOCK], stdout=WRONG)
    make_trial(run, config="v", task="002-b", reward=1.0)
    make_trial(run, config="v", task_folder="002-b.errored-20261026-000000", task="002-b", trial_id="x")
    outputs = []
    for name in ("first", "second"):
        out = tmp_path / name
        done = subprocess.run([sys.executable, str(ROOT / "scripts" / "classify_failures.py"), str(run),
                               "--out", str(out)], capture_output=True, text=True, check=True)
        table = done.stdout.split("\n\n")[0]  # the closing line names --out, which differs
        outputs.append({p.name: p.read_bytes() for p in sorted(out.iterdir())} | {"table": table})
    assert outputs[0] == outputs[1]
    assert set(outputs[0]) == {"trials_classified.csv", "summary.csv", "examples.md", "table"}
    rows = list(csv.DictReader((tmp_path / "first" / "trials_classified.csv").open()))
    assert list(rows[0]) == cf.COLUMNS
    assert [r["primary_label"] for r in rows] == [
        "unparsable_tool_call", "guardrail_blocked", "success", "archived_attempt"]
    examples = (tmp_path / "first" / "examples.md").read_text()
    assert "## guardrail_blocked (harness, 1 trials)" in examples and "v / 001-a" in examples
    assert "unparsable_tool_call" in outputs[0]["table"]


def test_cli_requires_out_outside_results(tmp_path):
    make_trial(tmp_path / "run")
    done = subprocess.run([sys.executable, str(ROOT / "scripts" / "classify_failures.py"), str(tmp_path / "run")],
                          capture_output=True, text=True)
    assert done.returncode != 0 and "--out" in done.stderr
