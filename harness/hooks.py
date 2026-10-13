"""Typed integration contract for Isha's components; no guessed guardrail API."""

from dataclasses import dataclass, field
from typing import Any, ClassVar


@dataclass(frozen=True)
class Decision:
    allowed: bool = True
    feedback: str = ""
    rule_id: str | None = None
    event: str | None = None


@dataclass(frozen=True)
class RunState:
    task: str
    step: int
    spent_usd: float
    elapsed_seconds: float
    components: frozenset[str]


class Hook:
    """Subclass and override only required hooks. Return values must be JSON compatible."""

    components: frozenset[str] = frozenset()
    tools: ClassVar[list[dict]] = []

    def before_query(self, history: list[dict], state: RunState) -> list[dict]:
        return history

    def on_missing_tool_call(self, response: dict, state: RunState) -> str | None:
        """Return corrective feedback, or None to keep stock format-error feedback."""
        return None

    def before_execute(self, action: dict, state: RunState) -> Decision:
        return Decision()

    def before_submit(self, action: dict, state: RunState) -> Decision:
        return Decision()

    def after_execute(self, action: dict, result: dict, state: RunState) -> dict:
        return result

    def execute_tool(self, action: dict, state: RunState) -> dict:
        raise NotImplementedError("Plugin must implement its advertised tools")


@dataclass
class Services:
    """Passed to build_hook(config, services) and build_guardrail(config, services)."""

    environment: Any
    events: Any
    config: Any
    extras: dict = field(default_factory=dict)
