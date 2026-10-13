"""Select prompt sections without modifying the frozen stock templates."""

import re
from copy import deepcopy

from harness.config import ROOT, HarnessConfig


def render_templates(stock: dict, config: HarnessConfig) -> tuple[dict, dict]:
    parts = re.split(
        r"<!-- @section ([\w:]+) -->",
        (ROOT / "agent_instructions.md").read_text(encoding="utf-8"),
    )
    sections = {parts[i]: parts[i + 1].strip() for i in range(1, len(parts), 2)}
    agent = deepcopy(stock["agent"])
    if config.enabled("C0"):
        agent["system_template"] = sections["C0:system"]
        agent["instance_template"] = sections["C0:instance"]
    suffix = ""
    for key in ("C1", "C2", "C3", "C4", "C5"):
        if config.enabled(key):
            suffix += "\n\n" + sections[key]
    agent["instance_template"] += suffix
    variables = {
        k: getattr(config, k)
        for k in ("step_limit", "budget_usd", "command_timeout", "offload_chars")
    }
    variables["_harness_prompt_suffix"] = suffix
    return agent, variables
