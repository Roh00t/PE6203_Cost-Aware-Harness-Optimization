import asyncio
import copy
import json
import threading
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock

import litellm
import pytest
from minisweagent.agents.default import DefaultAgent
from minisweagent.environments.local import LocalEnvironment
from minisweagent.exceptions import FormatError

from harness.components.budget import BudgetManager, CostCapExceeded, JobLedger
from harness.components.context import ContextManager
from harness.config import HarnessConfig, load_config
from harness.environment import SAFE_ENV, HarborEnvironment
from harness.gateway import OpenRouterGateway, UsageError
from harness.hooks import Decision, Hook, RunState
from harness.loop import HarnessAgent
from harness.prompts import render_templates
from harness.telemetry import JsonlLog


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    monkeypatch.setattr(
        litellm,
        "completion",
        Mock(side_effect=AssertionError("Tests must not call a paid API")),
    )


class Events:
    def __init__(self):
        self.rows = []

    def write(self, **row):
        self.rows.append(row)


def response(command="printf hello", prompt=10, completion=4, provider="Darkbloom"):
    message = {"role": "assistant", "content": "Working"}
    if command is not None:
        message["tool_calls"] = [
            {
                "id": "call1",
                "type": "function",
                "function": {
                    "name": "bash",
                    "arguments": json.dumps({"command": command}),
                },
            }
        ]
    return litellm.ModelResponse(
        model="openai/gpt-oss-20b",
        provider=provider,
        choices=[
            {"finish_reason": "tool_calls" if command else "stop", "message": message}
        ],
        usage={
            "prompt_tokens": prompt,
            "completion_tokens": completion,
            "prompt_tokens_details": {"cached_tokens": 2},
            "completion_tokens_details": {"reasoning_tokens": 3},
        },
    )


def gateway(tmp_path, responses, **kwargs):
    _, stock = load_config("configs/harness/h0.yaml")
    price = {
        "provider": "Darkbloom",
        "prompt_usd_per_mtok": 0.018,
        "completion_usd_per_mtok": 0.09,
    }
    calls = JsonlLog(
        tmp_path / "calls.jsonl",
        {"config_id": "test", "task_id": "synthetic", "trial_id": "test"},
    )
    model = OpenRouterGateway(
        calls=calls, events=Events(), price=price, **kwargs, **stock["model"]
    )
    model._call_api = Mock(side_effect=responses)
    return model


class FakeEnv:
    def __init__(self):
        self.commands = []
        self.files = {}

    def execute(self, action):
        command = action["command"]
        self.commands.append(command)
        return {
            "output": "COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT\n"
            if command == "echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT"
            else "hello",
            "returncode": 0,
            "exception_info": "",
        }

    def check_finished(self, output):
        LocalEnvironment._check_finished(self, output)

    def get_template_vars(self):
        return dict(system="Linux", release="test", version="test", machine="x86_64")

    def serialize(self):
        return {}

    def write_text(self, path, content):
        self.files[path] = content


class StockEnv(FakeEnv):
    def execute(self, action):
        result = super().execute(action)
        self.check_finished(result)
        return result


def agent(tmp_path, responses, config=None, hooks=(), guardrail=None):
    config = config or HarnessConfig()
    _, stock = load_config("configs/harness/h0.yaml")
    settings, variables = render_templates(stock, config)
    settings["step_limit"] = config.step_limit if config.enabled("C3") else 0
    model = gateway(tmp_path, responses)
    obj = HarnessAgent(
        model,
        FakeEnv(),
        harness_config=config,
        events=Events(),
        guardrail=guardrail or Hook(),
        hooks=hooks,
        **settings,
    )
    return obj, variables


def test_h0_defaults_and_templates():
    config, stock = load_config("configs/harness/h0.yaml")
    settings, _ = render_templates(stock, config)
    assert settings["cost_limit"] == settings["step_limit"] == 0
    assert "mode" not in settings
    assert settings["instance_template"] == stock["agent"]["instance_template"]
    assert settings["system_template"] == stock["agent"]["system_template"]


def test_typo_and_h0_flags_rejected():
    with pytest.raises(ValueError):
        HarnessConfig(components=["C9"])
    with pytest.raises(ValueError):
        HarnessConfig(components=["C1"])
    with pytest.raises(ValueError):
        HarnessConfig(offload_char=20)


