# Harness bug review (harness-v1, eval pass 1)

Roshan, 2026-10-27. This is a report only: no frozen file was changed. **Update:** all nine fixes are applied on branch `bug-fixes` as harness-v1.1, pending Rohit's approval; see `docs/bug_fixes.md` (BF-01 to BF-09). Each suspected bug from the code review was checked against the real code in `tests/test_known_issues.py`. Each one is an `xfail(strict=True)` test that asserts the *correct* behaviour, so it is reported as xfailed today and starts failing once the bug is fixed. Next to them are control tests that must keep passing after any fix. Evidence comes from `results/eval/rohit-eval-pass1` (200 scored trials).

Every proposed diff below was applied to a scratch copy of the repository, never to the frozen files. Results on that copy:
- All 21 xfail tests flip to XPASS(strict).
- All other 199 tests still pass, including the existing guardrail, C5 and C2-bypass tests.
- Replaying all 1,498 bash commands from pass 1 through the fixed guardrails removes the 12 U-FMT-03 blocks, keeps both U-FMT-04 blocks (which were correct), and adds no new block.

## Summary

| # | Suspicion | Verdict | Changed a pass-1 outcome? |
|---|---|---|---|
| 1 | U-FMT-03 blocks valid heredocs, strings and `<<` operators | **Confirmed**, wider than suspected (here-strings and `$(( a << b ))` too) | **Yes, plausibly 2–3 trials:** V/071, V-E/015 (V-E/068 recovered) |
| 2 | U-INT-04 matches `.ssh` paths and `ssh-keygen` | **Confirmed** | No: 0 U-INT-04 events |
| 3 | U-INT-03 blocks `cat x.py \| python3` | **Confirmed** | No: 0 U-INT-03 events |
| 4 | C5 marks inputs ✗ and truncates `.code-workspace` | **Confirmed**, plus a third defect: `~/…` paths lose the `~` | Unknown. 35 of 46 ✗ lines in V/V-E were false; both 113 trials still passed |
| 5 | 429 rejections keep a full reservation against B_task; byte estimate binds before step 50 | **First half confirmed**; second half **rejected for pass 1** (by design, never bound) | No: no `CostCapExceeded` in pass 1 |
| 6 | C2 file tools bypass the guardrails, G-INT-01 included | **Confirmed**; the U-rule bypass is intended, the G-INT-01 gap is not | No: no file-tool call touched a grader path |
| 7 | C4 counts expected non-zero exits and blocks forever | **Confirmed** (back-to-back is not required) | Possibly V/073 (3 of 5 V intercepts) |
| 8 | C1 offload overwrites earlier `harness_chars` | **Confirmed** | No (accounting only, 720 chars in 4 observations) |
| 9 | Status line shows `$0.02` for V-E; "40 min" hard-coded | **Confirmed** (cosmetic); "40 min" is right for all 40 eval tasks | No |

Rule events in pass 1 (`guardrail_block` / `guardrail_log` in `agent/events.jsonl`, active trials only; B0 and E have no rules):

| Rule | H0 | V | V-E |
|---|---|---|---|
| U-FMT-03 block | 0 | 5 (task 071) | 7 (015 ×6, 068 ×1) |
| U-FMT-04 block | 0 | 0 | 2 (040, 074) |
| U-INT-05 log | 0 | 0 | 2 (039, 080) |
| All other rules | 0 | 0 | 0 |

No trial reached 10 blocks, so `GuardrailLimit` never fired (maximum 6, V-E/015).

---

## 1. U-FMT-03 rejects valid commands as "unterminated heredoc"

**Symptom.** `_unterminated_heredoc` runs `<<(-?)\s*['"]?(\w+)` over *every* line: heredoc bodies, quoted strings, here-strings and arithmetic included. A matching closer must be a line equal to the delimiter, with nothing else on it. Rejected as a result:
- `print(1 << 3)` or Ruby `items << 1` inside a properly closed heredoc;
- `ruby -e "... f << data }"`;
- `cat <<< hello`;
- `echo $(( 1 << 3 ))`;
- a heredoc nested in `bash -lc "..."`, whose last line is `PY"`.

