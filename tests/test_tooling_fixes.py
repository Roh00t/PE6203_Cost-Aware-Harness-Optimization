"""Regression tests for the run-tooling and analysis fixes in docs/bug_fixes.md (BF-23 to BF-34)."""

import importlib.util
import json
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from harness.telemetry import origin_counts  # noqa: E402
from scripts.check_no_task_leak import find_leaks  # noqa: E402


def load(name):
    spec = importlib.util.spec_from_file_location(f"{name}_fixes_under_test", ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


run_state, runner, task_list = load("run_state"), load("run_all_configs"), load("task_list")
collect_costs, analysis = load("collect_costs"), load("analyze")


# --- BF-23 and BF-28: resume classification --------------------------------------------------

def job(tmp_path, *trials, finished=True):
    folder = tmp_path / "001-task"
    folder.mkdir()
    (folder / "result.json").write_text(json.dumps({"finished_at": "2026-10-25T00:00:00Z" if finished else None}))
    for index, trial in enumerate(trials):
        (folder / f"001-task__{index}").mkdir()
        text = trial if isinstance(trial, str) else json.dumps(trial)
        (folder / f"001-task__{index}" / "result.json").write_text(text)
    return folder


def trial(exception=None, reward=None):
    return {"exception_info": {"exception_type": exception} if exception else None,
            "verifier_result": {"rewards": {"reward": reward}} if reward is not None else None}


@pytest.mark.parametrize("trials, state", [
    ([trial(reward=1.0)], "finished"),
    ([trial("AgentTimeoutError", 1.0)], "finished"),        # scored budget outcome: never rerun
    ([trial("AgentTimeoutError", 0.0)], "finished"),
    ([trial("NonZeroAgentExitCodeError", 0.0)], "errored"),  # crashed agent install: infrastructure
    ([trial("RuntimeError")], "errored"),                    # Docker build or network
    ([trial("RuntimeError"), trial(reward=0.5)], "finished"),
    (['{"finished_at": "2026-10-25T00:00:00Z", "exce'], "interrupted"),  # killed mid-write
], ids=["scored", "timeout-scored", "timeout-zero", "agent-crash", "docker", "mixed", "damaged-json"])
def test_resume_state(tmp_path, trials, state):
    assert run_state.job_state(job(tmp_path, *trials)) == state


def test_unfinished_job_is_interrupted(tmp_path):
    assert run_state.job_state(job(tmp_path, trial(reward=1.0), finished=False)) == "interrupted"


def test_harbor_run_uses_the_tested_classifier():
    assert 'python3 scripts/run_state.py "$RUN_DIR/$id"' in (ROOT / "scripts/harbor_run.sh").read_text()


def test_trial_outcome_skips_a_damaged_result(tmp_path):
    folder = job(tmp_path, '{"finished_at": "x", "verif')
    assert runner.trial_outcome(folder)["exception"] == "no finished trial"


# --- BF-24: arguments after -- cannot bypass the gates ----------------------------------------

@pytest.mark.parametrize("extra", [
    ["-i", "000-count-nuclei"], ["--include-task-name", "x"], ["-p", "/tmp"], ["--n-concurrent", "4"],
    ["-n4"], ["-k", "4"], ["--config", "job.yaml"], ["--override-memory-mb=99999"], ["--no-delete"],
    ["--disable-verification"], ["--dataset", "other@1.0"],
])
def test_gate_bypassing_arguments_are_refused(extra):
    done = subprocess.run(["bash", str(ROOT / "scripts/harbor_run.sh"), "--split", "dev", "--mode", "oracle",
                           "--dry-run", "--", *extra], capture_output=True, text=True, cwd=ROOT)
    assert done.returncode == 1
    assert "would bypass this script's checks" in done.stderr


# --- BF-25: the unmodified-benchmark check sees added files ------------------------------------

@pytest.mark.parametrize("script", ["harbor_run.sh", "sample_tasks.py"])
def test_checkout_check_includes_untracked_files(script):
    text = (ROOT / "scripts" / script).read_text()
    assert "--untracked-files=all" in text and "--untracked-files=no" not in text


# --- BF-26: the leak checker reads model templates and non-UTF-8 files -----------------------

def leak_fixture(root: Path) -> Path:
    tasks = root / "benchmark" / "tasks"
    (tasks / "777-synthetic-task").mkdir(parents=True)
    (tasks / "777-synthetic-task" / "task.toml").write_text('[task]\nname = "synthetic"\n')
    (tasks / "777-synthetic-task" / "instruction.md").write_text("Create the output.\n")
    for folder in ("harness", "configs/harness", "configs/models"):
        (root / folder).mkdir(parents=True)
    return tasks


def test_task_id_in_a_model_template_is_a_leak(tmp_path):
    tasks = leak_fixture(tmp_path)
    (tmp_path / "configs/models/base.yaml").write_text("instance_template: solve 777-synthetic-task\n")
    assert [leak.value for leak in find_leaks(tmp_path, tasks)] == ["777-synthetic-task"]


def test_task_id_in_a_latin1_file_is_a_leak(tmp_path):
    tasks = leak_fixture(tmp_path)
    (tmp_path / "harness/notes.py").write_bytes("# caf\xe9 777-synthetic-task\n".encode("latin-1"))
    assert [leak.value for leak in find_leaks(tmp_path, tasks)] == ["777-synthetic-task"]


# --- BF-27 and BF-29: the amended list and the frozen fingerprints -----------------------------

def test_args_output_is_the_amended_eval_list():
    done = subprocess.run([sys.executable, str(ROOT / "scripts/task_list.py"), "eval", "--args"],
                          capture_output=True, text=True, check=True)
    ids = [line.removeprefix("-i ") for line in done.stdout.splitlines()]
    assert all(line.startswith("-i ") for line in done.stdout.splitlines())
    assert task_list.fingerprint(ids) == "973635ea4e6a477e2fbfffd1045494cb69e0678c02ceea2276c56c63fa0468b8"


def test_edited_subset_is_refused():
    subset = json.loads((ROOT / "configs/task_subset.json").read_text())
    amendments = json.loads((ROOT / "configs/subset_amendments.json").read_text())
    eval_ids, _ = task_list.apply_amendments(subset, amendments["amendments"])
    task_list.check_frozen(subset, amendments, eval_ids)  # the real configs pass
    edited = {**subset, "dev_task_ids": subset["dev_task_ids"][1:] + [subset["eval_task_ids"][0]]}
    with pytest.raises(SystemExit, match="dev split no longer matches"):
        task_list.check_frozen(edited, amendments, eval_ids)


# --- BF-28: Ctrl+C lets harbor_run.sh run its trap ---------------------------------------------

class Child:
    def __init__(self, hangs=False):
        self.hangs, self.terminated, self.waits = hangs, False, []

    def wait(self, timeout=None):
        self.waits.append(timeout)
        if len(self.waits) == 1:
            raise KeyboardInterrupt
        if self.hangs and not self.terminated:
            raise subprocess.TimeoutExpired("harbor_run.sh", timeout)
        return 130

    def terminate(self):
        self.terminated = True


@pytest.mark.parametrize("hangs", [False, True])
def test_ctrl_c_waits_for_the_child_trap(monkeypatch, hangs):
    child = Child(hangs)
    monkeypatch.setattr(runner.subprocess, "Popen", lambda *args, **kwargs: child)
    assert runner.run_child(["bash", "scripts/harbor_run.sh"], {}, grace_s=5) == 130
    assert child.waits[1] == 5
    assert child.terminated is hangs  # terminated only if it outlives the grace period


# --- BF-30: export leaves out symlinks and media files -----------------------------------------

def test_export_skips_symlinks_and_images_outside_artifacts(tmp_path):
    secret = tmp_path / "host_file.txt"
    secret.write_text("not part of the run")
    trial_dir = tmp_path / "run" / "001-task" / "001-task__abc"
    (trial_dir / "agent").mkdir(parents=True)
    (trial_dir / "result.json").write_text(json.dumps({
        "task_name": "local/001-task", "trial_name": "001-task__abc", "finished_at": "2026-10-25T00:00:00Z",
        "verifier_result": {"rewards": {"reward": 1.0}}}))
    (trial_dir / "agent" / "trial.log").write_text("log")
    (trial_dir / "agent" / "screenshot.png").write_bytes(b"\x89PNG")
    (trial_dir / "agent" / "hosts.txt").symlink_to(secret)
    dest = tmp_path / "out"
    done = subprocess.run([sys.executable, str(ROOT / "scripts/export_run.py"), str(tmp_path / "run"), str(dest)],
                          capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
    exported = {p.name for p in dest.rglob("*") if p.is_file()}
    assert "trial.log" in exported and "result.json" in exported
    assert "screenshot.png" not in exported and "hosts.txt" not in exported


# --- BF-32: scored agent timeouts and a tight cost cross-check --------------------------------

def timed_out_trial(tmp_path, exception):
    path = tmp_path / "b0" / "001-task" / "001-task__abc" / "result.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({
        "task_name": "local/001-task", "trial_name": "001-task__abc", "finished_at": "2026-10-25T00:00:00Z",
        "exception_info": {"exception_type": exception}, "verifier_result": {"rewards": {"reward": 1.0}}}))
    table = json.loads((ROOT / "configs/pricing.json").read_text())
    return analysis.load_trial(path, table, {"001-task": {"family": "A"}}, {"001-task"}, "B0",
                               ROOT / "configs/pricing.json")


