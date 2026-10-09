#!/usr/bin/env python3
"""Confirm Harbor resolves an args file to exactly the intended tasks.

Uses Harbor's own DatasetConfig (the code path `harbor run -p tasks -i ...`
takes), so a prefix/glob mismatch or a task Harbor deems invalid is caught
before any tokens are spent. Must run inside the TUA-Bench environment:

    uv run --project data/TUA-Bench python scripts/check_harbor_filter.py configs/eval_tasks.args
"""

import asyncio
import sys
from pathlib import Path

from harbor.models.job.config import DatasetConfig

REPO_ROOT = Path(__file__).resolve().parent.parent
TASKS_DIR = REPO_ROOT / "data" / "TUA-Bench" / "tasks"


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    tokens = Path(sys.argv[1]).read_text().split()
    if tokens[0::2] != ["-i"] * (len(tokens) // 2) or len(tokens) % 2:
        sys.exit(f"{sys.argv[1]} is not a sequence of `-i <task-id>` pairs")
    wanted = tokens[1::2]

    config = DatasetConfig(path=TASKS_DIR, task_names=wanted)
    resolved = sorted(c.path.name for c in asyncio.run(config.get_task_configs()))

    if resolved != sorted(wanted):
        sys.exit(f"Harbor resolved {len(resolved)} tasks, expected {len(wanted)}.\n"
                 f"  missing: {sorted(set(wanted) - set(resolved))}\n"
                 f"  unexpected: {sorted(set(resolved) - set(wanted))}")
    print(f"OK: Harbor resolves {sys.argv[1]} to exactly {len(resolved)} tasks")


if __name__ == "__main__":
    main()
