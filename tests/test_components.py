"""Offline tests for the independently ablatable C2, C4, and C5 plugins."""

import base64
import shlex
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from harness.components.recovery import FailureRecovery
from harness.components.submit_gate import SubmissionGate, extract_paths
from harness.components.tools import HELPER_PATH, ToolInterface
from harness.hooks import RunState, Services


class Events:
    def __init__(self):
        self.rows = []

    def write(self, **row):
        self.rows.append(row)


class FakeEnvironment:
    def __init__(self, root: Path):
        self.root = root
        self.commands = []
        self.helper_source = None
        self.file_checks = {}

    def write_text(self, path: str, text: str) -> None:
        assert path == HELPER_PATH
        self.helper_source = text

    def execute(self, action: dict) -> dict:
        command = action["command"]
        self.commands.append(command)
        if command.startswith("python3 " + HELPER_PATH + " "):
            if self.helper_source is None:
                return {
                    "output": "C2 helper was not uploaded",
                    "returncode": 1,
                    "exception_info": "",
                }
            encoded = shlex.split(command)[-1]
            assert base64.b64decode(encoded, validate=True)
            result = subprocess.run(
                [sys.executable, "-c", self.helper_source, encoded],
                cwd=self.root,
                capture_output=True,
                check=False,
                text=True,
            )
            return {
                "output": result.stdout.strip() or result.stderr.strip(),
                "returncode": result.returncode,
                "exception_info": "",
            }
        path = next((key for key in self.file_checks if key in command), None)
        return {
            "output": "",
            "returncode": self.file_checks.get(path, 1),
            "exception_info": "",
        }


def make_services(tmp_path: Path, *, components=(), step_limit=50):
    environment = FakeEnvironment(tmp_path)
    events = Events()
    config = SimpleNamespace(
        config_id="test", components=list(components), step_limit=step_limit
    )
    return Services(environment, events, config)


def state(*, task="", step=1, components=()):
    return RunState(task, step, 0.0, 0.0, frozenset(components))


def test_c2_advertises_four_tools_and_uploads_generic_helper(tmp_path: Path):
    services = make_services(tmp_path, components={"C2"})
    plugin = ToolInterface(services)

    assert plugin.components == frozenset({"C2"})
    assert [tool["function"]["name"] for tool in plugin.tools] == [
        "read_file",
        "write_file",
        "edit_file",
        "search",
    ]
    assert services.environment.helper_source is not None
    assert "MAX_HITS = 100" in services.environment.helper_source


def test_c2_reads_numbered_lines_and_caps_the_range(tmp_path: Path):
    services = make_services(tmp_path, components={"C2"})
    plugin = ToolInterface(services)
    (tmp_path / "notes.txt").write_text("alpha\nbeta\ngamma\n", encoding="utf-8")

    result = plugin.execute_tool(
        {"tool": "read_file", "arguments": {"path": "notes.txt", "start_line": 2}},
        state(components={"C2"}),
    )

    assert result["returncode"] == 0
    assert result["output"] == "2: beta\n3: gamma"
    assert result["extra"]["origin"] == "env"
    assert "notes.txt" not in services.environment.commands[0]


def test_c2_write_and_edit_require_one_unique_match(tmp_path: Path):
    plugin = ToolInterface(make_services(tmp_path, components={"C2"}))
    path = str(tmp_path / "folder with spaces" / "report 'final'.txt")

    written = plugin.execute_tool(
        {"tool": "write_file", "arguments": {"path": path, "content": "old\nold\n"}},
        state(components={"C2"}),
    )
    ambiguous = plugin.execute_tool(
        {"tool": "edit_file", "arguments": {"path": path, "old": "old", "new": "new"}},
        state(components={"C2"}),
    )

    assert written["returncode"] == 0
    assert "found 2" in ambiguous["output"]
    assert (Path(path)).read_text(encoding="utf-8") == "old\nold\n"

    (Path(path)).write_text("replace me\nkeep me\n", encoding="utf-8")
    edited = plugin.execute_tool(
        {
            "tool": "edit_file",
            "arguments": {"path": path, "old": "replace me", "new": "updated"},
        },
        state(components={"C2"}),
    )
    assert edited["returncode"] == 0
    assert (Path(path)).read_text(encoding="utf-8") == "updated\nkeep me\n"


