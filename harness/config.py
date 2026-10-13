"""Validated component configuration; frozen model files remain authoritative."""

from copy import deepcopy
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

ROOT = Path(__file__).resolve().parents[1]


class HarnessConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    config_id: str = "H0"
    model_file: str = "configs/models/base.yaml"
    components: list[Literal["C0", "C1", "C2", "C3", "C4", "C5"]] = Field(
        default_factory=list
    )
    plugins: list[str] = Field(default_factory=list)
    guardrail_factory: str = "harness.isha_adapter:build_guardrail"
    step_limit: int = Field(default=50, gt=0)
    budget_usd: float = Field(default=0.01, gt=0)
    command_timeout: int = Field(default=180, gt=0)
    offload_chars: int = Field(default=2000, ge=1600)
    compact_at_tokens: int = Field(default=24000, gt=0)
    keep_tail: int = Field(default=6, ge=1)

    @model_validator(mode="after")
    def validate_flags(self):
        if len(set(self.components)) != len(self.components):
            raise ValueError("Duplicate component flags")
        if self.config_id == "H0" and self.components:
            raise ValueError("H0 must have all components disabled")
        return self

    def enabled(self, component: str) -> bool:
        return component in self.components


def resolve(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def load_config(path: str | Path) -> tuple[HarnessConfig, dict]:
    config = HarnessConfig.model_validate(
        yaml.safe_load(resolve(path).read_text(encoding="utf-8"))
    )
    stock = deepcopy(
        yaml.safe_load(resolve(config.model_file).read_text(encoding="utf-8"))
    )
    model = stock["model"]
    provider = model["model_kwargs"]["extra_body"]["provider"]
    if (
        len(provider.get("order", [])) != 1
        or provider.get("allow_fallbacks") is not False
    ):
        raise ValueError(
            "The frozen model must pin exactly one provider without fallback"
        )
    if not model["model_name"].startswith("openrouter/"):
        raise ValueError("All model calls must use OpenRouter")
    # Harbor's stock CLI uses --yolo --cost-limit 0. DefaultAgent is already noninteractive.
    stock["agent"].pop("mode", None)
    stock["agent"]["cost_limit"] = 0.0
    stock["agent"]["step_limit"] = config.step_limit if config.enabled("C3") else 0
    return config, stock
