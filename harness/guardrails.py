"""Deterministic command checks defined in guardrails.md section 3."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal


Action = Literal["allow", "block", "log", "note"]
_FLAGS = re.MULTILINE


@dataclass(frozen=True)
class GuardrailResult:
    rule_id: str | None
    action: Action
    message: str | None = None

    @property
    def blocked(self) -> bool:
        return self.action == "block"


@dataclass(frozen=True)
class _Rule:
    rule_id: str
    patterns: tuple[re.Pattern[str], ...]
    message: str
    action: Action = "block"
    c2_only: bool = False
    captures: tuple[str, ...] = ()


_SEGMENT_START = r"(?:^|[;&|]\s*|\$\(\s*)"
_RULES = (
    _Rule(
        "G-DST-01",
        (re.compile(r"\brm\s+(?:-\w*[rR]\w*\s+)+(?:--no-preserve-root\s+)?(?:/\*?|~/?|\$HOME/?|/app/\*?)(?=\s|[;&|\\]|$)", _FLAGS),),
        "BLOCKED [{rule_id}]: this command could destroy the environment and was not run. Delete or modify only the specific files the task requires.",
    ),
    _Rule(
        "G-DST-02",
        tuple(re.compile(pattern, _FLAGS) for pattern in (
            r"\bmkfs(?:\.\w+)?\b",
            r"\bdd\b[^;&|]*\bof=/dev/",
            r"\bwipefs\b",
            r">\s*/dev/[sh]d[a-z]",
        )),
        "BLOCKED [{rule_id}]: this command could destroy the environment and was not run. Delete or modify only the specific files the task requires.",
    ),
    _Rule(
        "G-DST-03",
        tuple(re.compile(pattern, _FLAGS) for pattern in (
            r":\(\)\s*\{\s*:\s*(?:\|\s*:\s*&|&\s*:\s*)\s*\}",
            r"\bkill\s+-9\s+-1\b",
            r"\bpkill\s+-9\s+-u\b",
        )),
        "BLOCKED [{rule_id}]: this command could destroy the environment and was not run. Delete or modify only the specific files the task requires.",
    ),
    _Rule(
        "G-DST-04",
        tuple(re.compile(pattern, _FLAGS) for pattern in (
            r"\b(?:shutdown|reboot|halt|poweroff)\b",
            r"\bsystemctl\s+(?:poweroff|reboot|halt)\b",
            r"\binit\s+[06]\b",
        )),
        "BLOCKED [{rule_id}]: this command could destroy the environment and was not run. Delete or modify only the specific files the task requires.",
    ),
    _Rule(
        "G-DST-05",
        (re.compile(r"\bch(?:mod|own)\s+-R\s+\S+\s+/(?=\s|$)", _FLAGS),),
        "BLOCKED [{rule_id}]: this command could destroy the environment and was not run. Delete or modify only the specific files the task requires.",
    ),
    _Rule(
        "G-INT-01",
        tuple(re.compile(pattern, _FLAGS) for pattern in (
            r"(?<![\w.])/(?:tests|solution|oracle)(?=/|\s|$|['\"])",
            r"/logs/verifier\b",
            r"\btest_outputs\.py\b",
            r"\bsolve\.sh\b",
        )),
        "BLOCKED [G-INT-01]: paths reserved for the benchmark's grader are not part of the task. Work only from the task's inputs.",
    ),
    _Rule(
        "G-SEC-01",
        tuple(re.compile(pattern, re.MULTILINE) for pattern in (
            _SEGMENT_START + r"(?:printenv|env)\s*(?=$|[;&|])",
            r"/proc/\d+/environ",
            r"\$\{?\w*(?:API_KEY|TOKEN|SECRET)\}?",
        )),
        "",
        action="log",
    ),
    _Rule(
        "U-INT-01",
        (re.compile(_SEGMENT_START + r"(?:sudo\s+)?(?P<program>vi|vim|nvim|nano|emacs|pico|less|more|top|htop|man|watch)\b", _FLAGS),),
        "BLOCKED [{rule_id}]: '{program}' is interactive and would hang. Read with cat/head/sed -n, edit with sed, python, or cat <<'EOF' > file.",
        c2_only=True,
        captures=("program",),
    ),
    _Rule(
        "U-INT-02",
        tuple(re.compile(pattern, _FLAGS) for pattern in (
            r"\btail\s+(?:-\w*f\w*|--follow)\b",
            r"\bjournalctl\b[^;&|]*\s-f\b",
        )),
        "BLOCKED [U-INT-02]: follow mode never exits. Use 'tail -n 50 FILE' and run it again to poll.",
        c2_only=True,
    ),
    _Rule(
        "U-INT-03",
        (re.compile(_SEGMENT_START + r"(?P<program>python3?|ipython|node|irb|sqlite3|psql|mysql)\s*(?=$|[;&|])", _FLAGS),),
        "BLOCKED [U-INT-03]: a bare '{program}' waits for input. Use '{program} -c \"...\"', '{program} script', or pipe input in.",
        c2_only=True,
        captures=("program",),
    ),
    _Rule(
        "U-INT-04",
        tuple(re.compile(pattern, _FLAGS) for pattern in (
            r"\bsudo\b(?!\s+-n\b)",
            r"\b(?:ssh|scp)\b(?![^;&|]*BatchMode=yes)",
        )),
        "BLOCKED [U-INT-04]: this would wait for a password. Use 'sudo -n …' (fails fast without rights) or '-o BatchMode=yes'.",
        c2_only=True,
    ),
    _Rule(
        "U-FMT-01",
        (re.compile(r"^\s*$", re.MULTILINE),),
        "REJECTED [U-FMT-01]: empty command. Send one bash command.",
        c2_only=True,
    ),
    _Rule(
        "U-FMT-02",
        (),
        "REJECTED [U-FMT-02]: command is {n} characters (limit 8000). Write long content to a file with a heredoc across several steps.",
        c2_only=True,
    ),
    _Rule(
        "U-FMT-03",
        (),
        "REJECTED [U-FMT-03]: heredoc '{delim}' is never closed. End it with a line containing only {delim}.",
        c2_only=True,
    ),
    _Rule(
        "U-FMT-04",
        (),
        "REJECTED [U-FMT-04]: submit on its own: echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT",
        c2_only=True,
    ),
)

_HEREDOC_START = re.compile(r"<<(-?)[ \t]*(['\"]?)(\w+)\2")
_SUBMIT = "COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT"


def strip_heredoc_bodies(command: str) -> str:
    """Remove heredoc bodies while retaining shell command lines."""
    lines = command.splitlines(keepends=True)
    kept: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        kept.append(line)
        delimiters = [
            (match.group(3), match.group(1) == "-")
            for match in _HEREDOC_START.finditer(line)
        ]
        index += 1
        for delimiter, strip_tabs in delimiters:
            while index < len(lines):
                body_line = lines[index]
                index += 1
                terminator = body_line.rstrip("\r\n")
                if strip_tabs and terminator.startswith("\t"):
                    terminator = terminator.lstrip("\t")
                if terminator == delimiter:
                    break
    return "".join(kept)


def _unterminated_heredoc(command: str) -> str | None:
    lines = command.splitlines()
    for index, line in enumerate(lines):
        matches = list(_HEREDOC_START.finditer(line))
        for match in matches:
            delimiter = match.group(3)
            closed = False
            for body_line in lines[index + 1 :]:
                candidate = body_line.lstrip("\t") if match.group(1) else body_line
                if candidate == delimiter:
                    closed = True
                    break
            if not closed:
                return delimiter
    return None


def check_extra_tool_calls(tool_call_count: int) -> GuardrailResult | None:
    """Return the documented note when calls beyond the first are ignored."""
    if tool_call_count < 0:
        raise ValueError("tool_call_count cannot be negative")
    extra_count = tool_call_count - 1
    if extra_count <= 0:
        return None
    return GuardrailResult(
        "U-FMT-05",
        "note",
        f"NOTE: {extra_count} extra tool call(s) were ignored; send one command per response.",
    )


def check_command(command: str, *, c2_enabled: bool = False) -> GuardrailResult:
    """Return the first matching rule; G rules always precede C2 rules."""
    for rule in _RULES:
        if rule.c2_only and not c2_enabled:
            continue
        candidate = command if not rule.c2_only else strip_heredoc_bodies(command)
        if rule.rule_id == "U-FMT-01" and not candidate.strip():
            values: dict[str, str | int] = {}
        elif rule.rule_id == "U-FMT-02" and len(command) > 8000:
            values = {"n": len(command)}
        elif rule.rule_id == "U-FMT-03":
            delimiter = _unterminated_heredoc(command)
            if delimiter is None:
                continue
            values = {"delim": delimiter}
        elif rule.rule_id == "U-FMT-04" and _SUBMIT in command:
            if command.strip() == f"echo {_SUBMIT}":
                continue
            values = {}
        elif rule.rule_id in {"U-FMT-01", "U-FMT-02", "U-FMT-04"}:
            continue
        else:
            match = next(
                (found for pattern in rule.patterns if (found := pattern.search(candidate))),
                None,
            )
            if match is None:
                continue
            values = {name: match.group(name) for name in rule.captures}
        message = rule.message.format(rule_id=rule.rule_id, **values) if rule.message else None
        return GuardrailResult(rule.rule_id, rule.action, message)
    return GuardrailResult(None, "allow")
