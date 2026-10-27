"""C2 file tools executed only inside the task container."""

import base64
import json
import re
import shlex

from pydantic import (
    BaseModel,
    ConfigDict,
    ValidationError,
    field_validator,
    model_validator,
)

from harness.hooks import Hook, RunState, Services

HELPER_PATH = "/tmp/harness/bin/tools.py"
_MAX_LINES = 200
_MAX_HITS = 100

_HELPER_SOURCE = r'''import base64
import json
import re
import sys
from pathlib import Path

MAX_LINES = 200
MAX_HITS = 100

def emit(text, status=0):
    print(text)
    raise SystemExit(status)

def main():
    try:
        request = json.loads(base64.b64decode(sys.argv[1], validate=True))
    except (IndexError, ValueError, TypeError) as error:
        emit(f"Invalid encoded tool request: {error}", 2)
    operation = request["tool"]
    args = request["arguments"]
    path = Path(args["path"])
    try:
        if operation == "read_file":
            start = args.get("start_line", 1)
            end = min(
                args.get("end_line") or start + MAX_LINES - 1,
                start + MAX_LINES - 1,
            )
            selected = []
            # Invalid UTF-8 bytes (Latin-1, a stray BOM byte) show as U+FFFD instead of failing.
            with path.open(encoding="utf-8", errors="replace") as source:
                for number, line in enumerate(source, 1):
                    if number < start:
                        continue
                    if number > end:
                        break
                    text = line.rstrip("\r\n")
                    selected.append(f"{number}: {text}")
            if not selected:
                emit(f"No lines in {path} for range {start}-{end}.", 1)
            emit("\n".join(selected))
        elif operation == "write_file":
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(args["content"], encoding="utf-8")
            emit(f"Wrote {len(args['content'])} characters to {path}.")
        elif operation == "edit_file":
            # newline="" keeps CRLF files CRLF; a snippet sent with \n matches their \r\n.
            with path.open(encoding="utf-8", newline="") as source:
                content = source.read()
            old, new = args["old"], args["new"]
            if "\r\n" in content and "\n" in old and "\r\n" not in old:
                old, new = old.replace("\n", "\r\n"), new.replace("\n", "\r\n")
            first = content.find(old)
            # find, not count: count misses overlapping matches ("aa" in "aaa").
            if first < 0:
                count = 0
            elif content.find(old, first + 1) < 0:
                count = 1
            else:
                count = max(2, content.count(old))
            if count != 1:
                emit(f"Expected exactly one match in {path}; found {count}.", 1)
            with path.open("w", encoding="utf-8", newline="") as target:
                target.write(content[:first] + new + content[first + len(old):])
            emit(f"Replaced the unique match in {path}.")
        elif operation == "search":
            expression = re.compile(args["pattern"])
            search_path = Path(args["path"])
            if search_path.is_file():
                candidates = [search_path] if not args.get("glob") or search_path.match(args["glob"]) else []
            elif search_path.is_dir():
                candidates = sorted(search_path.glob(args.get("glob") or "**/*"))
            else:
                emit(f"Search path does not exist: {search_path}", 1)
            hits = []
            truncated = False
            unreadable = 0
            for candidate in candidates:
                candidate_hits = []
                try:
                    if not candidate.is_file():
                        continue
                    with candidate.open("rb") as raw:
                        if b"\0" in raw.read(8192):
                            continue  # binary file
                    with candidate.open(encoding="utf-8", errors="replace") as source:
                        for number, line in enumerate(source, 1):
                            if expression.search(line):
                                text = line.rstrip("\r\n")
                                candidate_hits.append(
                                    f"{candidate}:{number}: {text}"
                                )
                                if len(candidate_hits) > MAX_HITS - len(hits):
                                    break
                except OSError:
                    # One unreadable file (permissions, a vanished temp file) must not
                    # discard the hits from all the others.
                    unreadable += 1
                    continue
                if len(candidate_hits) > MAX_HITS - len(hits):
                    truncated = True
                    candidate_hits = candidate_hits[:MAX_HITS - len(hits)]
                hits.extend(candidate_hits)
                if truncated:
                    break
            output = "\n".join(hits) if hits else "No matches."
            if truncated:
                output += f"\nResults capped at {MAX_HITS} hits."
            if unreadable:
                output += f"\nSkipped {unreadable} unreadable file(s)."
            emit(output)
        else:
            emit(f"Unknown tool: {operation}", 2)
    except (OSError, UnicodeError, re.error, ValueError, NotImplementedError) as error:
        emit(f"{type(error).__name__}: {error}", 1)

if __name__ == "__main__":
    main()
'''


def _string(value, name: str, example: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be a non-empty string; example: {example}")
    if "\x00" in value:
        raise ValueError(f"{name} must not contain NUL; example: {example}")
    return value


class _ToolArguments(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class _ReadFileArguments(_ToolArguments):
    path: str
    start_line: int = 1
    end_line: int | None = None

    @field_validator("start_line", "end_line")
    @classmethod
    def positive_line(cls, value):
        if value is not None and value < 1:
            raise ValueError("line numbers must be positive integers")
        return value

    @model_validator(mode="after")
    def bounded_range(self):
        end = self.end_line if self.end_line is not None else self.start_line + _MAX_LINES - 1
        if end < self.start_line:
            raise ValueError("end_line must be at least start_line")
        if end - self.start_line + 1 > _MAX_LINES:
            raise ValueError(f"read_file is limited to {_MAX_LINES} lines")
        return self


class _WriteFileArguments(_ToolArguments):
    path: str
    content: str


class _EditFileArguments(_ToolArguments):
    path: str
    old: str
    new: str

    @field_validator("old")
    @classmethod
    def non_empty_old_text(cls, value):
        if not value:
            raise ValueError("old must be non-empty")
        return value


class _SearchArguments(_ToolArguments):
    pattern: str
    path: str
    glob: str = "**/*"

    @field_validator("pattern")
    @classmethod
    def valid_regex(cls, value):
        try:
            re.compile(value)
        except re.error as error:
            raise ValueError(f"pattern is not a valid regular expression: {error}") from error
        return value


_ARGUMENT_MODELS = {
    "read_file": _ReadFileArguments,
    "write_file": _WriteFileArguments,
    "edit_file": _EditFileArguments,
    "search": _SearchArguments,
}


def _tool_schema(name: str, description: str, model: type[_ToolArguments]):
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": model.model_json_schema(),
        },
    }


