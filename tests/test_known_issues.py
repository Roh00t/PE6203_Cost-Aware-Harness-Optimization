"""Known harness bugs found in review, reproduced against the real (frozen) code.

Each xfail test asserts the *correct* behaviour, so it fails today and is reported as xfailed;
`raises` pins the expected failure, so a broken test setup still shows up as an error.
strict=True makes it fail loudly once the bug is fixed: then drop the marker. The plain tests
next to them are controls that must keep passing after any fix. Write-up and proposed diffs:
docs/harness_bug_review.md (issue numbers below match it).
"""

import json
import os
import subprocess
import time
from types import SimpleNamespace
from unittest.mock import Mock

import litellm
import pytest

from harness.components.budget import BudgetManager, CostCapExceeded
from harness.components.context import ContextManager
from harness.components.recovery import FailureRecovery
from harness.components.submit_gate import SubmissionGate, extract_paths
from harness.config import load_config
from harness.gateway import OpenRouterGateway
from harness.guardrails import check_command
from harness.hooks import RunState, Services
from harness.isha_adapter import IshaGuardrail
from harness.loop import HarnessAgent
from harness.telemetry import JsonlLog


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    monkeypatch.setattr(litellm, "completion", Mock(side_effect=AssertionError("Tests must not call a paid API")))


class Events:
    def __init__(self):
        self.rows = []

    def write(self, **row):
        self.rows.append(row)


def rule(command: str) -> str | None:
    return check_command(command, c2_enabled=True).rule_id


def state(step: int = 1, components: frozenset[str] = frozenset({"C2", "C4"})) -> RunState:
    return RunState("task", step, 0.0, 60.0, components)


# --- 1. U-FMT-03 scans heredoc bodies and quoted strings -----------------------------------------

@pytest.mark.xfail(strict=True, raises=AssertionError, reason="#1 U-FMT-03 treats << inside heredoc bodies, strings and arithmetic as heredocs")
@pytest.mark.parametrize("command", [
    "python3 - <<'PY'\nprint(1 << 3)\nPY",
    "ruby <<'RB'\nitems = []\nitems << 1\nRB",
    "bash -lc \"python3 - <<'PY'\nprint('hi')\nPY\"",
    "ruby -e \"File.open('out.txt', 'w') { |f| f << data }\"",
    "cat <<< hello",
    "echo $(( 1 << 3 ))",
], ids=["python-shift", "ruby-append", "nested-bash-lc", "ruby-e-string", "here-string", "arithmetic"])
def test_valid_commands_are_not_rejected_as_unterminated_heredocs(command):
    assert rule(command) != "U-FMT-03"


@pytest.mark.parametrize("command, expected", [
    ("cat <<'EOF' > out.txt\nhello", "U-FMT-03"),
    ("cat <<'EOF' > out.txt\nhello\nEOF", None),
    ("cat <<-EOF > out.txt\n\thello\n\tEOF", None),
])
def test_unterminated_heredoc_control(command, expected):
    assert rule(command) == expected


# --- 2. U-INT-04 matches .ssh paths and ssh-* tools ----------------------------------------------

@pytest.mark.xfail(strict=True, raises=AssertionError, reason="#2 U-INT-04 \\bssh\\b matches ~/.ssh paths and ssh-keygen")
@pytest.mark.parametrize("command", [
    "ls -la ~/.ssh", "cat /home/user/.ssh/config", "ssh-keygen -t ed25519 -N '' -f /tmp/key"])
def test_ssh_paths_and_tools_are_not_password_prompts(command):
    assert rule(command) != "U-INT-04"


@pytest.mark.parametrize("command, expected", [
    ("ssh user@host", "U-INT-04"), ("scp f.txt host:/tmp", "U-INT-04"),
    ("ssh -o BatchMode=yes host true", None)])
def test_ssh_control(command, expected):
    assert rule(command) == expected


# --- 3. U-INT-03 blocks the piped input its own message recommends ------------------------------

@pytest.mark.xfail(strict=True, raises=AssertionError, reason="#3 U-INT-03 blocks 'cat script.py | python3' though its message says to pipe input in")
@pytest.mark.parametrize("command", ["cat script.py | python3", "echo 'print(1)' | python3"])
def test_piped_interpreter_is_allowed(command):
    assert rule(command) is None


