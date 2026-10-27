"""Durable, append-only records with no request headers or credentials."""

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path


class JsonlLog:
    def __init__(self, path: Path, identity: dict):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.identity = identity
        self._lock = threading.Lock()

    def write(self, **record):
        record = {
            **self.identity,
            "ts": datetime.now(timezone.utc).isoformat(),
            **record,
        }
        with self._lock, self.path.open("a", encoding="utf-8") as out:
            out.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
            out.flush()
            os.fsync(out.fileno())


def origin_counts(messages: list[dict]) -> dict[str, int]:
    # "feedback": format-error messages, which the stock loop sends too, so they are not
    # harness overhead (harness-v1 counted them as "harness").
    counts = dict.fromkeys(("system", "task", "model", "env", "harness", "feedback"), 0)
    for i, msg in enumerate(messages):
        text = json.dumps(
            {k: v for k, v in msg.items() if k != "extra"}, ensure_ascii=False
        )
        extra = msg.get("extra") or {}
        origin = extra.get("origin") or {
            "system": "system",
            "assistant": "model",
            "tool": "env",
        }.get(msg["role"], "task" if i == 1 else "harness")
        harness = min(len(text), int(extra.get("harness_chars", 0)))
        counts[origin] += len(text) - harness
        counts["harness"] += harness
    return counts
