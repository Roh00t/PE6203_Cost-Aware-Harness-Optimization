"""Regression tests for the harness-v1.1 fixes listed in docs/bug_fixes.md (BF-NN ids).

Bugs #1–#9 from docs/harness_bug_review.md keep their tests in test_known_issues.py, and the
guardrail rule fixes are in test_guardrails.py. This file covers the rest.
"""

import asyncio
import os
import threading
from types import SimpleNamespace
from unittest.mock import Mock

import litellm
import pytest

from harness.components.context import ContextManager
from harness.components.recovery import FailureRecovery
from harness.components.submit_gate import SubmissionGate
from harness.components.tools import ToolInterface
from harness.config import HarnessConfig
from harness.environment import HarborEnvironment, TrialCancelled
from harness.gateway import MAX_ATTEMPTS
from harness.hooks import RunState, Services
from test_components import make_services
from test_harness_core import Events, agent, gateway, response


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    monkeypatch.setattr(litellm, "completion", Mock(side_effect=AssertionError("Tests must not call a paid API")))


# --- BF-19: C5's 90 % exception exists only with C3's step cap ---------------------------------

class MissingFiles:
    def execute(self, action):
        return {"output": "", "returncode": 1}


def gate(components):
    config = HarnessConfig(config_id="test", components=components)
    return SubmissionGate(Services(environment=MissingFiles(), events=Events(), config=config))


def submit_at(hook, step, components):
    return hook.before_submit({}, RunState("Save /app/out.txt", step, 0.0, 60.0, frozenset(components)))


def test_gate_fires_late_in_a_run_without_a_step_cap():
    assert not submit_at(gate(["C5"]), 120, {"C5"}).allowed


def test_gate_keeps_its_90_percent_exception_with_c3():
    assert submit_at(gate(["C3", "C5"]), 46, {"C3", "C5"}).allowed
    assert not submit_at(gate(["C3", "C5"]), 44, {"C3", "C5"}).allowed


# --- BF-20: ignored extra tool calls never reach the after-execute hooks -----------------------

def test_ignored_extra_calls_cause_no_stall_nudge_or_status_line(tmp_path):
    config = HarnessConfig(config_id="test", components=["C2", "C3", "C4"])
    recovery = FailureRecovery(Events())
    obj, _ = agent(tmp_path, [response()], config, hooks=[recovery])
    obj.state = Mock(return_value=RunState("Synthetic", 1, 0, 0, frozenset(config.components)))
    obj.model.format_observation_messages = Mock(side_effect=lambda message, outputs, variables: outputs)
    obj.add_messages = lambda *messages: messages
    calls = [{"tool": "bash", "command": "ls", "tool_call_id": f"c{i}"} for i in range(4)]

    outputs = obj.execute_actions({"extra": {"actions": calls}})

    assert not any(row["type"] == "stall_nudge" for row in recovery.events.rows)
    assert "[budget]" in outputs[0]["output"]
    assert all("[budget]" not in output["output"] for output in outputs[1:])


# --- BF-21: C1 shortening keeps an exact, additive harness_chars ---------------------------------

def test_shortening_counts_its_own_text_and_drops_cut_harness_text():
    manager = ContextManager(SimpleNamespace(keep_tail=1, compact_at_tokens=10**9), None, Events())
    status = "\n[budget] step 2/50"
    old = {"role": "tool", "content": "x" * 500 + status, "extra": {"harness_chars": len(status)}}
    history = [
        {"role": "system", "content": "s"}, {"role": "user", "content": "task"},
        {"role": "assistant", "content": "a1"}, {"role": "tool", "content": "first"},
        {"role": "assistant", "content": "a2"}, old,
        {"role": "assistant", "content": "a3"}, {"role": "tool", "content": "recent"},
    ]

    shortened = manager.view(history, 4)[5]

    suffix = "\n[older observation shortened]"
    assert shortened["content"].endswith(suffix)
    assert shortened["extra"]["harness_chars"] == len(suffix) == 30  # the status line was cut


# --- BF-10: a failed container call is an observation, a cancellation still propagates ---------

def run_in_adapter(error, *, cancelled=False):
    async def check():
        class Container:
            async def exec(self, **kwargs):
                raise error

        stop = threading.Event()
        env = HarborEnvironment(Container(), asyncio.get_running_loop(), template_vars={}, stop_event=stop)
        if cancelled:
            stop.set()
        return await asyncio.to_thread(env.execute, {"command": "soffice --headless &"})

    return asyncio.run(check())


