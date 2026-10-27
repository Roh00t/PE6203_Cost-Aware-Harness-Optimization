"""C4 repeat-failure, stall, and timeout recovery."""

import hashlib
import json

from harness.hooks import Decision, Hook, RunState, Services

_STALL_NUDGE = (
    "\n[Harness recovery] The same observation has repeated three times. "
    "Please re-read the task and check your assumptions before trying a different approach."
)
_TIMEOUT_RECOVERY = (
    "\n[Harness recovery] The command timed out or was killed. If it is safe to "
    "continue asynchronously, start it with `nohup CMD > /tmp/job.log 2>&1 &`, "
    "then poll with `tail -n 50 /tmp/job.log`."
)
_REPEAT_SUFFIX = "state in one sentence why it failed, then try a different approach."


def _normalised_command(command: str) -> str:
    return " ".join(command.split())


def _append_harness_text(result: dict, text: str) -> dict:
    output = result.get("output", "")
    separator = "" if not output or output.endswith("\n") else "\n"
    addition = separator + text.lstrip("\n")
    extra = dict(result.get("extra") or {})
    extra["harness_chars"] = int(extra.get("harness_chars", 0)) + len(addition)
    return {**result, "output": output + addition, "extra": extra}


class FailureRecovery(Hook):
    components = frozenset({"C4"})

    def __init__(self, events):
        self.events = events
        self.failures: dict[str, int] = {}
        self.last_errors: dict[str, str] = {}
        self.last_observation_hash: str | None = None
        self.observation_streak = 0
        self.nudged_observations: set[str] = set()

    def before_execute(self, action: dict, state: RunState) -> Decision:
        command = action.get("command")
        if not isinstance(command, str):
            return Decision()
        digest = hashlib.sha256(_normalised_command(command).encode("utf-8")).hexdigest()
        failures = self.failures.get(digest, 0)
        if failures < 2:
            return Decision()
        error = self.last_errors.get(digest, "No error details were recorded.")
        feedback = (
            f"REJECTED: this command has already failed {failures} times. "
            f"Last error: {error}\n{_REPEAT_SUFFIX}"
        )
        self.events.write(
            type="repeat_intercept",
            step=state.step,
            command_hash=digest,
            failures=failures,
        )
        return Decision(
            allowed=False,
            feedback=feedback,
            rule_id="C4-REPEAT-FAILURE",
            event="repeat_intercept",
        )

    def after_execute(self, action: dict, result: dict, state: RunState) -> dict:
        command = action.get("command")
        if isinstance(command, str):
            digest = hashlib.sha256(_normalised_command(command).encode("utf-8")).hexdigest()
            returncode = result.get("returncode")
            extra = result.get("extra") or {}
            if (
                isinstance(returncode, int)
                and not isinstance(returncode, bool)
                and returncode != 0
                and extra.get("origin") != "harness"
            ):
                # Count back-to-back failures only: a command in between may have changed the
                # state (file created, process started), so a later retry is not blind.
                self.failures = {digest: self.failures.get(digest, 0) + 1}
                output = str(result.get("output", ""))
                exception = str(result.get("exception_info", ""))
                self.last_errors[digest] = (output + ("\n" + exception if exception else ""))[-1000:]
            elif extra.get("origin") != "harness":
                self.failures = {}

            if returncode in (124, 137):
                result = _append_harness_text(result, _TIMEOUT_RECOVERY)

        observation = json.dumps(
            {
                "output": result.get("output", ""),
                "returncode": result.get("returncode"),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        observation_hash = hashlib.sha256(observation.encode("utf-8")).hexdigest()
        if observation_hash == self.last_observation_hash:
            self.observation_streak += 1
        else:
            self.last_observation_hash = observation_hash
            self.observation_streak = 1
        if self.observation_streak >= 3 and observation_hash not in self.nudged_observations:
            self.nudged_observations.add(observation_hash)
            result = _append_harness_text(result, _STALL_NUDGE)
            self.events.write(
                type="stall_nudge",
                step=state.step,
                observation_hash=observation_hash,
            )
        return result


def build_hook(config, services: Services) -> Hook:
    return FailureRecovery(services.events)
