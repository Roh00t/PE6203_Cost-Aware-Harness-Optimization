"""C3 budget checks and a process-safe optional job reservation ledger."""

import sqlite3
from pathlib import Path

from minisweagent.exceptions import LimitsExceeded


class CostCapExceeded(LimitsExceeded):
    pass


def stop_cost(status="CostCapExceeded"):
    raise CostCapExceeded(
        {
            "role": "exit",
            "content": status,
            "extra": {"exit_status": status, "submission": ""},
        }
    )


class JobLedger:
    """Reservations survive crashes; use a fresh ledger per explicitly approved run."""

    def __init__(self, path, cap):
        self.path, self.cap = Path(path), float(cap)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS limits (id INTEGER PRIMARY KEY, cap REAL)"
            )
            db.execute("INSERT OR IGNORE INTO limits VALUES (1, ?)", (self.cap,))
            if (
                db.execute("SELECT cap FROM limits WHERE id=1").fetchone()[0]
                != self.cap
            ):
                raise ValueError("Job ledger budget differs from its original cap")
            db.execute(
                "CREATE TABLE IF NOT EXISTS charges (id INTEGER PRIMARY KEY, amount REAL, status TEXT)"
            )

    def reserve(self, amount):
        with sqlite3.connect(self.path, timeout=30) as db:
            db.execute("BEGIN IMMEDIATE")
            spent = db.execute(
                "SELECT COALESCE(SUM(amount),0) FROM charges"
            ).fetchone()[0]
            if spent + float(amount) > self.cap:
                stop_cost("budget_abort")
            return db.execute(
                "INSERT INTO charges(amount,status) VALUES (?,?)",
                (float(amount), "reserved"),
            ).lastrowid

    def settle(self, reservation, amount):
        with sqlite3.connect(self.path, timeout=30) as db:
            db.execute(
                "UPDATE charges SET amount=?, status=? WHERE id=?",
                (float(amount), "measured", reservation),
            )


class BudgetManager:
    def __init__(self, config, events):
        self.config, self.events = config, events
        self.nudged = set()

    def observation(self, result, state, context_tokens):
        text = f"\n[budget] step {state.step}/{self.config.step_limit} | ${state.spent_usd:.8f}/${self.config.budget_usd:.2f} | context ~{context_tokens} tok | elapsed {state.elapsed_seconds / 60:.1f}/40 min"
        for fraction, message in (
            (0.7, "stop exploring; verify outputs"),
            (0.9, "submit now if outputs exist"),
        ):
            if (
                state.step >= self.config.step_limit * fraction
                and fraction not in self.nudged
            ):
                text += "\n" + message
                self.nudged.add(fraction)
                self.events.write(
                    type="budget_nudge", step=state.step, fraction=fraction
                )
        return {
            **result,
            "output": result.get("output", "") + text,
            "extra": {
                **result.get("extra", {}),
                "harness_chars": result.get("extra", {}).get("harness_chars", 0)
                + len(text),
            },
        }