def test_agent_timeout_with_a_reward_is_scored(tmp_path):
    assert timed_out_trial(tmp_path, "AgentTimeoutError")["scored"] is True


def test_infrastructure_exception_is_not_scored(tmp_path):
    assert timed_out_trial(tmp_path, "RuntimeError")["scored"] is False


def call(step, prompt=1000, origins=None, cost_reported=None):
    return {"call_idx": step, "step": step, "model": "openai/gpt-oss-20b", "provider": "Darkbloom",
            "provider_expected": "Darkbloom", "purpose": "agent", "prompt_tokens": prompt,
            "completion_tokens": 10, "prompt_chars_by_origin": origins}


def write_trial(tmp_path, calls, recorded=None, messages=None):
    agent = tmp_path / "trial" / "agent"
    agent.mkdir(parents=True)
    (agent / "calls.jsonl").write_text("".join(json.dumps(c) + "\n" for c in calls))
    if messages is not None:
        (agent / "mini-swe-agent.trajectory.json").write_text(json.dumps({"messages": messages}))
    if recorded is not None:
        (agent.parent / "result.json").write_text(json.dumps(
            {"agent_result": {"metadata": {"known_cost_table_usd": recorded}}}))
    return agent / "calls.jsonl"


def summarize(log):
    return collect_costs.summarize(log, model="openai/gpt-oss-20b", provider="Darkbloom",
                                   pricing=ROOT / "configs/pricing.json")


