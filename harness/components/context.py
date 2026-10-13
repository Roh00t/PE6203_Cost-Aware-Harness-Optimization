"""Deterministic C1 views; never edit the full saved trajectory."""

import json
from copy import deepcopy


def estimate_tokens(messages: list[dict]) -> int:
    clean = [{k: v for k, v in m.items() if k != "extra"} for m in messages]
    return (len(json.dumps(clean, ensure_ascii=False)) + 3) // 4


def exchanges(history: list[dict]) -> tuple[list[dict], list[list[dict]]]:
    prefix, groups = history[:2], []
    for msg in history[2:]:
        if msg["role"] == "assistant" or not groups:
            groups.append([])
        groups[-1].append(msg)
    return prefix, groups


class ContextManager:
    def __init__(self, config, env, events):
        self.config, self.env, self.events = config, env, events
        self.index = 0

    def offload(self, output: dict, step: int) -> dict:
        raw = output.get("output", "")
        if len(raw) <= self.config.offload_chars:
            return output
        self.index += 1
        path = f"/tmp/harness/obs/step_{step}_{self.index}.log"
        self.env.write_text(path, raw)
        stub = f"\n[offloaded {len(raw)} characters, {len(raw.splitlines())} lines to {path}; inspect with grep or sed -n]\n"
        self.events.write(type="offload", step=step, path=path, chars=len(raw))
        return {
            **output,
            "output": raw[:800] + stub + raw[-800:],
            "extra": {
                **output.get("extra", {}),
                "full_output": raw,
                "harness_chars": len(stub),
            },
        }

    def view(self, history: list[dict], step: int) -> list[dict]:
        view = deepcopy(history)
        prefix, groups = exchanges(view)
        # Preserve the first exchange and recent exchanges, including paired tool results.
        middle = groups[1 : -self.config.keep_tail]
        for group in middle:
            for msg in group:
                if (
                    msg["role"] == "tool"
                    and isinstance(msg.get("content"), str)
                    and len(msg["content"]) > 300
                ):
                    msg["content"] = (
                        msg["content"][:300] + "\n[older observation shortened]"
                    )
                    msg.setdefault("extra", {})["harness_chars"] = 29
        if not middle or estimate_tokens(view) <= self.config.compact_at_tokens:
            return view
        lines = []
        for index, group in enumerate(middle, 2):
            actions = [
                a for m in group for a in (m.get("extra") or {}).get("actions", [])
            ]
            outputs = [m for m in group if m["role"] in ("tool", "user")]
            command = " | ".join(
                str(a.get("command", a.get("tool", ""))) for a in actions
            )[:120]
            summaries = []
            for msg in outputs:
                extra = msg.get("extra") or {}
                raw = extra.get(
                    "full_output", extra.get("raw_output", msg.get("content", ""))
                )
                first = str(raw).splitlines()[0] if raw else ""
                summaries.append(f"rc={extra.get('returncode')} {first}")
            result = "; ".join(summaries)[:300]
            lines.append(f"exchange {index}: {command}: {result}")
        digest = {
            "role": "user",
            "content": "[Earlier exchanges condensed]\n" + "\n".join(lines),
            "extra": {"origin": "harness"},
        }
        compact = (
            prefix
            + groups[0]
            + [digest]
            + [m for g in groups[-self.config.keep_tail :] for m in g]
        )
        self.events.write(
            type="compaction",
            step=step,
            before_tokens=estimate_tokens(view),
            after_tokens=estimate_tokens(compact),
            exchanges=len(middle),
        )
        return compact
