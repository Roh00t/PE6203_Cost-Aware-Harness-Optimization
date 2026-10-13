"""DefaultAgent subclass with explicit hooks and independently enabled C1/C3."""

import time
from copy import deepcopy

from minisweagent.agents.default import DefaultAgent
from minisweagent.exceptions import LimitsExceeded, TimeExceeded

from harness.components.budget import BudgetManager
from harness.components.context import ContextManager, estimate_tokens
from harness.hooks import Decision, RunState


class HarnessAgent(DefaultAgent):
    def __init__(
        self, model, env, *, harness_config, events, guardrail, hooks=(), **kwargs
    ):
        super().__init__(model, env, **kwargs)
        self.harness_config, self.events, self.guardrail = (
            harness_config,
            events,
            guardrail,
        )
        self.hooks = list(hooks)
        self.context_manager = (
            ContextManager(harness_config, env, events)
            if harness_config.enabled("C1")
            else None
        )
        self.budget_manager = (
            BudgetManager(harness_config, events)
            if harness_config.enabled("C3")
            else None
        )
        self.context_tokens = 0
        self.guardrail_blocks = 0
        model.missing_tool_feedback = self.on_missing_tool_call
        if harness_config.enabled("C2"):
            self.config.max_consecutive_format_errors = 5
        for hook in self.hooks:
            for tool in hook.tools:
                name = tool["function"]["name"]
                if name == "bash" or name in model.tool_plugins:
                    raise ValueError("Duplicate tool " + name)
                model.tool_plugins[name] = hook

    def add_messages(self, *messages):
        if not self.messages and len(messages) == 2:
            suffix = self.extra_template_vars.get("_harness_prompt_suffix", "")
            if suffix:
                messages[1].setdefault("extra", {})["harness_chars"] = len(
                    self._render_template(suffix)
                )
        return super().add_messages(*messages)

    def state(self):
        return RunState(
            self.extra_template_vars.get("task", ""),
            self.n_calls,
            float(self.model.spent),
            time.time() - self._start_time,
            frozenset(self.harness_config.components),
        )

    def before_query(self, history, state):
        view = (
            self.context_manager.view(history, state.step)
            if self.context_manager
            else deepcopy(history)
        )
        for hook in self.hooks:
            view = hook.before_query(view, state)
        return view

    def on_missing_tool_call(self, response):
        for hook in self.hooks:
            feedback = hook.on_missing_tool_call(response, self.state())
            if feedback is not None:
                return feedback
        return None  # H0 retains stock FormatError behavior.

    def before_execute(self, action, state):
        decision = self.guardrail.before_execute(action, state)
        if decision.event or decision.rule_id:
            self.events.write(
                type=decision.event
                or ("guardrail_block" if not decision.allowed else "guardrail_log"),
                step=state.step,
                rule_id=decision.rule_id,
                command=str(action.get("command", ""))[:500],
            )
        if not decision.allowed:
            self.guardrail_blocks += 1
            if self.guardrail_blocks >= 10:
                raise LimitsExceeded(
                    {
                        "role": "exit",
                        "content": "GuardrailLimit",
                        "extra": {"exit_status": "GuardrailLimit", "submission": ""},
                    }
                )
            return decision
        for hook in self.hooks:
            decision = hook.before_execute(action, state)
            if not decision.allowed:
                return decision
        return Decision()

    def before_submit(self, action, state):
        for hook in self.hooks:
            decision = hook.before_submit(action, state)
            if not decision.allowed:
                return decision
        return Decision()

    def after_execute(self, action, result, state):
        for hook in self.hooks:
            result = hook.after_execute(action, result, state)
        if self.context_manager:
            result = self.context_manager.offload(result, state.step)
        if self.budget_manager:
            result = self.budget_manager.observation(result, state, self.context_tokens)
        return result

    def query(self):
        if 0 < self.config.step_limit <= self.n_calls:
            self.events.write(type="cap_reached", step=self.n_calls, limit="steps")
            raise LimitsExceeded(
                {
                    "role": "exit",
                    "content": "LimitsExceeded",
                    "extra": {"exit_status": "LimitsExceeded", "submission": ""},
                }
            )
        if 0 < self.config.wall_time_limit_seconds <= time.time() - self._start_time:
            raise TimeExceeded(
                {
                    "role": "exit",
                    "content": "TimeExceeded",
                    "extra": {"exit_status": "TimeExceeded", "submission": ""},
                }
            )
        view = self.before_query(self.messages, self.state())
        self.context_tokens = estimate_tokens(view)
        self.n_calls += 1
        self.model.step = self.n_calls
        message = self.model.query(view)
        self.cost += message.get("extra", {}).get("cost", 0.0)
        self.add_messages(message)
        return message

    def execute_actions(self, message):
        outputs = []
        for action in message.get("extra", {}).get("actions", []):
            state = self.state()
            decision = self.before_execute(action, state)
            if decision.allowed:
                plugin = self.model.tool_plugins.get(action.get("tool"))
                result = (
                    plugin.execute_tool(action, state)
                    if plugin
                    else self.env.execute(action)
                )
                # Detect submission from actual output, not a regex over the command.
                lines = result.get("output", "").lstrip().splitlines()
                if (
                    result.get("returncode") == 0
                    and lines
                    and lines[0].strip() == "COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT"
                ):
                    decision = self.before_submit(action, state)
                    if decision.allowed:
                        self.env.check_finished(result)
                    else:
                        result = {
                            "output": decision.feedback,
                            "returncode": -1,
                            "exception_info": "",
                            "extra": {"origin": "harness"},
                        }
                        self.events.write(
                            type="submit_gate",
                            step=state.step,
                            rule_id=decision.rule_id,
                        )
            else:
                result = {
                    "output": decision.feedback,
                    "returncode": -1,
                    "exception_info": "",
                    "extra": {"origin": "harness"},
                }
            outputs.append(self.after_execute(action, result, state))
        return self.add_messages(
            *self.model.format_observation_messages(
                message, outputs, self.get_template_vars()
            )
        )