**Location.** [harness/guardrails.py:188](../harness/guardrails.py#L188) (`_unterminated_heredoc`), [harness/guardrails.py:159](../harness/guardrails.py#L159) (`_HEREDOC_START`), used at [harness/guardrails.py:229](../harness/guardrails.py#L229). `guardrails.md` §3 says U-rules match the command *with heredoc bodies removed*; U-FMT-03 is the one U-rule that doesn't.

**Reproduction.** `test_valid_commands_are_not_rejected_as_unterminated_heredocs` (6 cases); control `test_unterminated_heredoc_control`.

```python
check_command("python3 - <<'PY'\nprint(1 << 3)\nPY", c2_enabled=True).rule_id   # 'U-FMT-03'
check_command("cat <<< hello", c2_enabled=True).rule_id                         # 'U-FMT-03'
```

**Evidence.** All 12 U-FMT-03 blocks in pass 1 are false positives:

| Trial | Blocks | What was blocked | Outcome |
|---|---|---|---|
| V / 071-paste-image-docx | 5 (steps 1–4, 6) | `bash -lc "python3 - <<'PY' … PY"`: the inner script ends in a line that is exactly `PY`; U-FMT-03 saw `PY"` | Reward 0, then 9 format errors in 17 calls → RepeatedFormatError. **H0 solved this task (reward 1.0)** with the same `python3 - <<'PY'` heredoc, not nested |
| V-E / 015-gym-auditorium-sim | 6 (steps 9–12, 20–21) | A closed `<<'RUBY'` heredoc whose body has `spaces_to_keep << space` (blocked as heredoc `space`); then `openstudio -e "…{\|f\| f << idf.to_s }"` (heredoc `idf`) | Reward 0, required outputs never written (`Missing required file`) |
| V-E / 068-strike-first-two-lines | 1 (step 10) | `bash -c "python3 - <<'PY' … PY"` | Recovered next step by writing the script to a file; reward 0, verifier silent |

**Impact.**
- U-FMT-03 is the only rule that changed outcomes in pass 1. It plausibly cost V one task (071) and V-E one task (015); 068 recovered.
- On mean reward that is at most +0.025 for V and +0.025–0.05 for V-E.
- The bias runs against our harness: V − B0 and V-E − B0 are, if anything, understated.

**Proposed fix (not applied).** Scan shell lines only and skip each body once its closer is found. Ignore single-line quoted strings, `<<<`, and unquoted delimiters that don't start like a word, and accept a closer followed by the closing quote of an enclosing `bash -c "…"`.

```diff
--- a/harness/guardrails.py
+++ b/harness/guardrails.py
-_HEREDOC_START = re.compile(r"<<(-?)[ \t]*(['\"]?)(\w+)\2")
+# Not a here-string (<<<); an unquoted delimiter must start like a word, so arithmetic
+# shifts such as $(( 1 << 3 )) are not heredocs.
+_HEREDOC_START = re.compile(r"(?<!<)<<(?!<)(-?)[ \t]*(?:(['\"])(\w+)\2|([A-Za-z_]\w*))")
+# Quoted strings on one line (other than a quoted heredoc delimiter) are data, not shell syntax.
+_QUOTED = re.compile(r"(<<-?[ \t]*(['\"])\w+\2)|'[^'\n]*'|\"(?:\\.|[^\"\\\n])*\"")
@@ def strip_heredoc_bodies(command: str) -> str:
-            (match.group(3), match.group(1) == "-")
+            (match.group(3) or match.group(4), match.group(1) == "-")
@@
 def _unterminated_heredoc(command: str) -> str | None:
+    """Scan shell lines only: skip each heredoc's body once its delimiter line is found."""
     lines = command.splitlines()
-    for index, line in enumerate(lines):
-        matches = list(_HEREDOC_START.finditer(line))
-        for match in matches:
-            delimiter = match.group(3)
-            closed = False
-            for body_line in lines[index + 1 :]:
-                candidate = body_line.lstrip("\t") if match.group(1) else body_line
-                if candidate == delimiter:
-                    closed = True
+    index = 0
+    while index < len(lines):
+        shell = _QUOTED.sub(lambda match: match.group(1) or "''", lines[index])
+        index += 1
+        for match in _HEREDOC_START.finditer(shell):
+            delimiter = match.group(3) or match.group(4)
+            while index < len(lines):
+                candidate = lines[index].lstrip("\t") if match.group(1) else lines[index]
+                index += 1
+                # Nested in bash -c "...", the delimiter line also carries the closing quote.
+                if candidate.rstrip("\"')") == delimiter:
                     break
-            if not closed:
+            else:
                 return delimiter
     return None
```

Known limit of the fix: `$(( x << y ))` with a *word* operand is still flagged, and a heredoc inside a multi-line quoted string is no longer checked (bash runs it anyway).

---

## 2. U-INT-04 matches `.ssh` paths and `ssh-*` tools

**Symptom.** `\b(?:ssh|scp)\b` matches wherever `ssh` is a word, including `ls ~/.ssh`, `cat /home/user/.ssh/config` and `ssh-keygen -N '' …`. None of these waits for a password.

**Location.** [harness/guardrails.py:119](../harness/guardrails.py#L119).

**Reproduction.** `test_ssh_paths_and_tools_are_not_password_prompts` (3 cases); control `test_ssh_control` (`ssh user@host` and `scp f host:` stay blocked, `-o BatchMode=yes` passes).

**Evidence.** 0 U-INT-04 events in pass 1. Task 106's U-INT-04 false positive (`sudo`) was fixed before eval (§7.1); this is a second one in the same rule.

**Impact.** None observed; a latent false positive for SSH-key tasks.

**Proposed fix.**

```diff
-        (re.compile(r"\b(?:ssh|scp)\b(?![^;&|]*BatchMode=yes)", _FLAGS),),
+        (re.compile(r"(?<![\w.-])(?:ssh|scp)(?![\w./-])(?![^;&|]*BatchMode=yes)", _FLAGS),),
```

---

## 3. U-INT-03 blocks the piped input its own message recommends

**Symptom.** The rule's segment start includes a single `|`, so `cat script.py | python3` and `echo 'print(1)' | python3` are blocked. Yet the message says *"Use 'python3 -c "..."', 'python3 script', or pipe input in."* An interpreter reading a pipe gets EOF and exits; it never waits.

**Location.** [harness/guardrails.py:112](../harness/guardrails.py#L112), using `_SEGMENT_START` at [harness/guardrails.py:35](../harness/guardrails.py#L35). The pattern matches `guardrails.md` §3.2, so the doc and the code agree with each other but not with the message.

**Reproduction.** `test_piped_interpreter_is_allowed` (2 cases); control `test_bare_interpreter_control` (`python3`, `cd /app && python3` stay blocked).

**Evidence.** 0 U-INT-03 events in pass 1.

**Impact.** None observed.

**Proposed fix.** Keep `_SEGMENT_START` for U-INT-01 (`… | less` must stay blocked) and give U-INT-03 a start that excludes a single pipe. `guardrails.md` §3.2 would need the same edit.

```diff
 _SEGMENT_START = r"(?:^|[;&|]\s*|\$\(\s*)"
+# Like _SEGMENT_START but not after a single pipe: an interpreter reading a pipe never waits.
+_COMMAND_START = r"(?:^|(?:;|&&?|\|\|)\s*|\$\(\s*)"
@@ "U-INT-03"
-        (re.compile(_SEGMENT_START + r"(?P<program>python3?|ipython|node|irb|sqlite3|psql|mysql)\s*(?=$|[;&|])", _FLAGS),),
+        (re.compile(_COMMAND_START + r"(?P<program>python3?|ipython|node|irb|sqlite3|psql|mysql)\s*(?=$|[;&|])", _FLAGS),),
```

---

## 4. C5 path checks: inputs reported missing, extensions truncated, `~` dropped

**Symptom.** C5 has three separate defects. All three produce ✗ lines that tell the model a file is *"missing, empty, or not written during this trial"* when it isn't:
1. **Inputs.** Every absolute path in the instruction is checked with `test -s && mtime >= trial start`. An input file exists but is older than the trial, so it gets ✗. That invites the model to overwrite its inputs.
2. **Hyphenated extensions.** The extension is `[A-Za-z0-9]{1,12}`, so `/app/project.code-workspace` becomes `/app/project.code`, which never exists.
3. **Home-relative paths.** The bare-path lookbehind lets `~` precede `/`, so `~/Desktop/interstellar.png` is checked as `/Desktop/interstellar.png`.

**Location.** [harness/components/submit_gate.py:9](../harness/components/submit_gate.py#L9) (`_PATH`), [harness/components/submit_gate.py:58](../harness/components/submit_gate.py#L58) (the single combined check), [harness/components/submit_gate.py:66](../harness/components/submit_gate.py#L66) (the message).

**Reproduction.**
- `test_hyphenated_extension_is_kept` and `test_home_relative_path_is_not_turned_into_a_root_path`.
- `test_gate_does_not_call_an_existing_input_missing` runs the gate's real shell commands against real files with real mtimes.
- Control: `test_extract_paths_control` (spaces in backticks, `.tar.gz`).

```python
extract_paths("Save the workspace as `/app/project.code-workspace`.")  # ['/app/project.code']
extract_paths("Save the image to ~/Desktop/out.png.")                  # ['/Desktop/out.png']
```

**Evidence.** C5 fired 50 times in V/V-E (18 and 32 `submit_gate` events), and 31 of those checklists had at least one ✗. Of the 46 ✗ lines:

| Cause | ✗ lines | Examples |
|---|---|---|
| Input file under `/input/` | 20 | `/app/input/building.osm`, `/app/input/images/*.tif` |
| Other input named in the instruction (judged by reading the instruction) | 7 | `/app/shi17a.pdf` ×2, `/app/tilearray.png` ×2, `/home/user/Desktop/src.mp4`, `/app/OSP_Envelope_Price-List_2023_5000.xlsx`, `/app/dog_with_background.png` |
| `~` dropped | 6 | `/.config/Code/User/keybindings.json` (115), `/Desktop/interstellar.png` (112), `/Desktop/flipped_…mp4` (110) |
| Extension truncated | 2 | `/app/project.code` (113, V and V-E) |
| Plausibly real (output not yet written) | 11 | V-E/015's five EnergyPlus outputs, `/home/user/Desktop/image.docx` (V-E/071), … |

So **35 of 46 ✗ lines (76 %) were false.** Both 113 trials still passed (reward 1.0). The checklist's effect on the other trials can't be isolated without an ablation; H0+C5 (pass 2) will show it.

**Impact.**
- C5's signal is mostly noise on tasks that name input files, which is most Scientific tasks.
- This weakens the C5 ablation rather than biasing V against B0: the model can ignore a ✗ and resubmit.

**Proposed fix.** One exec per path, as before. The exit code now separates missing (1) from exists-but-unchanged (2), and an unchanged file is reported neutrally. The extension allows inner hyphens and `~/…` is skipped. Expanding `~` instead would need `$HOME` in the exec environment, and `SAFE_ENV` does not pass it. The existing `test_c5_first_submission_checks_paths_and_emits_checklist` passes unchanged.

```diff
--- a/harness/components/submit_gate.py
+++ b/harness/components/submit_gate.py
 _PATH = re.compile(
-    r"`(?P<quoted>/[^`\n]*\.[A-Za-z0-9]{1,12})`|"
-    r"(?P<bare>(?<![\w:/])/(?:[A-Za-z0-9._+-]+/)*[A-Za-z0-9._+-]+\.[A-Za-z0-9]{1,12}(?![\w]))"
+    r"`(?P<quoted>/[^`\n]*\.[A-Za-z0-9][A-Za-z0-9-]{0,23})`|"
+    # ~/... is skipped: the check runs without the agent's $HOME, so it would always say missing.
+    r"(?P<bare>(?<![\w:/~])/(?:[A-Za-z0-9._+-]+/)*[A-Za-z0-9._+-]+\.[A-Za-z0-9][A-Za-z0-9-]{0,23}(?![\w-]))"
 )
@@ class SubmissionGate(Hook):
-        checks: list[tuple[str, bool]] = []
+        checks: list[tuple[str, bool, bool]] = []
         for path in paths:
             quoted = shlex.quote(path)
+            # rc 0: written during the trial; 1: missing or empty; 2: exists but unchanged.
             command = (
-                f"test -s {quoted} && {_MTIME_CHECK} {quoted} "
-                f"{self.trial_started_at:.6f}"
+                f"test -s {quoted} || exit 1; {_MTIME_CHECK} {quoted} "
+                f"{self.trial_started_at:.6f} || exit 2"
             )
-            result = self.environment.execute({"command": command})
-            checks.append((path, result.get("returncode") == 0))
+            returncode = self.environment.execute({"command": command}).get("returncode")
+            checks.append((path, returncode in (0, 2), returncode == 0))
 
         lines = [
-            f"{'✓' if exists else '✗'} {path} "
-            f"({'exists, non-empty, and written during this trial' if exists else 'missing, empty, or not written during this trial'})"
-            for path, exists in checks
+            f"✓ {path} (exists, non-empty, and written during this trial)" if fresh
+            else f"• {path} (exists but unchanged since the trial started; fine if it is an input)" if exists
+            else f"✗ {path} (missing or empty)"
+            for path, exists, fresh in checks
         ]
```

---

## 5. Gateway: unbilled 429 rejections consume B_task

**Symptom.** Before each attempt the gateway reserves the worst case:
- the request size in **bytes** priced as input tokens, plus 4,096;
- plus the **full `max_tokens` = 8,192** at the completion price.

On any exception it adds that whole reservation to `unknown_reserved`, which counts against B_task until the trial ends. That includes HTTP 429, which the provider rejects before generating anything and does not bill. The job ledger's reservation for the failed attempt is never settled either, so the same phantom amount also sits on the job-wide cap.

**Location.**
- [harness/gateway.py:204](../harness/gateway.py#L204) (`unknown_reserved += reserve`)
- [harness/gateway.py:66](../harness/gateway.py#L66) (`request_reserve`)
- [harness/gateway.py:160](../harness/gateway.py#L160) (the cap check)
- [harness/gateway.py:166](../harness/gateway.py#L166) (ledger reservation with no settle on failure)

**Reproduction.** `test_rate_limited_attempts_do_not_exhaust_the_task_budget` runs two steps whose 4 attempts are all 429s (8 attempts, $0 billed) on a ~40 KB prompt; the next step raises `CostCapExceeded` instead of calling the API. The control `test_server_error_keeps_its_reservation_control` shows one reservation is $0.0015 ($0.000794 input + $0.000737 output), about 1/6 of V's $0.01. So **about 6 throttled attempts end a V trial with `CostCapExceeded`**, or about 8 for V-E ($0.002 each against $0.0167).

**Evidence.** All 12 failed attempts in active pass-1 trials (H0 3, V 2, V-E 7) are HTTP 429 with no reported cost.
- **V-E/039** lost 3 attempts to 429s at steps 18–19, about $0.006 of phantom reservation (37 % of its B_task). It was not capped: it ran 45 model calls on $0.0063 of real spend and ended on RepeatedFormatError.
- **Archived V-E/077** (rerun as an infrastructure error) had 8 rejected attempts. They held about $0.011 of phantom reservation against $0.0016 of real spend, roughly 77 % of B_task, before the retries ran out.
- No pass-1 trial ended with `CostCapExceeded`.

**Second half, rejected for pass 1.** "The byte estimate makes the dollar cap bind before step 50" is how the design is meant to work: architecture §6 says the cap *"can end a trial a few steps before step 50"*. The reservation only matters for the next call, so the cap binds once real spend passes about B_task − $0.0016. In pass 1:
- the highest V spend was $0.0066 (V/076, 47 steps);
- V/088 reached step 50 at $0.0062 and ended on the **step** cap (`LimitsExceeded`, the only `cap_reached` event);
- no trial got within $0.0018 of its dollar cap.

**Impact.** None in pass 1. Under heavy Darkbloom throttling (up to 14 of 36 calls in one smoke trial) the risk is real: such trials would end as `CostCapExceeded`, which the classifier and the report read as a harness-level budget failure, when the cause is the provider.

**Proposed fix.** Release a 429's reservation, both per task and in the job ledger. Keep reserving for other failures, which may have been billed. `usage_complete` stays `False`, so the cost report still flags the call.

```diff
--- a/harness/gateway.py
+++ b/harness/gateway.py
-                # A failed attempt may have been billed; do not invent zero usage.
+                # A failed attempt may have been billed; do not invent zero usage. A 429 is
+                # rejected before generation and not billed, so it releases its reservation.
                 self.usage_complete = False
-                self.unknown_reserved += reserve
+                if status == 429:
+                    if self.job_ledger:
+                        self.job_ledger.settle(reservation, 0)
+                else:
+                    self.unknown_reserved += reserve
```

This changes nothing the model sees (the status line shows real spend only), so it can't change a trial unless the cap would have fired.

---

## 6. C2 file tools bypass every guardrail, G-INT-01 included

**Symptom.** `HarnessAgent.before_execute` only calls the guardrail when `tool == "bash"`. As a result, `read_file`, `search`, `write_file` and `edit_file` with `path="/tests/test_outputs.py"` run without the always-on G-INT-01 grader-path check. Skipping the *U-rules* for file tools is intended and tested (`test_c2_function_tool_bypasses_command_guardrail_and_executes_plugin`): a file path is not a shell command. Skipping the *G-rules* is not intended.

**Location.** [harness/loop.py:83](../harness/loop.py#L83).

**Reproduction.** `test_file_tool_cannot_read_grader_paths`; control `test_bash_grader_path_control` (`cat /tests/test_outputs.py` is blocked).

**Evidence.**
- C2 file tools were used 82 times in pass 1: V-E 60 (24 `read_file`, 19 `write_file`, 14 `search`, 3 `edit_file`), V 22.
- None touched `/tests`, `/solution`, `/oracle`, `test_outputs.py`, `solve.sh` or `/logs/verifier`.
- Harbor uploads `tests/` only after the agent finishes (guardrails.md §6), so the path wouldn't exist during the trial anyway.

**Impact.** None observed; a gap in a defence-in-depth control that `guardrails.md` §3.1 says applies to every host configuration.

**Proposed fix.** Pass the file tool's `path` through the G rules only (C2 off), before the existing bash branch. The existing bypass test still passes. A blocked file-tool call doesn't count toward the 10-block limit in this sketch.

```diff
--- a/harness/loop.py
+++ b/harness/loop.py
+from harness.guardrails import check_command
@@
     def before_execute(self, action, state):
+        if action.get("tool", "bash") != "bash":
+            # File tools have no command; their path still goes through the always-on G rules.
+            path = str((action.get("arguments") or {}).get("path", ""))
+            result = check_command(path, c2_enabled=False)
+            if result.blocked:
+                self.events.write(type="guardrail_block", step=state.step,
+                                  rule_id=result.rule_id, command=path[:500])
+                return Decision(False, result.message or "", result.rule_id, "guardrail_block")
         if action.get("tool", "bash") == "bash":
```

---

## 7. C4 blocks a repeated probe forever, even after the state changed

**Symptom.** C4 counts every non-zero exit per command hash for the whole trial and refuses the command on its third run. It doesn't matter what ran in between. Expected non-zero exits therefore count as failures:
- `grep` with no match;
- `test -f` while polling for a file;
- `pkill` with nothing to kill.

A polling probe or retry becomes permanently unavailable even after another command fixed the state.

**Location.** [harness/components/recovery.py:82](../harness/components/recovery.py#L82) (count), [harness/components/recovery.py:50](../harness/components/recovery.py#L50) (block on ≥ 2).

**Reproduction.** `test_probe_runs_again_after_a_state_change` (`test -f` / `touch`, `grep -q` / `echo >>`, `pkill` / start). Control `test_repeat_intercept_control`: an identical failing command run back-to-back is still intercepted.

**Evidence.** 6 `repeat_intercept` events (V 5, V-E 1):
- **V/073-force-quit-frozen-doc** accounts for 3 of them. `pkill -f soffice` returned **143** each time. Its pattern also matches the agent's own `bash -c "pkill -f soffice"` shell, so the command most likely killed soffice *and* itself with SIGTERM. C4 counted that as a failure and blocked the identical command at steps 6, 16 and 19, even after other commands, including `which pkill` (rc 0), ran in between. The trial ended reward 0 via RepeatedFormatError.
- V/039 and V/040 (`xdg-open …`) and V-E/111 (`gsettings set …`) were real repeated failures, where the intercept did its job.

**Impact.** Plausibly contributed to V/073's failure; otherwise small.

**Proposed fix.** Count back-to-back failures only. The design targets blind retries; a command in between may have changed the state.

```diff
--- a/harness/components/recovery.py
+++ b/harness/components/recovery.py
-                self.failures[digest] = self.failures.get(digest, 0) + 1
+                # Count back-to-back failures only: a command in between may have changed the
+                # state (file created, process started), so a later retry is not blind.
+                self.failures = {digest: self.failures.get(digest, 0) + 1}
                 output = str(result.get("output", ""))
                 exception = str(result.get("exception_info", ""))
                 self.last_errors[digest] = (output + ("\n" + exception if exception else ""))[-1000:]
+            elif extra.get("origin") != "harness":
+                self.failures = {}
```

**Related observation (not a C4 bug, no test).** `harness/environment.py:110` labels every rc 124/137 as a timeout: it emits `command_timeout` and C4 appends the timeout recipe. V/073's two `pkill -f soffice -9` calls returned 137 because they killed their own shell, not because they timed out. So 2 of V's 6 `command_timeout` events are self-kills. Telling them apart needs the command's duration.

---

## 8. C1 offload drops `harness_chars` added earlier by C2/C4

**Symptom.** Hooks run before C1 (`loop.py` `after_execute`: hooks, then offload, then the budget line). C4's timeout recipe and stall nudge add to `extra.harness_chars`. Offload then *replaces* `harness_chars` with the stub length, so those characters are counted as environment output instead of harness overhead.

**Location.** [harness/components/context.py:41](../harness/components/context.py#L41).

**Reproduction.** `test_offload_keeps_earlier_harness_chars` (189 C4 characters lost).

**Evidence.**
- 75 offloaded observations in V/V-E. In 4 of them, C4 text was part of the offloaded output (V-E/011, 037, 041: 189-char timeout recipe; V/089: 153-char stall nudge).
- 720 characters in total were misattributed from harness to env. Each is re-sent with every later prompt, so the token effect is a few thousand tokens across the whole pass.

**Impact.** The harness-overhead estimate (17 % of V's known cost, 16 % of V-E's) is slightly low. Accounting only; no outcome changes.

**Proposed fix.**

```diff
-                "harness_chars": len(stub),
+                "harness_chars": int(output.get("extra", {}).get("harness_chars", 0)) + len(stub),
```

This can also be corrected offline without a rerun: add the C4 text found in `extra.full_output` back to the harness share.

---

## 9. C3 status line: `$0.02` for V-E, hard-coded "40 min"

**Symptom.** `${budget_usd:.2f}` rounds V-E's $0.0167 to `$0.02` (928 status lines in V-E). The model is told it has 20 % more budget than it does. The wall-clock limit is the literal `40`.

**Location.** [harness/components/budget.py:70](../harness/components/budget.py#L70).

**Reproduction.** `test_status_line_shows_the_exact_budget`; control `test_status_line_control` (`$0.01` still prints as `$0.01`).

**Evidence.** All 40 eval tasks have `agent_timeout_sec = 2400` (`configs/task_subset.json`), so "40 min" is correct for this subset. That part is a latent issue only.

**Impact.** Cosmetic. The cap itself is enforced on the exact value.

**Proposed fix.** `:g` prints `0.0167` and `0.01`. Leave "40 min" unless a task with a different timeout is added.

```diff
-...| ${state.spent_usd:.8f}/${self.config.budget_usd:.2f} | context ...
+...| ${state.spent_usd:.8f}/${self.config.budget_usd:g} | context ...
```

---

## Recommendation for Rohit

**What would need a V/V-E rerun.** The rule table and component behaviour are frozen with `harness-v1`. Any fix that changes what the model sees or what runs would make pass-1 V/V-E results incomparable with new runs. That covers #1, #2, #3, #4, #6, #7 and #9 (the status line text is part of every billed prompt). Those fixes would need a `harness-v1.1` tag, a rerun of V and V-E, and a rerun of whichever ablations contain the component: H0+C2 for #1–#3, H0+C4 for #7, H0+C5 for #4. Only **#1** has an observed effect on outcomes (V/071, V-E/015), so it is the only one worth a rerun, and only if there is time.

**Safe without a rerun.**
- **#8** can be corrected offline in the analysis.
- **#5** doesn't change any model-visible text, and no pass-1 trial came near the cap. Fixing it before passes 2–3 can't change a pass-1 number, but it is still a code change after the freeze and should be logged as a freeze exception like the other four.

**No-rerun alternative (recommended given the deadline).** Keep `harness-v1` and report the findings as harness-level failures and threats to validity:
1. In the failure classification, label V/071 and V-E/015 as harness-level `guardrail_blocked` (false positive). V-E/068 recovered from its block and failed later. V-E/040 and V-E/074 were correct U-FMT-04 blocks that didn't cause the failure. `classify_failures.py` already flags all five for manual review.
2. State the upper bound: had U-FMT-03 not misfired, V's mean reward would be at most +0.025 higher and V-E's at most +0.05. That only strengthens V − B0 (+0.075) and V-E − B0 (+0.170).
3. In the guardrails section (`guardrails.md` §7 eval-phase review):
   - report the rule counts table above;
   - record U-FMT-03 as a rule that the dev review missed (dev tasks never produced a nested or Ruby heredoc);
   - note #2 and #3 as latent false positives.
4. In the C5 discussion, report that 35 of 46 ✗ lines were false (inputs, `~`, `.code-workspace`). That caveats whatever H0+C5 shows in pass 2.
5. Note the 429 reservation risk (#5) next to the rate-limit discussion, and the self-kill/timeout mislabel next to the `command_timeout` counts.
