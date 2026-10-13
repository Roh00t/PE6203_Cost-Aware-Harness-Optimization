"""Harbor 0.6.3 custom host agent; model credentials never enter the task container."""

import asyncio
import importlib
import json
import threading
from pathlib import Path

from harbor.agents.base import BaseAgent

from harness.components.budget import JobLedger
from harness.config import ROOT, load_config
from harness.environment import SAFE_ENV, HarborEnvironment
from harness.gateway import OpenRouterGateway
from harness.hooks import Hook, Services
from harness.loop import HarnessAgent
from harness.prompts import render_templates
from harness.telemetry import JsonlLog


def factory(path):
    module, separator, name = path.partition(":")
    if not separator:
        raise ValueError("Factory path must be module:function")
    try:
        return getattr(importlib.import_module(module), name)
    except (ImportError, AttributeError) as error:
        raise RuntimeError(
            f"Missing integration factory {path}. See docs/harness_core.md; do not bypass guardrails for paid runs."
        ) from error


class CostAwareAgent(BaseAgent):
    SUPPORTS_ATIF = (
        False  # Native mini trajectory + calls/events are written; no false ATIF claim.
    )

    def __init__(
        self,
        logs_dir: Path,
        model_name=None,
        *,
        config_path="configs/harness/h0.yaml",
        job_budget_usd=None,
        job_ledger_path=None,
        **kwargs,
    ):
        if (job_budget_usd is None) != (job_ledger_path is None):
            raise ValueError("Supply both job_budget_usd and job_ledger_path")
        self.job_ledger = (
            JobLedger(job_ledger_path, float(job_budget_usd))
            if job_ledger_path
            else None
        )
        self.harness_config, self.stock = load_config(config_path)
        frozen_model = self.stock["model"]["model_name"]
        if model_name is not None and model_name != frozen_model:
            raise ValueError(
                "Harbor model override differs from the frozen model config"
            )
        super().__init__(logs_dir=logs_dir, model_name=frozen_model, **kwargs)
        self.guardrail_factory = factory(self.harness_config.guardrail_factory)
        self.plugin_factories = [factory(path) for path in self.harness_config.plugins]
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.stop_event = threading.Event()

    @staticmethod
    def name():
        return "cost-aware-harness"

    def version(self):
        return "0.1.0"

    async def setup(self, environment):
        # Container Python and GNU timeout are prerequisites; no host platform leakage.
        result = await environment.exec(
            command="python3 -c 'import json,os,platform; print(json.dumps(dict(platform.uname()._asdict(), cwd=os.getcwd())))'",
            env=dict(SAFE_ENV),
            timeout_sec=30,
        )
        if result.return_code:
            raise RuntimeError(
                "Container requires python3 for bounded output and template metadata"
            )
        self.template_vars = json.loads(result.stdout)
        check = await environment.exec(
            command="command -v bash && command -v timeout",
            env=dict(SAFE_ENV),
            timeout_sec=30,
        )
        if check.return_code:
            raise RuntimeError("Container requires bash and GNU timeout")

    async def run(self, instruction, environment, context):
        config = self.harness_config
        identity = {
            "config_id": config.config_id,
            "task_id": environment.environment_name,
            "trial_id": environment.session_id,
        }
        events = JsonlLog(self.logs_dir / "events.jsonl", identity)
        calls = JsonlLog(self.logs_dir / "calls.jsonl", identity)
        adapter = HarborEnvironment(
            environment,
            asyncio.get_running_loop(),
            template_vars=self.template_vars,
            timeout=config.command_timeout if config.enabled("C3") else 30,
            events=events,
            stop_event=self.stop_event,
        )
        services = Services(adapter, events, config)
        guardrail = self.guardrail_factory(config, services)
        hooks = [build(config, services) for build in self.plugin_factories]
        if not isinstance(guardrail, Hook) or any(
            not isinstance(hook, Hook) for hook in hooks
        ):
            raise TypeError("Integration factories must return Hook instances")
        provided = set().union(*(hook.components for hook in hooks))
        missing = set(config.components).intersection({"C2", "C4", "C5"}) - provided
        if missing:
            raise RuntimeError(
                "Enabled components have no implementation: "
                + ", ".join(sorted(missing))
            )
        if provided - set(config.components):
            raise RuntimeError(
                "Plugin implements a disabled component; ablation would be invalid"
            )
        prices = json.loads((ROOT / "configs/pricing.json").read_text(encoding="utf-8"))
        model_config = dict(self.stock["model"])
        price = prices["models"][model_config["model_name"].removeprefix("openrouter/")]

        def update_usage(gateway):
            context.n_input_tokens = gateway.n_input
            context.n_output_tokens = gateway.n_output
            context.n_cache_tokens = gateway.n_cached
            context.cost_usd = float(gateway.spent) if gateway.usage_complete else None
            context.metadata = {
                **(context.metadata or {}),
                "config_id": config.config_id,
                "known_cost_table_usd": float(gateway.spent),
                "usage_complete": gateway.usage_complete,
                "calls_log": "calls.jsonl",
                "cost_policy": "full input rate; reasoning included in completion",
            }

        gateway = OpenRouterGateway(
            calls=calls,
            events=events,
            price=price,
            stop_event=self.stop_event,
            budget_usd=config.budget_usd if config.enabled("C3") else None,
            on_usage=update_usage,
            job_ledger=self.job_ledger,
            **model_config,
        )
        agent_kwargs, variables = render_templates(self.stock, config)
        agent_kwargs["output_path"] = self.logs_dir / "mini-swe-agent.trajectory.json"
        agent = HarnessAgent(
            gateway,
            adapter,
            harness_config=config,
            events=events,
            guardrail=guardrail,
            hooks=hooks,
            **agent_kwargs,
        )
        events.write(
            type="trial_start",
            components=config.components,
            model=gateway.config.model_name,
            step_limit=agent.config.step_limit,
            budget_usd=config.budget_usd if config.enabled("C3") else None,
            command_timeout=adapter.timeout,
        )
        worker = asyncio.create_task(
            asyncio.to_thread(agent.run, instruction, **variables)
        )
        try:
            result = await asyncio.shield(worker)
            context.metadata = {**(context.metadata or {}), **result}
            events.write(type="trial_end", **result)
        except asyncio.CancelledError:
            adapter.cancel()
            events.write(type="trial_cancelled")
            # to_thread cannot kill an in-flight HTTP request. The stop event prevents another.
            worker.add_done_callback(
                lambda done: done.exception() if not done.cancelled() else None
            )
            raise
        finally:
            update_usage(gateway)
