"""Adapt Isha's guardrail results to the harness hook contract."""

from harness.guardrails import check_command
from harness.hooks import Decision, Hook


class IshaGuardrail(Hook):
    def before_execute(self, action, state):
        command = action.get("command")
        if not isinstance(command, str):
            return Decision(False, "Command must be a string", event="invalid_action")
        result = check_command(command, c2_enabled="C2" in state.components)
        return Decision(
            allowed=not result.blocked,
            feedback=result.message or "",
            rule_id=result.rule_id,
            event=("guardrail_block" if result.blocked else "guardrail_log")
            if result.rule_id
            else None,
        )


def build_guardrail(config, services):
    return IshaGuardrail()
