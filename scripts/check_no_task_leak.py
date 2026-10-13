#!/usr/bin/env python3
"""Reject task-specific identifiers and instruction filenames in agent code."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


_FILENAME = re.compile(r"(?<![\w.-])(?:[A-Za-z0-9_.-]+/)*([A-Za-z0-9_.-]+\.[A-Za-z0-9]{1,12})(?![\w.-])")
_IGNORED_DIRS = {".git", "__pycache__", ".pytest_cache"}


@dataclass(frozen=True)
class Leak:
    path: Path
    line: int
    value: str
    kind: str
    text: str


def _task_sources(tasks_root: Path) -> tuple[set[str], set[str]]:
    if not tasks_root.is_dir():
        raise FileNotFoundError(f"TUA-Bench task sources not found: {tasks_root}")

    task_ids: set[str] = set()
    filenames: set[str] = set()
    task_dirs = sorted(path for path in tasks_root.iterdir() if path.is_dir())
    if not task_dirs:
        raise FileNotFoundError(f"No task instruction directories found under: {tasks_root}")

    for task_dir in task_dirs:
        task_file = task_dir / "task.toml"
        if not task_file.is_file():
            continue
        instruction_file = task_dir / "instruction.md"
        if not instruction_file.is_file():
            raise FileNotFoundError(f"Task instruction not found: {instruction_file}")
        task_ids.add(task_dir.name)
        try:
            instruction = instruction_file.read_text(encoding="utf-8")
        except OSError as error:
            raise ValueError(f"Cannot read task instruction {instruction_file}: {error}") from error
        filenames.update(match.group(1) for match in _FILENAME.finditer(instruction))

    if not task_ids:
        raise FileNotFoundError(f"No task.toml instruction files found under: {tasks_root}")
    return task_ids, filenames


def _target_files(repo_root: Path) -> Iterable[Path]:
    targets = (repo_root / "harness", repo_root / "configs" / "harness", repo_root / "agent_instructions.md")
    for target in targets:
        if target.is_file():
            yield target
        elif target.is_dir():
            for path in sorted(target.rglob("*")):
                if path.is_file() and not any(part in _IGNORED_DIRS for part in path.parts):
                    yield path


def find_leaks(repo_root: Path, tasks_root: Path) -> list[Leak]:
    task_ids, filenames = _task_sources(tasks_root)
    leaks: list[Leak] = []
    for path in _target_files(repo_root):
        try:
            contents = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        relative_path = path.relative_to(repo_root)
        for line_number, line in enumerate(contents.splitlines(), start=1):
            for task_id in task_ids:
                if task_id in line:
                    leaks.append(Leak(relative_path, line_number, task_id, "task ID", line.strip()))
            for filename in filenames:
                if filename in line:
                    leaks.append(Leak(relative_path, line_number, filename, "instruction filename", line.strip()))
    return leaks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--tasks-root", type=Path)
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    tasks_root = (args.tasks_root or repo_root / "data" / "TUA-Bench" / "tasks").resolve()

    try:
        leaks = find_leaks(repo_root, tasks_root)
    except (FileNotFoundError, ValueError) as error:
        print(f"check_no_task_leak: ERROR: {error}", file=sys.stderr)
        return 2

    if leaks:
        for leak in leaks:
            print(f"{leak.path}:{leak.line}: {leak.kind} {leak.value!r}: {leak.text}")
        print(f"check_no_task_leak: FAILED ({len(leaks)} leak(s))", file=sys.stderr)
        return 1
    print("check_no_task_leak: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())