def test_cost_reasoning_not_double_counted(tmp_path):
    model = gateway(tmp_path, [response()])
    model.query([{"role": "user", "content": "task"}])
    row = json.loads((tmp_path / "calls.jsonl").read_text())
    assert row["cost_table_usd"] == pytest.approx((10 * 0.018 + 4 * 0.09) / 1e6)
    assert row["reasoning_tokens"] == 3 and row["cached_tokens"] == 2
    assert model.spent == Decimal("0.00000054")


def test_format_error_still_logged_and_charged(tmp_path):
    model = gateway(tmp_path, [response(None)])
    with pytest.raises(FormatError) as error:
        model.query([{"role": "user", "content": "task"}])
    assert error.value.messages[0]["extra"]["response"]["usage"]["prompt_tokens"] == 10
    assert json.loads((tmp_path / "calls.jsonl").read_text())["error"] == "FormatError"
    assert model.spent > 0


def test_missing_usage_is_not_zero(tmp_path):
    bad = response()
    bad.usage.prompt_tokens = None
    model = gateway(tmp_path, [bad])
    with pytest.raises(UsageError):
        model.query([])
    assert not model.usage_complete
    assert json.loads((tmp_path / "calls.jsonl").read_text())["cost_table_usd"] is None


def test_provider_mismatch_logged(tmp_path):
    model = gateway(tmp_path, [response(provider="wrong")])
    with pytest.raises(UsageError):
        model.query([])
    assert (
        json.loads((tmp_path / "calls.jsonl").read_text())["error"]
        == "EndpointMismatch"
    )


def test_retry_each_attempt_logged(tmp_path):
    error = litellm.RateLimitError(
        message="rate", model="test", llm_provider="openrouter"
    )
    stop = Mock()
    stop.is_set.return_value = False
    stop.wait.return_value = False
    model = gateway(tmp_path, [error, response()], stop_event=stop)
    model.query([])
    rows = [json.loads(s) for s in (tmp_path / "calls.jsonl").read_text().splitlines()]
    assert [r["retries"] for r in rows] == [0, 1]
    assert rows[0]["prompt_tokens"] is None
    assert not model.usage_complete
    stop.wait.assert_called_once_with(2)


def test_budget_refuses_unaffordable_call(tmp_path):
    model = gateway(tmp_path, [response()], budget_usd=0.00001)
    with pytest.raises(CostCapExceeded):
        model.query([])
    model._call_api.assert_not_called()


def test_cancel_refuses_call(tmp_path):
    stop = threading.Event()
    stop.set()
    model = gateway(tmp_path, [response()], stop_event=stop)
    with pytest.raises(RuntimeError):
        model.query([])
    model._call_api.assert_not_called()


def test_h0_matches_stock_on_scripted_success(tmp_path):
    sequence = [response(), response("echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT")]
    ours, variables = agent(tmp_path / "ours", copy.deepcopy(sequence))
    _, stock = load_config("configs/harness/h0.yaml")
    baseline = DefaultAgent(
        gateway(tmp_path / "stock", copy.deepcopy(sequence)),
        StockEnv(),
        **stock["agent"],
    )
    assert (
        ours.run("Synthetic task", **variables)["exit_status"]
        == baseline.run("Synthetic task")["exit_status"]
        == "Submitted"
    )
    assert ours.env.commands == baseline.env.commands
    assert ours.n_calls == baseline.n_calls == 2

    def clean(messages):
        return [{k: v for k, v in msg.items() if k != "extra"} for msg in messages]

    assert clean(ours.messages) == clean(baseline.messages)


def test_h0_matches_stock_on_three_format_errors(tmp_path):
    ours, variables = agent(tmp_path / "ours", [response(None) for _ in range(3)])
    _, stock = load_config("configs/harness/h0.yaml")
    baseline = DefaultAgent(
        gateway(tmp_path / "stock", [response(None) for _ in range(3)]),
        StockEnv(),
        **stock["agent"],
    )
    assert (
        ours.run("Synthetic", **variables)["exit_status"]
        == baseline.run("Synthetic")["exit_status"]
        == "RepeatedFormatError"
    )
    assert ours.n_calls == baseline.n_calls == 3
    assert ours.cost == baseline.cost


def test_missing_tool_hook_then_submit(tmp_path):
    class Recovery(Hook):
        components = frozenset({"C2"})

        def on_missing_tool_call(self, response, state):
            return "Use an actual tool call."

    config = HarnessConfig(config_id="test", components=["C2"])
    obj, variables = agent(
        tmp_path,
        [response(None), response("echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT")],
        config,
        [Recovery()],
    )
    assert obj.run("Synthetic", **variables)["exit_status"] == "Submitted"
    assert obj.messages[2]["content"] == "Use an actual tool call."


