"""C5 one-time pre-submission output verification."""

import re
import shlex
import time

from harness.hooks import Decision, Hook, RunState, Services

_PATH = re.compile(
    r"`(?P<quoted>/[^`\n]*\.[A-Za-z0-9]{1,12})`|"
    r"(?P<bare>(?<![\w:/])/(?:[A-Za-z0-9._+-]+/)*[A-Za-z0-9._+-]+\.[A-Za-z0-9]{1,12}(?![\w]))"
)
_MTIME_CHECK = (
    "python3 -c "
    + shlex.quote(
        "import os,sys; p=sys.argv[1]; start=float(sys.argv[2]); "
        "sys.exit(0 if os.path.getmtime(p) >= start else 1)"
    )
)
_READBACK_REQUEST = (
    "Confirm each requirement by reading the outputs back and checking that they "
    "contain the requested result. Then submit again."
)


def extract_paths(task: str) -> list[str]:
    paths = [
        match.group("quoted") or match.group("bare")
        for match in _PATH.finditer(task)
    ]
    return list(dict.fromkeys(paths))


class SubmissionGate(Hook):
    components = frozenset({"C5"})
    max_gate_rejections = 1

    def __init__(self, services: Services, trial_started_at: float | None = None):
        self.environment = services.environment
        self.config = services.config
        self.trial_started_at = time.time() if trial_started_at is None else trial_started_at
        self.rejections = 0

    def before_submit(self, action: dict, state: RunState) -> Decision:
        limit = int(self.config.step_limit)
        if (
            self.rejections >= self.max_gate_rejections
            or limit <= 0
            or state.step >= 0.9 * limit
        ):
            return Decision()

        paths = extract_paths(state.task)
        checks: list[tuple[str, bool]] = []
        for path in paths:
            quoted = shlex.quote(path)
            command = (
                f"test -s {quoted} && {_MTIME_CHECK} {quoted} "
                f"{self.trial_started_at:.6f}"
            )
            result = self.environment.execute({"command": command})
            checks.append((path, result.get("returncode") == 0))

        lines = [
            f"{'✓' if exists else '✗'} {path} "
            f"({'exists, non-empty, and written during this trial' if exists else 'missing, empty, or not written during this trial'})"
            for path, exists in checks
        ]
        checklist = "\n".join(lines) if lines else "No absolute output file paths were found to check."
        feedback = (
            "Before submitting, verify the task requirements.\n"
            f"{checklist}\n\n"
            f"Task excerpt:\n{state.task[:600]}\n\n"
            f"{_READBACK_REQUEST}"
        )
        self.rejections += 1
        return Decision(
            allowed=False,
            feedback=feedback,
            rule_id="C5-SUBMIT-GATE",
            event="submit_gate",
        )


def build_hook(config, services: Services) -> Hook:
    return SubmissionGate(services)