def test_cross_check_allows_one_late_call_only(tmp_path):
    one = (Decimal(1000) * Decimal("0.018") + Decimal(10) * Decimal("0.09")) / Decimal(1000000)
    log = write_trial(tmp_path / "late", [call(1), call(2)], recorded=str(one))  # second call logged late
    assert summarize(log)["cost_crosscheck_passed"] is True
    log = write_trial(tmp_path / "off", [call(1), call(2)], recorded="0.005")  # v1 tolerated $0.01
    with pytest.raises(ValueError, match="Trial known cost mismatch"):
        summarize(log)


# --- BF-34: format-error feedback is not harness overhead --------------------------------------

def feedback_message(text):
    return {"role": "user", "content": text, "extra": {"interrupt_type": "FormatError"}}


def test_v1_logs_move_format_error_feedback_out_of_harness(tmp_path):
    feedback = feedback_message("REJECTED: no valid bash tool call found (stop).")
    chars = len(json.dumps({k: v for k, v in feedback.items() if k != "extra"}, ensure_ascii=False))
    messages = [{"role": "system", "content": "s"}, {"role": "user", "content": "task"}, feedback,
                {"role": "assistant", "content": "ok"}]
    # harness-v1 counted the feedback as harness text from step 2 on.
    log = write_trial(tmp_path, [call(1, origins={"task": 1000, "harness": 0}),
                                 call(2, origins={"task": 1000 - chars, "harness": chars})], messages=messages)
    report = summarize(log)
    assert Decimal(report["harness_injected_cost_usd_estimate"]) == 0
    assert Decimal(report["format_error_feedback_cost_usd_estimate"]) > 0
    assert report["format_error_feedback_separated"] is True


def test_v1_1_logs_record_feedback_under_its_own_origin():
    counts = origin_counts([{"role": "system", "content": "s"}, {"role": "user", "content": "task"},
                            feedback_message("try again") | {"extra": {"interrupt_type": "FormatError",
                                                                      "origin": "feedback"}}])
    assert counts["feedback"] > 0 and counts["harness"] == 0