def test_c2_search_returns_file_line_hits_and_caps_at_100(tmp_path: Path):
    services = make_services(tmp_path, components={"C2"})
    plugin = ToolInterface(services)
    source = tmp_path / "source"
    source.mkdir()
    (source / "matches.txt").write_text("".join("match\n" for _ in range(101)), encoding="utf-8")
    (source / "ignored.bin").write_bytes(b"\xff\x00")

    result = plugin.execute_tool(
        {
            "tool": "search",
            "arguments": {"pattern": "^match$", "path": str(source), "glob": "*.txt"},
        },
        state(components={"C2"}),
    )

    assert result["returncode"] == 0
    assert result["output"].count("matches.txt:") == 100
    assert "Results capped at 100 hits." in result["output"]
    assert "ignored.bin" not in result["output"]


@pytest.mark.parametrize(
    ("name", "arguments", "message"),
    [
        ("read_file", {"path": "x", "start_line": True}, "start_line: Input should be a valid integer"),
        ("read_file", {"path": "x", "start_line": 0}, "line numbers must be positive integers"),
        ("read_file", {"path": "x", "start_line": 1, "end_line": 202}, "limited to 200 lines"),
        ("read_file", {"path": "x", "unexpected": 1}, "Unexpected argument"),
        ("write_file", {"path": "x"}, "Missing argument"),
        ("edit_file", {"path": "x", "old": "", "new": "y"}, "old must be non-empty"),
        ("search", {"path": "x", "pattern": "["}, "not a valid regular expression"),
    ],
)
def test_c2_rejects_invalid_arguments_before_container_execution(
    tmp_path: Path, name: str, arguments: dict, message: str
):
    services = make_services(tmp_path, components={"C2"})
    plugin = ToolInterface(services)

    result = plugin.execute_tool({"tool": name, "arguments": arguments}, state())

    assert result["returncode"] == 1
    assert message in result["output"]
    assert "example:" in result["output"]
    assert services.environment.commands == []
    assert result["extra"]["origin"] == "harness"


def test_c2_missing_tool_call_feedback_uses_documented_message():
    plugin = ToolInterface(make_services(Path.cwd(), components={"C2"}))

    feedback = plugin.on_missing_tool_call(
        {"choices": [{"finish_reason": "stop"}]}, state(components={"C2"})
    )

    assert feedback == (
        "REJECTED: no valid bash tool call found (stop). "
        "Reply with brief reasoning and exactly one bash tool call."
    )


def test_c4_allows_two_attempts_then_intercepts_whitespace_equivalent_command():
    events = Events()
    recovery = FailureRecovery(events)
    first_action = {"command": "  make   build "}
    repeated_action = {"command": "make build"}

    assert recovery.before_execute(first_action, state()).allowed
    recovery.after_execute(first_action, {"output": "missing source", "returncode": 2}, state())
    assert recovery.before_execute(repeated_action, state()).allowed
    recovery.after_execute(repeated_action, {"output": "missing source", "returncode": 2}, state())

    decision = recovery.before_execute({"command": "make build"}, state(step=3))
    recovery.after_execute(
        {"command": "make build"},
        {"output": decision.feedback, "returncode": -1, "extra": {"origin": "harness"}},
        state(step=3),
    )

    assert not decision.allowed
    assert "Last error: missing source" in decision.feedback
    assert "state in one sentence why it failed" in decision.feedback
    assert next(iter(recovery.failures.values())) == 2
    assert [event["type"] for event in events.rows] == ["repeat_intercept"]
    assert recovery.before_execute({"command": "make clean"}, state()).allowed


def test_c4_counts_only_executed_failures_not_harness_intercepts():
    recovery = FailureRecovery(Events())
    action = {"command": "false"}
    for _ in range(2):
        recovery.after_execute(action, {"output": "failed", "returncode": 1}, state())
    blocked = recovery.before_execute(action, state())
    recovery.after_execute(
        action,
        {"output": blocked.feedback, "returncode": -1, "extra": {"origin": "harness"}},
        state(),
    )

    assert next(iter(recovery.failures.values())) == 2


def test_c4_stall_nudge_triggers_once_after_three_identical_observations():
    events = Events()
    recovery = FailureRecovery(events)
    action = {"command": "printf same"}
    results = [
        recovery.after_execute(action, {"output": "same", "returncode": 0}, state(step=i))
        for i in range(1, 5)
    ]

    assert "re-read the task" not in results[0]["output"]
    assert "re-read the task" not in results[1]["output"]
    assert "re-read the task" in results[2]["output"]
    assert "re-read the task" not in results[3]["output"]
    assert results[2]["extra"]["harness_chars"] > 0
    assert [event["type"] for event in events.rows] == ["stall_nudge"]