def test_guardrail_block_prevents_execution(tmp_path):
    class Block(Hook):
        def before_execute(self, action, state):
            return Decision(False, "blocked", "G-test")

    obj, variables = agent(tmp_path, [response() for _ in range(10)], guardrail=Block())
    assert obj.run("Synthetic", **variables)["exit_status"] == "GuardrailLimit"
    assert obj.env.commands == []


def test_c3_step_limit(tmp_path):
    config = HarnessConfig(config_id="test", components=["C3"], step_limit=2)
    obj, variables = agent(tmp_path, [response(), response()], config)
    assert obj.run("Synthetic", **variables)["exit_status"] == "LimitsExceeded"
    assert obj.n_calls == 2
    assert "[budget]" in obj.messages[3]["content"]


def test_submission_gate_defers_once(tmp_path):
    class Gate(Hook):
        def __init__(self):
            self.count = 0

        def before_submit(self, action, state):
            self.count += 1
            return Decision(self.count > 1, "Verify first")

    obj, variables = agent(
        tmp_path,
        [response("echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT") for _ in range(2)],
        hooks=[Gate()],
    )
    assert obj.run("Synthetic", **variables)["exit_status"] == "Submitted"
    assert obj.n_calls == 2


def test_offload_preserves_original():
    env, events = FakeEnv(), Events()
    manager = ContextManager(HarnessConfig(), env, events)
    original = {"output": "a" * 3000, "returncode": 0, "exception_info": ""}
    result = manager.offload(original, 1)
    assert original["output"] == "a" * 3000
    assert list(env.files.values()) == ["a" * 3000]
    assert result["extra"]["full_output"] == original["output"]
    assert len(result["output"]) < len(original["output"])


def test_compaction_keeps_tool_pairs_and_history():
    history = [
        {"role": "system", "content": "system"},
        {"role": "user", "content": "task"},
    ]
    for i in range(10):
        history += [
            {
                "role": "assistant",
                "content": "work",
                "tool_calls": [
                    {
                        "id": str(i),
                        "type": "function",
                        "function": {"name": "bash", "arguments": "{}"},
                    }
                ],
                "extra": {"actions": [{"command": "printf generic"}]},
            },
            {
                "role": "tool",
                "tool_call_id": str(i),
                "content": "result" * 100,
                "extra": {"returncode": 0},
            },
        ]
    snapshot = copy.deepcopy(history)
    config = HarnessConfig(
        config_id="test", components=["C1"], compact_at_tokens=1, keep_tail=2
    )
    view = ContextManager(config, FakeEnv(), Events()).view(history, 10)
    assert history == snapshot
    ids = [m["tool_call_id"] for m in view if m["role"] == "tool"]
    assert ids == ["0", "8", "9"]
    assert view[:4] == history[:4]
    assert view[-4:] == history[-4:]


def test_budget_nudge_once():
    manager = BudgetManager(HarnessConfig(), Events())
    state = RunState("", 35, 0.001, 2, frozenset({"C3"}))
    assert "stop exploring" in manager.observation({"output": ""}, state, 20)["output"]
    assert (
        "stop exploring" not in manager.observation({"output": ""}, state, 20)["output"]
    )


def test_job_ledger_shares_cap(tmp_path):
    one = JobLedger(tmp_path / "ledger.db", 0.01)
    two = JobLedger(tmp_path / "ledger.db", 0.01)
    reservation = one.reserve(0.008)
    with pytest.raises(CostCapExceeded):
        two.reserve(0.004)
    one.settle(reservation, 0.001)
    assert two.reserve(0.004)
    with pytest.raises(ValueError):
        JobLedger(tmp_path / "ledger.db", 0.02)


def test_async_bridge_secrets_and_exit_code():
    async def check():
        class Container:
            async def exec(self, **kwargs):
                assert kwargs["env"] == SAFE_ENV
                assert not any(
                    "KEY" in k or "SECRET" in k or "TOKEN" in k for k in kwargs["env"]
                )
                assert "PIPESTATUS[0]" in kwargs["command"]
                assert kwargs["cwd"] is None
                return SimpleNamespace(stdout="ok", stderr="", return_code=7)

        env = HarborEnvironment(
            Container(), asyncio.get_running_loop(), template_vars={}
        )
        output = await asyncio.to_thread(env.execute, {"command": "printf ok"})
        assert output["returncode"] == 7 and output["output"] == "ok"

    asyncio.run(check())