def test_container_call_failure_returns_an_observation():
    result = run_in_adapter(RuntimeError("Command timed out after 45 seconds"))
    assert result["returncode"] == -1
    assert "Command timed out after 45 seconds" in result["exception_info"]
    assert "> /tmp/job.log 2>&1 &" in result["output"]
    assert result["extra"]["harness_chars"] == len(result["output"])


def test_cancelled_trial_still_raises():
    with pytest.raises(TrialCancelled):
        run_in_adapter(RuntimeError("never reached"), cancelled=True)


# --- BF-11: the rate-limit retry window matches stock mini-swe-agent ---------------------------

def test_rate_limit_retries_back_off_for_minutes_with_jitter(tmp_path):
    error = litellm.RateLimitError(message="429", model="openai/gpt-oss-20b", llm_provider="openrouter")
    stop = Mock()
    stop.is_set.return_value = False
    stop.wait.return_value = False
    model = gateway(tmp_path, [error] * (MAX_ATTEMPTS - 1) + [response()], stop_event=stop)

    assert model.query([])["extra"]["actions"]  # succeeds on the last allowed attempt

    waits = [call.args[0] for call in stop.wait.call_args_list]
    assert len(waits) == MAX_ATTEMPTS - 1 == 9
    for attempt, wait in enumerate(waits):
        delay = min(60, 4 * 2**attempt)
        assert delay / 2 <= wait <= delay
    assert sum(waits) >= 180  # v1 gave up after 2 + 4 + 8 = 14 s


def test_rate_limit_still_gives_up_after_the_last_attempt(tmp_path):
    error = litellm.RateLimitError(message="429", model="openai/gpt-oss-20b", llm_provider="openrouter")
    stop = Mock()
    stop.is_set.return_value = False
    stop.wait.return_value = False
    model = gateway(tmp_path, [error] * MAX_ATTEMPTS, stop_event=stop)
    with pytest.raises(litellm.RateLimitError):
        model.query([])
    assert stop.wait.call_count == MAX_ATTEMPTS - 1


# --- BF-16 to BF-18: C2 file tools -------------------------------------------------------------

def tool(tmp_path, name, **arguments):
    hook = ToolInterface(make_services(tmp_path, components=("C2",)))
    return hook.execute_tool({"tool": name, "arguments": arguments}, RunState("task", 1, 0, 0, frozenset({"C2"})))


def test_search_survives_unreadable_and_non_utf8_files(tmp_path):
    (tmp_path / "a.txt").write_text("the needle\n")
    (tmp_path / "latin1.txt").write_bytes(b"caf\xe9 needle\n")
    (tmp_path / "binary.bin").write_bytes(b"\0needle\0")
    locked = tmp_path / "z_locked.txt"
    locked.write_text("needle\n")
    locked.chmod(0)
    try:
        result = tool(tmp_path, "search", pattern="needle", path=str(tmp_path))
    finally:
        locked.chmod(0o600)
    assert result["returncode"] == 0
    assert "a.txt:1: the needle" in result["output"]
    assert "latin1.txt:1: caf� needle" in result["output"]
    assert "binary.bin" not in result["output"]
    if os.geteuid() != 0:  # root can read a mode-000 file
        assert "Skipped 1 unreadable file(s)." in result["output"]


def test_read_file_shows_invalid_bytes_instead_of_failing(tmp_path):
    (tmp_path / "notes.txt").write_bytes(b"\xa9 2026 Example\n")
    result = tool(tmp_path, "read_file", path=str(tmp_path / "notes.txt"))
    assert result["returncode"] == 0 and result["output"] == "1: � 2026 Example"


def test_edit_file_keeps_crlf_line_endings(tmp_path):
    target = tmp_path / "data.csv"
    target.write_bytes(b"id,name\r\nfoo,1\r\nbar,2\r\n")
    result = tool(tmp_path, "edit_file", path=str(target), old="foo,1\nbar", new="baz,1\nbar")
    assert result["returncode"] == 0
    assert target.read_bytes() == b"id,name\r\nbaz,1\r\nbar,2\r\n"


def test_edit_file_rejects_overlapping_matches(tmp_path):
    target = tmp_path / "x.txt"
    target.write_text("aaa")
    result = tool(tmp_path, "edit_file", path=str(target), old="aa", new="X")
    assert result["returncode"] == 1 and "found 2" in result["output"]
    assert target.read_text() == "aaa"


def test_unpaired_surrogate_is_a_tool_error_not_a_crash(tmp_path):
    result = tool(tmp_path, "write_file", path=str(tmp_path / "x.txt"), content="emoji \ud83d")
    assert result["returncode"] == 1
    assert "unpaired surrogate" in result["output"]
    assert result["extra"]["origin"] == "harness"
