"""Host model gateway using the same LiteLLM formatting as stock mini-swe-agent."""

import json
import threading
import time
from copy import deepcopy
from decimal import Decimal

import litellm
from minisweagent.exceptions import FormatError
from minisweagent.models.litellm_model import LitellmModel
from minisweagent.models.utils.actions_toolcall import BASH_TOOL

from harness.components.budget import stop_cost
from harness.telemetry import origin_counts


class UsageError(RuntimeError):
    """Unknown cost is an infrastructure error, never silently free."""


class OpenRouterGateway(LitellmModel):
    def __init__(
        self,
        *,
        calls,
        events,
        price,
        stop_event=None,
        budget_usd=None,
        on_usage=None,
        job_ledger=None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.calls, self.events, self.price = calls, events, price
        self.stop_event = stop_event or threading.Event()
        self.budget = Decimal(str(budget_usd)) if budget_usd is not None else None
        self.spent = Decimal("0")
        self.unknown_reserved = Decimal("0")
        self.job_ledger = job_ledger
        self.on_usage = on_usage or (lambda gateway: None)
        self.n_input = self.n_output = self.n_cached = 0
        self.call_idx = self.step = 0
        self.tool_plugins = {}
        self.request_origins = {}
        self.missing_tool_feedback = None
        self.last_response = None
        self.usage_complete = True
        pinned = self.config.model_kwargs["extra_body"]["provider"]["order"]
        if pinned != [price["provider"]]:
            raise ValueError("Model provider differs from frozen pricing")

    def tools_for_request(self):
        tools = [BASH_TOOL]
        for name, plugin in self.tool_plugins.items():
            tools.extend(
                tool for tool in plugin.tools if tool["function"]["name"] == name
            )
        return tools

    def request_reserve(self, messages):
        # Conservative byte-based input allowance + template overhead. A local estimate,
        # not provider-certified tokenization. Keep max_tokens/decoding unchanged.
        size = (
            len(
                json.dumps(
                    {"messages": messages, "tools": self.tools_for_request()},
                    ensure_ascii=False,
                ).encode("utf-8")
            )
            + 4096
        )
        output = self.config.model_kwargs["max_tokens"]
        return (
            Decimal(size) * Decimal(str(self.price["prompt_usd_per_mtok"]))
            + Decimal(output) * Decimal(str(self.price["completion_usd_per_mtok"]))
        ) / Decimal(1000000)

    def _call_api(self, messages):
        # Disable LiteLLM's own retries so each attempt has exactly one log record.
        return litellm.completion(
            model=self.config.model_name,
            messages=messages,
            tools=self.tools_for_request(),
            **deepcopy(self.config.model_kwargs),
            num_retries=0,
        )

    def _parse_actions(self, response):
        tool_calls = response.choices[0].message.tool_calls or []
        if not self.tool_plugins or all(t.function.name == "bash" for t in tool_calls):
            return super()._parse_actions(response)
        actions = []
        for tool in tool_calls:
            if tool.function.name == "bash":
                isolated = deepcopy(response)
                isolated.choices[0].message.tool_calls = [tool]
                actions.extend(super()._parse_actions(isolated))
                continue
            if tool.function.name not in self.tool_plugins:
                return super()._parse_actions(response)  # stock unknown-tool error
            try:
                args = json.loads(tool.function.arguments)
                if not isinstance(args, dict):
                    raise ValueError("Arguments must be an object")
            except (ValueError, TypeError):
                raise FormatError(
                    {
                        "role": "user",
                        "content": "Tool arguments must be a JSON object.",
                        "extra": {"interrupt_type": "FormatError"},
                    }
                )
            actions.append(
                {"tool": tool.function.name, "arguments": args, "tool_call_id": tool.id}
            )
        return actions

    def _price_response(self, data):
        usage = data.get("usage") or {}
        for key in ("prompt_tokens", "completion_tokens"):
            value = usage.get(key)
            if type(value) is not int or value < 0:
                raise UsageError("Missing or invalid " + key)
        self.n_input += usage["prompt_tokens"]
        self.n_output += usage["completion_tokens"]
        cached = (usage.get("prompt_tokens_details") or {}).get("cached_tokens")
        reasoning = (usage.get("completion_tokens_details") or {}).get(
            "reasoning_tokens"
        )
        self.n_cached += cached or 0
        cost = (
            Decimal(usage["prompt_tokens"])
            * Decimal(str(self.price["prompt_usd_per_mtok"]))
            + Decimal(usage["completion_tokens"])
            * Decimal(str(self.price["completion_usd_per_mtok"]))
        ) / Decimal(1000000)
        self.spent += cost
        return cost, usage, cached, reasoning

    def query(self, messages, **kwargs):
        if kwargs:
            raise ValueError(
                "Per-call model overrides are forbidden; edit no frozen decoding settings"
            )
        prepared = self._prepare_messages_for_api(messages)
        origins = origin_counts(messages)
        for attempt in range(4):
            if self.stop_event.is_set():
                raise RuntimeError("Trial cancelled")
            reserve = self.request_reserve(prepared)
            if (
                self.budget is not None
                and self.spent + self.unknown_reserved + reserve > self.budget
            ):
                self.events.write(
                    type="cap_reached", step=self.step, spent_usd=float(self.spent)
                )
                stop_cost()
            reservation = self.job_ledger.reserve(reserve) if self.job_ledger else None
            self.call_idx += 1
            record = dict(
                call_idx=self.call_idx,
                step=self.step,
                purpose="agent",
                model=self.config.model_name.removeprefix("openrouter/"),
                provider=None,
                provider_expected=self.price["provider"],
                prompt_tokens=None,
                completion_tokens=None,
                reasoning_tokens=None,
                cached_tokens=None,
                cost_table_usd=None,
                cost_reported_usd=None,
                finish_reason=None,
                error=None,
                retries=attempt,
                prompt_chars_by_origin=origins,
            )
            started = time.monotonic()
            try:
                response = self._call_api(prepared)
            except Exception as error:
                status = getattr(error, "status_code", None)
                record.update(
                    error=type(error).__name__,
                    http_status=status,
                    latency_ms=round((time.monotonic() - started) * 1000),
                )
                self.calls.write(**record)
                retryable = (
                    status == 429
                    or (isinstance(status, int) and 500 <= status < 600)
                    or isinstance(error, (litellm.Timeout, litellm.APIConnectionError))
                )
                # A failed attempt may have been billed; do not invent zero usage.
                self.usage_complete = False
                self.unknown_reserved += reserve
                self.on_usage(self)
                if not retryable or attempt == 3:
                    raise
                self.events.write(
                    type="api_retry",
                    step=self.step,
                    retry=attempt + 1,
                    error=type(error).__name__,
                )
                if self.stop_event.wait(2 ** (attempt + 1)):
                    raise RuntimeError("Trial cancelled") from error
                continue
            data = response.model_dump(mode="json")
            self.last_response = data
            record.update(
                model=data.get("model"),
                provider=data.get("provider"),
                response_id=data.get("id"),
                finish_reason=response.choices[0].finish_reason,
                latency_ms=round((time.monotonic() - started) * 1000),
            )
            try:
                cost, usage, cached, reasoning = self._price_response(data)
            except UsageError:
                self.usage_complete = False
                record["error"] = "UsageError"
                self.calls.write(**record)
                self.on_usage(self)
                raise
            if self.job_ledger:
                self.job_ledger.settle(reservation, cost)
            if cost > reserve:
                self.events.write(
                    type="reservation_underestimate",
                    step=self.step,
                    reserved_usd=float(reserve),
                    actual_usd=float(cost),
                )
            record.update(
                prompt_tokens=usage["prompt_tokens"],
                completion_tokens=usage["completion_tokens"],
                reasoning_tokens=reasoning,
                cached_tokens=cached,
                cost_table_usd=float(cost),
                cost_reported_usd=usage.get("cost"),
            )
            expected_model = self.config.model_name.removeprefix("openrouter/")
            observed_model = data.get("model")
            # LiteLLM may retain the routing prefix, but must not change the model.
            mismatch = observed_model not in (
                expected_model,
                self.config.model_name,
            ) or (
                data.get("provider") is not None
                and data["provider"] != self.price["provider"]
            )
            if mismatch:
                record["error"] = "EndpointMismatch"
            try:
                if mismatch:
                    raise UsageError(
                        "Response endpoint does not match frozen model/provider"
                    )
                actions = self._parse_actions(response)
            except FormatError as error:
                record["error"] = "FormatError"
                error.messages[0].setdefault("extra", {}).update(
                    cost=float(cost), response=data, origin="harness"
                )
                if (
                    not response.choices[0].message.tool_calls
                    and self.missing_tool_feedback
                ):
                    feedback = self.missing_tool_feedback(data)
                    if feedback is not None:
                        error.messages[0]["content"] = feedback
                self.events.write(
                    type="format_error",
                    step=self.step,
                    finish_reason=record["finish_reason"],
                )
                raise
            finally:
                self.calls.write(**record)
                self.on_usage(self)
            message = response.choices[0].message.model_dump()
            message["extra"] = dict(
                actions=actions, response=data, cost=float(cost), timestamp=time.time()
            )
            return message
        raise AssertionError("unreachable")