_TOOLS = [
    _tool_schema(
        "read_file",
        "Read up to 200 numbered lines from a UTF-8 file.",
        _ReadFileArguments,
    ),
    _tool_schema(
        "write_file",
        "Create or overwrite a UTF-8 file.",
        _WriteFileArguments,
    ),
    _tool_schema(
        "edit_file",
        "Replace one exact, unique text snippet in a UTF-8 file.",
        _EditFileArguments,
    ),
    _tool_schema(
        "search",
        "Search a file or directory with a regular expression; returns at most 100 file:line hits.",
        _SearchArguments,
    ),
]


class ToolInterface(Hook):
    components = frozenset({"C2"})
    tools = _TOOLS

    def __init__(self, services: Services):
        # No container calls here: factories run on Harbor's event-loop thread, where the
        # adapter's blocking bridge would deadlock (issue #2). Upload on first tool use instead.
        self.environment = services.environment
        self._helper_ready = False

    def _ensure_helper(self) -> None:
        if not self._helper_ready:
            self.environment.write_text(HELPER_PATH, _HELPER_SOURCE)
            self._helper_ready = True

    def on_missing_tool_call(self, response: dict, state: RunState) -> str:
        choices = response.get("choices")
        finish_reason = None
        if isinstance(choices, list) and choices and isinstance(choices[0], dict):
            finish_reason = choices[0].get("finish_reason")
        reason = finish_reason if isinstance(finish_reason, str) else "response contained no valid tool call"
        return (
            "REJECTED: no valid bash tool call found "
            f"({reason}). Reply with brief reasoning and exactly one bash tool call."
        )

    def _validate(self, name: str, arguments: dict) -> dict:
        if name not in _ARGUMENT_MODELS:
            raise ValueError(
                f"Unknown tool {name!r}; use a declared file tool, for example "
                "read_file(path='/app/output.txt', start_line=1, end_line=20)."
            )
        examples = {
            "read_file": "read_file(path='/app/output.txt', start_line=1, end_line=20)",
            "write_file": "write_file(path='/app/output.txt', content='result')",
            "edit_file": "edit_file(path='/app/output.txt', old='before', new='after')",
            "search": "search(pattern='TODO', path='/app')",
        }
        try:
            parsed = _ARGUMENT_MODELS[name].model_validate(arguments)
        except ValidationError as error:
            detail = error.errors(include_url=False)[0]
            field = ".".join(str(part) for part in detail["loc"])
            if detail["type"] == "extra_forbidden":
                problem = f"Unexpected argument: {field}."
            elif detail["type"] == "missing":
                problem = f"Missing argument: {field}."
            else:
                problem = detail["msg"].removeprefix("Value error, ")
                if field:
                    problem = f"{field}: {problem}"
            raise ValueError(f"{problem}; example: {examples[name]}") from error

        clean = parsed.model_dump(exclude_unset=True)
        for key in ("path", "pattern", "glob"):
            if key in clean:
                clean[key] = _string(clean[key], key, examples[name])
        return clean

    def execute_tool(self, action: dict, state: RunState) -> dict:
        name = action.get("tool")
        arguments = action.get("arguments")
        try:
            if not isinstance(name, str):
                raise TypeError(
                    "Tool name must be a string; example: "
                    "read_file(path='/app/output.txt', start_line=1, end_line=20)."
                )
            if not isinstance(arguments, dict):
                raise TypeError(
                    "Tool arguments must be an object; example: "
                    "read_file(path='/app/output.txt', start_line=1, end_line=20)."
                )
            clean = self._validate(name, arguments)
        except (TypeError, ValueError) as error:
            message = str(error)
            return {
                "output": message,
                "returncode": 1,
                "exception_info": "",
                "extra": {"origin": "harness", "harness_chars": len(message)},
            }

        try:
            payload = base64.b64encode(
                json.dumps({"tool": name, "arguments": clean}, ensure_ascii=False).encode("utf-8")
            ).decode("ascii")
        except UnicodeEncodeError:
            # e.g. an unpaired surrogate from the model: a tool error, not a crashed trial.
            message = (
                "Tool arguments must be valid Unicode text (found an unpaired surrogate); "
                "resend the text without it."
            )
            return {
                "output": message,
                "returncode": 1,
                "exception_info": "",
                "extra": {"origin": "harness", "harness_chars": len(message)},
            }
        self._ensure_helper()
        command = f"python3 {shlex.quote(HELPER_PATH)} {shlex.quote(payload)}"
        result = self.environment.execute({"command": command})
        return {
            "output": result.get("output", ""),
            "returncode": result.get("returncode", 1),
            "exception_info": result.get("exception_info", ""),
            "extra": {"origin": "env"},
        }


def build_hook(config, services: Services) -> Hook:
    return ToolInterface(services)
