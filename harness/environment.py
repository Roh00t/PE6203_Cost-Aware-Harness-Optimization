"""Synchronous mini Environment backed exclusively by Harbor container calls."""

import asyncio
import concurrent.futures
import shlex
import threading
from pathlib import Path

from minisweagent.environments.local import LocalEnvironment

SAFE_ENV = {
    "PAGER": "cat",
    "MANPAGER": "cat",
    "LESS": "-R",
    "PIP_PROGRESS_BAR": "off",
    "TQDM_DISABLE": "1",
}
MAX_OUTPUT = 1024 * 1024


class HarborEnvironment:
    def __init__(
        self,
        environment,
        loop,
        *,
        template_vars,
        timeout=30,
        events=None,
        stop_event=None,
    ):
        self.environment, self.loop = environment, loop
        self.template_vars, self.timeout, self.events = template_vars, timeout, events
        self.stop_event = stop_event or threading.Event()
        self.pending = set()
        self.lock = threading.Lock()

    def _wait(self, coroutine):
        if self.stop_event.is_set():
            coroutine.close()
            raise RuntimeError("Trial cancelled")
        future = asyncio.run_coroutine_threadsafe(coroutine, self.loop)
        with self.lock:
            self.pending.add(future)
        try:
            while True:
                try:
                    return future.result(timeout=0.25)
                except concurrent.futures.TimeoutError:
                    # A finished coroutine can itself raise TimeoutError. Do not poll it forever.
                    if future.done():
                        raise
                    if self.stop_event.is_set():
                        future.cancel()
                        raise RuntimeError("Trial cancelled")
        finally:
            with self.lock:
                self.pending.discard(future)

    def cancel(self):
        self.stop_event.set()
        with self.lock:
            for future in self.pending:
                future.cancel()

    def execute(self, action, cwd="", *, timeout=None):
        command = action.get("command")
        if not isinstance(command, str):
            return {
                "output": "",
                "returncode": -1,
                "exception_info": "Command must be a string",
            }
        # Stream drain in the container prevents Harbor from materializing unbounded output.
        # pipefail is not used: PIPESTATUS[0] preserves the agent command's exit status.
        drain = 'import sys; n=0\nwhile True:\n b=sys.stdin.buffer.read(65536)\n if not b: break\n if n<1048576: sys.stdout.buffer.write(b[:1048576-n])\n n+=len(b)\nif n>1048576: sys.stdout.buffer.write(b"\\n[output truncated at 1 MB]\\n")'
        inner = "exec 2>&1; " + command
        wrapped = (
            "timeout --signal=KILL "
            + str(timeout or self.timeout)
            + "s bash -c "
            + shlex.quote(inner)
        )
        wrapped += " | python3 -c " + shlex.quote(drain) + "; exit ${PIPESTATUS[0]}"
        result = self._wait(
            self.environment.exec(
                command=wrapped,
                cwd=cwd or None,
                env=dict(SAFE_ENV),
                timeout_sec=(timeout or self.timeout) + 15,
            )
        )
        output = {
            "output": (result.stdout or "") + (result.stderr or ""),
            "returncode": result.return_code,
            "exception_info": "",
        }
        if result.return_code in (124, 137):
            output["exception_info"] = "Command timed out or was killed"
            output["extra"] = {"exception_type": "CommandTimeout"}
            if self.events:
                self.events.write(
                    type="command_timeout", timeout=timeout or self.timeout
                )
        return output

    def check_finished(self, output):
        LocalEnvironment._check_finished(self, output)

    def write_text(self, path, text):
        # Large payload travels through Harbor's upload API, not an oversized shell argv.
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            local = Path(tmp) / "observation"
            local.write_text(text, encoding="utf-8")
            result = self._wait(
                self.environment.exec(
                    command="mkdir -p "
                    + shlex.quote(str(Path(path).parent).replace("\\", "/")),
                    env=dict(SAFE_ENV),
                    timeout_sec=30,
                )
            )
            if result.return_code:
                raise RuntimeError("Could not create offload directory")
            self._wait(self.environment.upload_file(local, path))

    def get_template_vars(self, **kwargs):
        return {**SAFE_ENV, **self.template_vars, **kwargs}

    def serialize(self):
        return {
            "info": {
                "config": {
                    "environment_type": "harness.environment.HarborEnvironment",
                    "environment": {"timeout": self.timeout, "env": SAFE_ENV},
                }
            }
        }