def test_missing_guardrail_fails_before_api(tmp_path):
    from harness.agent import factory

    with pytest.raises(RuntimeError, match="Missing integration factory"):
        factory("harness.nonexistent_adapter:build_guardrail")


def test_real_guardrail_blocks_and_logs_in_loop(tmp_path):
    from harness.isha_adapter import IshaGuardrail

    obj, variables = agent(
        tmp_path,
        [
            response("rm -rf /"),
            response("printenv"),
            response("echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT"),
        ],
        guardrail=IshaGuardrail(),
    )
    obj.run("Synthetic", **variables)
    assert "rm -rf /" not in obj.env.commands
    assert "printenv" in obj.env.commands
    assert any(row.get("rule_id") == "G-DST-01" for row in obj.events.rows)
    assert any(row.get("rule_id") == "G-SEC-01" for row in obj.events.rows)


def test_real_guardrail_c2_rules_are_flagged():
    from harness.isha_adapter import IshaGuardrail

    hook = IshaGuardrail()
    for flags, allowed in [(frozenset(), True), (frozenset({"C2"}), False)]:
        state = RunState("Synthetic", 1, 0, 0, flags)
        assert hook.before_execute({"command": "nano file"}, state).allowed is allowed


def test_actual_harbor_agent_orchestration(tmp_path, monkeypatch):
    from harbor.models.agent.context import AgentContext

    import harness.agent as module

    monkeypatch.setattr(module, "factory", lambda path: lambda config, services: Hook())
    monkeypatch.setattr(
        OpenRouterGateway,
        "_call_api",
        lambda self, messages: response("echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT"),
    )

    class Container:
        environment_name = "synthetic"
        session_id = "synthetic__trial"

        async def exec(self, **kwargs):
            return SimpleNamespace(
                stdout="COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT\n",
                stderr="",
                return_code=0,
            )

    async def run():
        obj = module.CostAwareAgent(logs_dir=tmp_path)
        obj.template_vars = dict(
            system="Linux", release="test", version="test", machine="x86_64"
        )
        context = AgentContext()
        await obj.run("Synthetic task", Container(), context)
        assert context.metadata["exit_status"] == "Submitted"
        assert context.n_input_tokens == 10 and context.cost_usd > 0
        assert (tmp_path / "mini-swe-agent.trajectory.json").exists()
        assert (tmp_path / "calls.jsonl").exists()

    asyncio.run(run())


def test_appended_prompt_overhead_attributed(tmp_path):
    config = HarnessConfig(config_id="test", components=["C3"])
    obj, variables = agent(
        tmp_path, [response("echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT")], config
    )
    obj.run("Synthetic", **variables)
    row = json.loads((tmp_path / "calls.jsonl").read_text())
    assert row["prompt_chars_by_origin"]["harness"] > 0


def test_submission_requires_successful_exit():
    env = FakeEnv()
    env.check_finished(
        {"output": "COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT\n", "returncode": 1}
    )


def test_model_override_rejected_before_integration(tmp_path):
    from harness.agent import CostAwareAgent

    with pytest.raises(ValueError, match="frozen"):
        CostAwareAgent(logs_dir=tmp_path, model_name="different")


def test_completed_container_timeout_does_not_poll_forever():
    async def check():
        class Container:
            async def exec(self, **kwargs):
                raise TimeoutError("container transport timed out")

        env = HarborEnvironment(
            Container(), asyncio.get_running_loop(), template_vars={}
        )
        with pytest.raises(TimeoutError):
            await asyncio.wait_for(
                asyncio.to_thread(env.execute, {"command": "printf hello"}), timeout=3
            )

    asyncio.run(check())


def test_digest_uses_actual_output_first_line():
    history = [{"role": "system", "content": "s"}, {"role": "user", "content": "t"}]
    for i in range(5):
        history += [
            {
                "role": "assistant",
                "content": "action",
                "extra": {"actions": [{"command": "printf hello"}]},
            },
            {
                "role": "tool",
                "content": '{\n"output": "wrapped"}',
                "extra": {"returncode": 0, "raw_output": f"actual line {i}\nsecond"},
            },
        ]
    config = HarnessConfig(
        config_id="test", components=["C1"], keep_tail=1, compact_at_tokens=1
    )
    view = ContextManager(config, FakeEnv(), Events()).view(history, 5)
    digest = next(
        msg["content"] for msg in view if msg["content"].startswith("[Earlier")
    )
    assert "actual line 1" in digest