def test_c4_different_observation_breaks_stall_sequence():
    recovery = FailureRecovery(Events())
    action = {"command": "printf result"}
    outputs = ["same", "different", "same", "same"]

    results = [
        recovery.after_execute(action, {"output": output, "returncode": 0}, state(step=i))
        for i, output in enumerate(outputs, 1)
    ]

    assert all("re-read the task" not in result["output"] for result in results)


@pytest.mark.parametrize("returncode", [124, 137])
def test_c4_timeout_adds_background_recipe_and_logs_event(returncode: int):
    events = Events()
    recovery = FailureRecovery(events)

    result = recovery.after_execute(
        {"command": "long-running generic command"},
        {"output": "timed out", "returncode": returncode},
        state(),
    )

    assert "nohup CMD > /tmp/job.log 2>&1 &" in result["output"]
    assert "tail -n 50 /tmp/job.log" in result["output"]
    assert result["extra"]["harness_chars"] > 0


def test_c5_extracts_backticked_and_bare_absolute_file_paths():
    task = (
        "Read `/app/input/source.tar.gz`, write /app/output/result.txt, "
        "and visit https://example.com/page.html. "
        "The same file is `/app/output/result.txt`."
    )

    assert extract_paths(task) == ["/app/input/source.tar.gz", "/app/output/result.txt"]


def test_c5_first_submission_checks_paths_and_emits_checklist(tmp_path: Path):
    services = make_services(tmp_path, components={"C5"}, step_limit=50)
    services.environment.file_checks = {
        "/app/output/good.txt": 0,
        "/app/output/missing.txt": 1,
    }
    plugin = SubmissionGate(services, trial_started_at=100.0)
    task = "Create `/app/output/good.txt` and /app/output/missing.txt, then verify them."

    decision = plugin.before_submit({}, state(task=task, step=10, components={"C5"}))

    assert not decision.allowed
    assert "✓ /app/output/good.txt" in decision.feedback
    assert "✗ /app/output/missing.txt" in decision.feedback
    assert task in decision.feedback
    assert "reading the outputs back" in decision.feedback
    assert all(command.startswith("test -s ") for command in services.environment.commands)
    assert all("100.000000" in command for command in services.environment.commands)


def test_c5_submission_without_paths_still_gets_a_checklist(tmp_path: Path):
    services = make_services(tmp_path, components={"C5"})
    plugin = SubmissionGate(services, trial_started_at=100.0)

    decision = plugin.before_submit(
        {}, state(task="Change a browser setting and verify it.", step=1)
    )

    assert not decision.allowed
    assert "No absolute output file paths" in decision.feedback
    assert "reading the outputs back" in decision.feedback
    assert services.environment.commands == []


def test_c5_task_excerpt_is_limited_to_first_600_characters(tmp_path: Path):
    services = make_services(tmp_path, components={"C5"})
    services.environment.file_checks = {"/app/out.txt": 0}
    plugin = SubmissionGate(services, trial_started_at=100.0)
    task = "Create /app/out.txt. " + ("x" * 580) + "TASK-TAIL-MUST-NOT-APPEAR"

    decision = plugin.before_submit({}, state(task=task, step=1))

    assert task[:600] in decision.feedback
    assert task[600:] not in decision.feedback


def test_c5_only_holds_first_submission(tmp_path: Path):
    services = make_services(tmp_path, components={"C5"})
    plugin = SubmissionGate(services, trial_started_at=100.0)
    current_state = state(task="Check that the browser setting is correct.", step=1)

    first = plugin.before_submit({}, current_state)
    second = plugin.before_submit({}, current_state)

    assert not first.allowed
    assert second.allowed
    assert plugin.rejections == 1
    assert services.events.rows == []


@pytest.mark.parametrize("step", [45, 50])
def test_c5_does_not_gate_at_or_after_90_percent_of_steps(tmp_path: Path, step: int):
    services = make_services(tmp_path, components={"C5"}, step_limit=50)
    plugin = SubmissionGate(services, trial_started_at=100.0)

    decision = plugin.before_submit(
        {}, state(task="Create /app/output/result.txt.", step=step, components={"C5"})
    )

    assert decision.allowed
    assert services.environment.commands == []
    assert services.events.rows == []
