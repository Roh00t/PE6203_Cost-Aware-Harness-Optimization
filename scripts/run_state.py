#!/usr/bin/env python3
"""Classify a per-task Harbor job folder for harbor_run.sh's resume logic.

    python3 scripts/run_state.py jobs/<run>/<task>     # prints finished | errored | interrupted

- interrupted: the job never finished, or a result.json is unreadable (killed mid-write).
- errored: the job finished, but every trial raised an exception that is not an outcome of the
  agent's own run (Docker build, network, crashed agent install, rate limit): an infrastructure
  error, set aside and rerun, never scored (system_architecture.md §10.3).
- finished: anything else. Harbor's AgentTimeoutError counts as finished: the wall-clock budget
  ran out, the verifier still scored the trial, and classify_failures.py labels it
  budget_exhausted. Rerunning it would replace a real result with a fresh sample.

Runs under the system python3 (3.9 on macOS), like the rest of harbor_run.sh.
"""

import json
import sys
from pathlib import Path

# Exceptions that end a trial as a scored outcome rather than an infrastructure failure.
OUTCOME_EXCEPTIONS = {"AgentTimeoutError"}


def _load(path: Path):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def job_state(job: Path) -> str:
    result = _load(job / "result.json")
    if not result or not result.get("finished_at"):
        return "interrupted"
    trials = [_load(path) for path in sorted(job.glob("*__*/result.json"))]
    if any(trial is None for trial in trials):
        return "interrupted"
    exceptions = [
        ((info.get("exception_type") if isinstance(info, dict) else None) or "unknown") if info else None
        for info in (trial.get("exception_info") for trial in trials)
    ]
    if trials and all(exceptions) and not OUTCOME_EXCEPTIONS.intersection(exceptions):
        return "errored"
    return "finished"


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__.strip().splitlines()[2].strip())
    print(job_state(Path(sys.argv[1])))