def test_bare_interpreter_control():
    result = check_command("python3", c2_enabled=True)
    assert result.rule_id == "U-INT-03" and "pipe input in" in result.message
    assert rule("cd /app && python3") == "U-INT-03"


# --- 4. C5 path extraction ------------------------------------------------------------------------

@pytest.mark.xfail(strict=True, raises=AssertionError, reason="#4 extract_paths truncates hyphenated extensions")
def test_hyphenated_extension_is_kept():
    assert extract_paths("Save the workspace as `/app/project.code-workspace`.") == ["/app/project.code-workspace"]


@pytest.mark.xfail(strict=True, raises=AssertionError, reason="#4 extract_paths drops the ~ of home-relative paths")
def test_home_relative_path_is_not_turned_into_a_root_path():
    assert "/Desktop/out.png" not in extract_paths("Save the image to ~/Desktop/out.png.")


@pytest.mark.xfail(strict=True, raises=AssertionError, reason="#4 C5 reports an unmodified input file as missing")
def test_gate_does_not_call_an_existing_input_missing(tmp_path):
    class LocalShell:
        """Runs the gate's real check commands against real files in tmp_path."""

        def execute(self, action):
            done = subprocess.run(["bash", "-c", action["command"]], capture_output=True, text=True)
            return {"output": done.stdout + done.stderr, "returncode": done.returncode}

    source, result = tmp_path / "input" / "data.csv", tmp_path / "output" / "summary.json"
    for path in (source, result):
        path.parent.mkdir()
        path.write_text("x")
    started = time.time()
    os.utime(source, (started - 3600, started - 3600))  # an input, older than the trial
    gate = SubmissionGate(Services(environment=LocalShell(), events=Events(), config=SimpleNamespace(step_limit=50)),
                          trial_started_at=started - 60)
    decision = gate.before_submit({}, RunState(f"Read {source} and save the summary to {result}.", 5, 0.0, 60.0,
                                               frozenset({"C5"})))
    assert f"✓ {result}" in decision.feedback
    assert f"✗ {source}" not in decision.feedback


def test_extract_paths_control():
    assert extract_paths("Write `/app/out dir/report.docx`, /app/x.txt and /app/notes.tar.gz") == [
        "/app/out dir/report.docx", "/app/x.txt", "/app/notes.tar.gz"]


# --- 5. Gateway reserves the worst case for unbilled 429 rejections -------------------------------

def gateway(tmp_path, responses, budget_usd):
    _, stock = load_config("configs/harness/V.yaml")
    price = {"provider": "Darkbloom", "prompt_usd_per_mtok": 0.018, "completion_usd_per_mtok": 0.09}
    calls = JsonlLog(tmp_path / "calls.jsonl", {"config_id": "test", "task_id": "synthetic", "trial_id": "t"})
    stop = Mock()
    stop.is_set.return_value = False
    stop.wait.return_value = False  # no real backoff sleeps
    model = OpenRouterGateway(calls=calls, events=Events(), price=price, stop_event=stop,
                              budget_usd=budget_usd, **stock["model"])
    model._call_api = Mock(side_effect=responses)
    return model


def ok_response():
    return litellm.ModelResponse(
        model="openai/gpt-oss-20b", provider="Darkbloom",
        choices=[{"finish_reason": "tool_calls", "message": {"role": "assistant", "content": "", "tool_calls": [
            {"id": "c1", "type": "function", "function": {"name": "bash", "arguments": json.dumps({"command": "ls"})}}]}}],
        usage={"prompt_tokens": 10_000, "completion_tokens": 100})


@pytest.mark.xfail(strict=True, raises=CostCapExceeded, reason="#5 each unbilled 429 attempt keeps its full reservation against B_task")
def test_rate_limited_attempts_do_not_exhaust_the_task_budget(tmp_path):
    rate_limited = litellm.RateLimitError(message="429", model="openai/gpt-oss-20b", llm_provider="openrouter")
    model = gateway(tmp_path, [rate_limited] * 8 + [ok_response()], budget_usd=0.01)
    history = [{"role": "user", "content": "x" * 40_000}]  # a mid-trial prompt, about 10k tokens
    for _ in range(2):  # two steps, each losing all 4 attempts to 429s; nothing is billed
        with pytest.raises(litellm.RateLimitError):
            model.query(history)
    assert model.query(history)["extra"]["actions"]


