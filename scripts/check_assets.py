#!/usr/bin/env python3
"""Fail if any task in an args file is missing assets that `setup-env` downloads.

Some TUA-Bench inputs, reference files and test fixtures are not in git; the
benchmark's `uv run setup-env` downloads them. Without them the oracle and
every agent fail for reasons unrelated to the harness. This uses the
benchmark's own target list (repo_env.setup_env.downloaded_data_targets).

    python3 scripts/check_assets.py configs/eval_tasks.args
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TUA_ROOT = REPO_ROOT / "data" / "TUA-Bench"


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    wanted = set(Path(sys.argv[1]).read_text().split()[1::2])

    sys.path.insert(0, str(TUA_ROOT))
    from repo_env.setup_env import downloaded_data_targets  # stdlib-only module

    tasks_dir = (TUA_ROOT / "tasks").resolve()
    missing: dict[str, list[str]] = {}
    for target in downloaded_data_targets():
        rel = Path(target).resolve().relative_to(tasks_dir)
        task_id = rel.parts[0]
        if task_id not in wanted:
            continue
        ok = target.is_dir() and any(target.iterdir()) if target.is_dir() else (
            target.is_file() and target.stat().st_size > 0)
        if not ok:
            missing.setdefault(task_id, []).append(str(Path(*rel.parts[1:])))

    if missing:
        lines = [f"  {t}: {len(f)} missing (e.g. {f[0]})" for t, f in sorted(missing.items())]
        sys.exit("Downloaded assets missing for:\n" + "\n".join(lines)
                 + "\nRun: (cd data/TUA-Bench && uv run setup-env)")
    print(f"OK: setup-env assets present for every task in {sys.argv[1]}")


if __name__ == "__main__":
    main()
