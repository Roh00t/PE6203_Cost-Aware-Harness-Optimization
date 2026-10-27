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


_SEGMENT_START = r"(?:^\s*|[;&|]\s*|\$\(\s*)"
# Like _SEGMENT_START but not after a single pipe: an interpreter reading a pipe never waits.
_COMMAND_START = r"(?:^\s*|(?:;|&&?|\|\|)\s*|\$\(\s*)"
_RULES = (
    _Rule(
        "G-DST-01",
        # Any flag order or long form, as long as one flag is recursive; optional `--` and quotes.
        (re.compile(
            r"\brm\b(?=[^;&|\n]*\s(?:-[A-Za-z]*[rR][A-Za-z]*|--recursive)(?=\s))"
            r"[^;&|\n]*\s[\"']?(?:/|~|\$HOME|\$\{HOME\}|/app)/?\*?[\"']?(?=\s|[;&|\\)]|$)",
            _FLAGS,
        ),),
        "BLOCKED [{rule_id}]: this command could destroy the environment and was not run. Delete or modify only the specific files the task requires.",
    ),
    _Rule(
        "G-DST-02",
        tuple(re.compile(pattern, _FLAGS) for pattern in (
            r"\bmkfs(?:\.\w+)?\b",
            r"\bdd\b[^;&|]*\bof=/dev/(?!(?:null|zero|stdout|stderr)\b|fd/)",
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
            # Only in command position: `logging.shutdown()` or "a reboot is required" is not one.
            _SEGMENT_START + r"(?:sudo\s+)?(?:\S*/)?(?:shutdown|reboot|halt|poweroff)\b",
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
            r"(?<![\w.~])/(?:tests|solution|oracle)(?=/|\s|$|['\";|&)*])",
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
            # The secret word must end the name or a `_…` part of it: not ${MAX_TOKENS}.
            r"\$\{?\w*(?:API_KEY|TOKEN|SECRET)(?:_\w*)?(?!\w)\}?",
        )),
        "",
        action="log",
    ),
    _Rule(
        "U-INT-01",
        # Not a longer name (watch-files.sh) and not top in batch mode (top -b).
        (re.compile(
            _SEGMENT_START + r"(?:sudo\s+)?(?P<program>vi|vim|nvim|nano|emacs|pico|less|more|htop|man|watch"
            r"|top(?![^;&|\n]*\s-\w*b))(?![\w.-])",
            _FLAGS,
        ),),
        "BLOCKED [{rule_id}]: '{program}' is interactive and would hang. Read with cat/head/sed -n, edit with sed, python, or cat <<'EOF' > file.",
        c2_only=True,
        captures=("program",),
    ),
    _Rule(
        "U-INT-02",
        (),  # checked per segment by _follow_mode, so a `timeout N` prefix can exempt it
        "BLOCKED [U-INT-02]: follow mode never exits. Use 'tail -n 50 FILE' and run it again to poll.",
        c2_only=True,
    ),
    _Rule(
        "U-INT-03",
        (re.compile(_COMMAND_START + r"(?P<program>python3?|ipython|node|irb|sqlite3|psql|mysql)\s*(?=$|[;&|])", _FLAGS),),
        "BLOCKED [U-INT-03]: a bare '{program}' waits for input. Use '{program} -c \"...\"', '{program} script', or pipe input in.",
        c2_only=True,
        captures=("program",),
    ),
    _Rule(
        "U-INT-04",
        # The program itself, not ~/.ssh paths or ssh-keygen.
        (re.compile(r"(?<![\w.-])(?:ssh|scp)(?![\w./-])(?![^;&|]*BatchMode=yes)", _FLAGS),),
        "BLOCKED [U-INT-04]: this would wait for a password. Use '-o BatchMode=yes' so it fails fast instead.",
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
    # Logged, not blocked: task containers grant passwordless sudo, so blocking it rejected
    # correct commands (dev review 2026-10-21, task 106). Last, so it never hides a block.
    _Rule(
        "U-INT-05",
        (re.compile(r"\bsudo\b(?!\s+-n\b)", _FLAGS),),
        "",
        action="log",
        c2_only=True,
    ),
)

# Not a here-string (<<<); an unquoted delimiter must start like a word, so arithmetic
# shifts such as $(( 1 << 3 )) are not heredocs.
_HEREDOC_START = re.compile(r"(?<!<)<<(?!<)(-?)[ \t]*(?:(['\"])(\w+)\2|([A-Za-z_]\w*))")
# Quoted strings on one line (other than a quoted heredoc delimiter) are data, not shell syntax.
_QUOTED = re.compile(r"(<<-?[ \t]*(['\"])\w+\2)|'[^'\n]*'|\"(?:\\.|[^\"\\\n])*\"")
_SUBMIT = "COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT"
# The submission on its own: optional quotes around the sentinel or around a `bash -c` wrapper.
_SUBMIT_ALONE = re.compile(
    r"^\s*(?:bash\s+-l?c\s+)?([\"']?)\s*echo\s+([\"']?)" + _SUBMIT + r"\2\s*\1\s*$"
)
_FOLLOW = (
    re.compile(r"\btail\b.*\s(?:-\w*[fF]\w*|--follow\b)"),
    re.compile(r"\bjournalctl\b.*\s(?:-\w*f\w*|--follow\b)"),
)


def _heredocs(line: str):
    """Heredoc starts on a shell line, ignoring `<<` inside one-line quoted strings."""
    shell = _QUOTED.sub(lambda match: match.group(1) or "''", line)
    for match in _HEREDOC_START.finditer(shell):
        yield match.group(3) or match.group(4), match.group(1) == "-"


def _closes(line: str, delimiter: str, strip_tabs: bool) -> bool:
    candidate = line.rstrip("\r\n")
    if strip_tabs:
        candidate = candidate.lstrip("\t")
    # Nested in bash -c "...", the delimiter line also carries the closing quote.
    return candidate.rstrip("\"')") == delimiter


def strip_heredoc_bodies(command: str) -> str:
    """Remove heredoc bodies while retaining shell command lines."""
    lines = command.splitlines(keepends=True)
    kept: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        kept.append(line)
        index += 1
        for delimiter, strip_tabs in _heredocs(line):
            while index < len(lines):
                index += 1
                if _closes(lines[index - 1], delimiter, strip_tabs):
                    break
    return "".join(kept)


def _unterminated_heredoc(command: str) -> str | None:
    """Scan shell lines only: skip each heredoc's body once its delimiter line is found."""
    lines = command.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        index += 1
        for delimiter, strip_tabs in _heredocs(line):
            while index < len(lines):
                index += 1
                if _closes(lines[index - 1], delimiter, strip_tabs):
                    break
            else:
                return delimiter
    return None


def _follow_mode(command: str) -> bool:
    """tail/journalctl in follow mode, unless the segment is bounded by `timeout N`."""
    for segment in re.split(r"[;&|\n]+", command):
        segment = segment.strip()
        if re.match(r"(?:sudo\s+)?timeout\b", segment):
            continue
        if any(pattern.search(segment) for pattern in _FOLLOW):
            return True
    return False


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
    """Return the first blocking rule (G rules before C2 rules), else the first log rule.

    A log-only match never hides a later block: checking continues after it.
    """
    logged: GuardrailResult | None = None
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
        elif rule.rule_id == "U-FMT-04" and _SUBMIT in candidate:
            if _SUBMIT_ALONE.match(candidate):
                continue
            values = {}
        elif rule.rule_id == "U-INT-02":
            if not _follow_mode(candidate):
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
        if rule.action != "log":
            return GuardrailResult(rule.rule_id, rule.action, message)
        logged = logged or GuardrailResult(rule.rule_id, rule.action, message)
    return logged or GuardrailResult(None, "allow")