def test_server_error_keeps_its_reservation_control(tmp_path):
    """A 5xx may have been billed, so its worst-case reservation must stay (fixed or not)."""
    server_error = litellm.InternalServerError(message="502", model="openai/gpt-oss-20b", llm_provider="openrouter")
    model = gateway(tmp_path, [server_error] * 4, budget_usd=None)
    history = [{"role": "user", "content": "x" * 40_000}]
    reserve = model.request_reserve(model._prepare_messages_for_api(history))
    with pytest.raises(litellm.InternalServerError):
        model.query(history)
    assert model.unknown_reserved == 4 * reserve and model.spent == 0
    assert 0.0014 < float(reserve) < 0.0017  # about 1/6 of B_task = $0.01 per failed attempt


# --- 6. C2 file tools bypass every guardrail, including G-INT-01 ---------------------------------

def guarded(action):
    agent = SimpleNamespace(guardrail=IshaGuardrail(), events=Events(), hooks=[], guardrail_blocks=0)
    return HarnessAgent.before_execute(agent, action, state())


@pytest.mark.xfail(strict=True, raises=AssertionError, reason="#6 read_file/search/write_file/edit_file skip G-INT-01 (loop.py checks bash only)")
def test_file_tool_cannot_read_grader_paths():
    assert not guarded({"tool": "read_file", "arguments": {"path": "/tests/test_outputs.py"}}).allowed


def test_bash_grader_path_control():
    assert not guarded({"command": "cat /tests/test_outputs.py"}).allowed


# --- 7. C4 counts expected non-zero exits and never forgets them ---------------------------------

def run(hook: FailureRecovery, command: str, returncode: int) -> bool:
    """True if C4 let the command run; then record its result."""
    action = {"command": command}
    if not hook.before_execute(action, state()).allowed:
        return False
    hook.after_execute(action, {"output": "", "returncode": returncode, "extra": {}}, state())
    return True


@pytest.mark.xfail(strict=True, raises=AssertionError, reason="#7 C4 blocks a polling probe forever, even after the state changed")
@pytest.mark.parametrize("probe, change", [
    ("test -f /tmp/out.txt", "touch /tmp/out.txt"),
    ("grep -q done /tmp/job.log", "echo done >> /tmp/job.log"),
    ("pkill -f soffice", "soffice --headless &"),
])
def test_probe_runs_again_after_a_state_change(probe, change):
    hook = FailureRecovery(Events())
    assert run(hook, probe, 1) and run(hook, probe, 1)
    assert run(hook, change, 0)
    assert run(hook, probe, 0)


def test_repeat_intercept_control():
    hook = FailureRecovery(Events())
    assert run(hook, "python3 broken.py", 1) and run(hook, "python3 broken.py", 1)
    assert not run(hook, "python3   broken.py", 1)
    assert hook.events.rows[-1]["type"] == "repeat_intercept"


# --- 8. C1 offload overwrites harness_chars added by C2/C4 ---------------------------------------

@pytest.mark.xfail(strict=True, raises=AssertionError, reason="#8 C1 offload replaces earlier harness_chars with the stub length")
def test_offload_keeps_earlier_harness_chars():
    env = SimpleNamespace(write_text=lambda path, text: None)
    manager = ContextManager(SimpleNamespace(offload_chars=2000), env, Events())
    result = manager.offload({"output": "x" * 5000, "returncode": 0, "extra": {"harness_chars": 189}}, 3)
    stub = len(result["output"]) - 1600  # the model sees 800 head + stub + 800 tail
    assert result["extra"]["harness_chars"] == 189 + stub


# --- 9. C3 status line rounds V-E's budget ---------------------------------------------------------

def status(budget_usd: float) -> str:
    manager = BudgetManager(SimpleNamespace(step_limit=50, budget_usd=budget_usd), Events())
    return manager.observation({"output": ""}, state(), 100)["output"]


@pytest.mark.xfail(strict=True, raises=AssertionError, reason="#9 the status line formats B_task with 2 decimals ($0.0167 shows as $0.02)")
def test_status_line_shows_the_exact_budget():
    assert "/$0.0167 " in status(0.0167)


def test_status_line_control():
    assert "/$0.01 " in status(0.01)
