"""Regression tests for issue #2: H0+C2 trials hung forever at "running agent...".

Plugin factories run inside CostAwareAgent.run(), on Harbor's event-loop thread. C2 used to
upload its helper from its constructor; HarborEnvironment._wait then blocked that thread while
waiting for a coroutine scheduled on the same loop, so neither the upload nor Harbor's agent
timeout could ever run. The other suites missed it because their fake environments are
synchronous. These tests use the real HarborEnvironment bridge on a running loop, and run each
check in a daemon thread with a deadline so a regression fails instead of hanging pytest.
"""

import asyncio
import threading
from types import SimpleNamespace
from unittest.mock import Mock

import litellm
import pytest

from harness.components.tools import HELPER_PATH, build_hook
from harness.config import load_config
from harness.environment import HarborEnvironment
from harness.gateway import REQUEST_TIMEOUT_S, OpenRouterGateway
from harness.hooks import RunState, Services
from harness.telemetry import JsonlLog

DEADLINE_S = 10


class Events:
    def __init__(self):
        self.rows = []

    def write(self, **row):
        self.rows.append(row)


class Container:
    """Async stand-in for a Harbor environment; records every container call."""

    def __init__(self):
        self.calls = []

    async def exec(self, **kwargs):
        self.calls.append(("exec", kwargs["command"]))
        return SimpleNamespace(stdout="ok", stderr="", return_code=0)

    async def upload_file(self, source, target):
        self.calls.append(("upload", str(target)))


def run_with_deadline(check):
    """Run asyncio.run(check()) in a daemon thread; fail if it doesn't finish in time."""
    outcome = {}

    def target():
        try:
            outcome["value"] = asyncio.run(check())
        except BaseException as error:  # re-raised in the test thread below
            outcome["error"] = error

    thread = threading.Thread(target=target, daemon=True)
    thread.start()
    thread.join(DEADLINE_S)
    if thread.is_alive():
        pytest.fail(f"deadlocked: no result within {DEADLINE_S} s")
    if "error" in outcome:
        raise outcome["error"]
    return outcome.get("value")


def c2_config():
    return load_config("configs/harness/c2.yaml")[0]


def test_building_c2_on_the_event_loop_makes_no_container_call():
    config, container = c2_config(), Container()

    async def check():
        # Same thread and loop as CostAwareAgent.run() building its plugins.
        adapter = HarborEnvironment(container, asyncio.get_running_loop(), template_vars={})
        return build_hook(config, Services(adapter, Events(), config))

    hook = run_with_deadline(check)
    assert "C2" in hook.components
    assert container.calls == []


def test_helper_is_uploaded_once_on_first_tool_use_from_the_worker_thread():
    config, container = c2_config(), Container()
    action = {"tool": "read_file", "arguments": {"path": "/tmp/example.txt"}}
    state = RunState(task="t", step=1, spent_usd=0.0, elapsed_seconds=0.0,
                     components=frozenset({"C2"}))

    async def check():
        adapter = HarborEnvironment(container, asyncio.get_running_loop(), template_vars={})
        hook = build_hook(config, Services(adapter, Events(), config))
        results = []
        for _ in range(2):  # the loop runs tools on its worker thread, as here
            results.append(await asyncio.to_thread(hook.execute_tool, action, state))
        return results

    results = run_with_deadline(check)
    assert [call for call in container.calls if call[0] == "upload"] == [("upload", HELPER_PATH)]
    helper_runs = [c for kind, c in container.calls if kind == "exec" and f"python3 {HELPER_PATH}" in c]
    assert len(helper_runs) == 2
    assert all(result["returncode"] == 0 for result in results)


def test_container_call_on_the_event_loop_thread_fails_fast():
    container = Container()

    async def check():
        adapter = HarborEnvironment(container, asyncio.get_running_loop(), template_vars={})
        with pytest.raises(RuntimeError, match="deadlock"):
            adapter.execute({"command": "true"})
        with pytest.raises(RuntimeError, match="deadlock"):
            adapter.write_text("/tmp/x/notes.md", "text")

    run_with_deadline(check)
    assert container.calls == []


def test_gateway_bounds_each_request(tmp_path, monkeypatch):
    _, stock = load_config("configs/harness/h0.yaml")
    price = {"provider": "Darkbloom", "prompt_usd_per_mtok": 0.018, "completion_usd_per_mtok": 0.09}
    calls = JsonlLog(tmp_path / "calls.jsonl", {"config_id": "t", "task_id": "t", "trial_id": "t"})
    model = OpenRouterGateway(calls=calls, events=Events(), price=price, **stock["model"])
    completion = Mock(return_value="response")
    monkeypatch.setattr(litellm, "completion", completion)

    assert model._call_api([{"role": "user", "content": "hi"}]) == "response"
    kwargs = completion.call_args.kwargs
    assert kwargs["timeout"] == REQUEST_TIMEOUT_S == 600
    assert kwargs["num_retries"] == 0
    # Frozen decoding settings still pass through unchanged.
    for key, value in stock["model"]["model_kwargs"].items():
        assert kwargs[key] == value
