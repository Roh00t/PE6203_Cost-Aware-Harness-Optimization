# Guardrail review: eval phase

Asmitha, 2026-10-27. **Update:** every defect below is fixed on branch `bug-fixes` (harness-v1.1, pending Rohit's approval; `docs/bug_fixes.md`), and `guardrails.md` §7.2 records this review. `guardrails.md` §7.1 promises this review after the eval runs: rule counts per configuration, and a hand check of every block in a failed trial. It covers all 11 configurations in `results/eval/rohit-eval-pass1/`, passes 1–3, and excludes archived infrastructure attempts (`<task>.errored-*`, `<task>.interrupted-*`). Pass 1 was already reviewed in `docs/harness_bug_review.md` (§1–§3). This review adds the ablation passes, a bash-level check of every blocked command, and a check of what each block actually changed.

## 1. Rule counts per configuration

Sources:
- every `guardrail_block` and `guardrail_log` record in `<config>/<task>/<trial>/agent/events.jsonl`;
- for B0 and E, which have no live rules, an offline replay of the always-on rules (see below).

| Config | Blocks | Logs | Detail |
|---|---|---|---|
| B0 | n/a (stock harness, no live rules) | n/a | Offline replay: 0 G-rule matches in 229 commands |
| E | n/a (stock harness, no live rules) | n/a | Offline replay: 0 G-rule matches in 278 commands |
| H0 | **0 blocks** | 0 logs | G-rules only |
| H0+C0 | **0 blocks** | 0 logs | G-rules only |
| H0+C1 | **0 blocks** | 0 logs | G-rules only |
| H0+C2 | 2 | 1 | U-FMT-03 ×1 (039), U-INT-03 ×1 (099); U-INT-05 log ×1 (068) |
| H0+C3 | **0 blocks** | 0 logs | G-rules only |
| H0+C4 | **0 blocks** | 0 logs | G-rules only |
| H0+C5 | **0 blocks** | 0 logs | G-rules only |
| V | 5 | 0 | U-FMT-03 ×5 (071) |
| V-E | 9 | 2 | U-FMT-03 ×7 (015 ×6, 068 ×1), U-FMT-04 ×2 (040, 074); U-INT-05 log ×2 (039, 080) |
| **Pass 1 (B0, E, H0, V, V-E)** | **14** | **2** | |
| **All 11 configurations** | **16** | **3** | |

Per rule, all configurations:

| Rule | Action | Events | Configs |
|---|---|---|---|
| G-DST-01…05, G-INT-01, G-SEC-01 | block / log | **0** | none, live or replayed |
| U-INT-01 (editors, pagers), U-INT-02 (follow mode), U-INT-04 (ssh/scp) | block | **0** | |
| U-INT-03 (bare REPL) | block | 1 | H0+C2 |
| U-INT-05 (`sudo` without `-n`) | log | 3 | H0+C2 ×1, V-E ×2 |
| U-FMT-01 (empty), U-FMT-02 (> 8,000 chars), U-FMT-05 (extra tool calls) | block / note | **0** | |
| U-FMT-03 (unterminated heredoc) | block | 13 | V ×5, V-E ×7, H0+C2 ×1 |
| U-FMT-04 (submit combined with work) | block | 2 | V-E ×2 |

Other facts:
- **GuardrailLimit was never reached.** The most blocks in one trial was 6 (V-E/015), against a limit of 10.
- **The offline G-rule replay** is the "G-SEC-01-style log review of B0/E trajectories" that `guardrails.md` §5 asks for. Every `bash` command in every active trajectory was passed through the real `harness.guardrails.check_command(cmd, c2_enabled=False)`, imported read-only. Result: 3,094 commands across all 11 configurations, 0 matches. In particular, no configuration probed for secrets or touched grader paths.

## 2. Method for "was the blocked command legitimate?"

`events.jsonl` truncates commands to 500 characters, so each blocked command was taken in full from the trajectory: the assistant tool call whose text matches the event. Each one was then run in a scratch directory outside the repo, under `/bin/bash` 3.2, with stubs for everything it would call:
- `python3`, `openstudio` and `zip` were replaced by stubs that only report what they received;
- an inner `bash -lc` became `bash -c`;
- `/tmp/` was redirected into the scratch folder.

**Legitimate** means all three of:
- bash parsed it with no `here-document … delimited by end-of-file` warning;
- each heredoc delivered its full body, up to its real last line;
- the embedded script is valid code (`ast.parse` for Python, `ruby -c` for Ruby).

This tests what the rules claim to test (shell syntax and protocol). It does not test whether the script would have succeeded in the task container; that question is answered from what the trajectory did next.

All 16 blocked commands parsed cleanly, and all 7 Python and 6 Ruby bodies passed the syntax check. The Ruby written by the `printf` in block 9 was checked as the file it produces.

## 3. Every block, reviewed

Steps are model calls, as in `events.jsonl`. Every trial below failed except V-E/074, which scored 0.819, the untouched-input partial score. "Recovered" means the model ran equivalent work later in the trial.

| # | Trial | Step | Rule | Blocked command (start) | Legitimate? | Label | Reason, and what happened next |
|---|---|---|---|---|---|---|---|
| 1–4 | V/071 | 1, 2, 3, 4 | U-FMT-03 | `bash -lc "python3 - <<'PY'` (step 3: `bash -lc "cat <<'PY'`) | Yes | **False positive** | The inner heredoc closes with a line that is exactly `PY`; the rule saw `PY"`. Not recovered in kind. The scripts also read a non-existent `image.png` |
| 5 | V/071 | 6 | U-FMT-03 | `bash -lc "python3 - <<'PY'` (GIMP export, then python-docx) | Yes | **False positive** | Same pattern. At step 7 the model moved the script into a file; it ran and failed with `ModuleNotFoundError: No module named 'docx'` |
| 6–8 | V-E/015 | 9, 10, 11 | U-FMT-03 | `cat > /tmp/filter_and_run.rb <<'RUBY'` | Yes | **False positive** | The heredoc closes correctly; Ruby's `spaces_to_keep << space` inside the body was read as heredoc `space`. Recovered at step 13 with `write_file`; the script then failed with `NameError: uninitialized constant OpenStudio::Runenergyplus` |
| 9 | V-E/015 | 12 | U-FMT-03 | `printf "%s\n" "require 'openstudio'" …` | Yes | **False positive** | Contains no heredoc at all; `<< space` sits inside a double-quoted argument |
| 10–11 | V-E/015 | 20, 21 | U-FMT-03 | `openstudio -e "model = …"` / `openstudio -e 'model = …'` | Yes | **False positive** | `f << idf.to_s` inside a quoted Ruby one-liner was read as heredoc `idf`. Recovered at steps 22–23 with `/tmp/translate.rb` |
| 12 | V-E/068 | 10 | U-FMT-03 | `bash -c "python3 - <<'PY'` | Yes | **False positive** | Same nested-quote pattern as V/071. Recovered at steps 11–12 (`cat > /tmp/strike.py <<'PY'`, then `python3 /tmp/strike.py`) |
| 13 | H0+C2/039 | 14 | U-FMT-03 | `bash -lc "python3 - <<'PY'` | Yes | **False positive** | Same pattern. Recovered at step 15 with `bash -lc "cat <<'PY' > /tmp/test.py` |
| 14 | H0+C2/099 | 12 | U-INT-03 | `echo 'import openpyxl …' \| python3` | Yes | **False positive** | `python3` reading a pipe gets EOF and never waits; the rule's own message recommends "pipe input in". Recovered at step 14 with `python3 -c "…"`. This is the first live occurrence of `docs/harness_bug_review.md` #3, which pass 1 had as latent |
| 15 | V-E/040 | 7 | U-FMT-04 | `bash -c "echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT"` | Yes | **False positive (harmless)** | The command does nothing except submit. The rule demands the exact text `echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT`. The model sent that at step 8 and was accepted. The bug review counts this block as correct; by the "would it run correctly" test it is over-strict but costless |
| 16 | V-E/074 | 4 | U-FMT-04 | `cd /tmp/casestudy && zip -qr '…/case study.docx' * && echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT` | Yes, in bash | **True positive** | This is what the rule is for: submission chained to unverified work. The model ran the `zip` alone at step 5 and resubmitted at step 6. The zip repacked the unedited document, so the score did not change |

**U-INT-05 logs (3).** All three were `sudo apt-get …` (H0+C2/068 step 3, V-E/039 step 23, V-E/080 step 3).
- Each returned `bash: line 1: sudo: command not found` (rc 127) at once.
- No hang and no `command_timeout` followed.
- The log-only rule behaved as intended.
- These eval images do not install `sudo`. The "passwordless sudo" note in `guardrails.md` §3.2 was observed on dev task 106 and does not hold for every image.

## 4. Did a block decide a trial's outcome?

The hand check of the trajectories leads to a narrower answer than "the guardrail caused the failure".

| Trial | Blocks | Verdict on causality | Why |
|---|---|---|---|
| V/071 | 5 | **Contributed, not proven decisive** | The blocks used 5 of 17 calls and the false message sent the model reformatting a correct heredoc. But the blocked scripts read `/home/user/Desktop/image.png`, which did not exist; the real input was `QTdHniCqfJbBLJe3L3nijU-1200-80.xcf` (from H0's `ls`). They also ran under `bash -lc`, where `docx` was missing (step 7). H0, H0+C0 and H0+C3 solved 071; H0+C2 failed it with no block |
| V-E/015 | 6 | **Not decisive** | The model got past both rounds of blocks with `write_file`. The blocked script ran and failed on a non-existent OpenStudio API. The verifier failed on an empty `eplusout.sql` that the model had created itself with `touch` before any work (step 7) |
| V-E/068 | 1 | Not decisive | Recovered next step. The edit failed because python-pptx's `Font` has no `strike` (`AttributeError: 'Font' object has no attribute 'strike'`, step 5) |
| H0+C2/039, H0+C2/099 | 1 each | Not decisive | Recovered within two steps. Both trials ended in `RepeatedFormatError` later |
| V-E/040, V-E/074 | 1 each | Not decisive | Submitted, or redid the work, at the next step |

**Upper bound, unchanged from the bug review.** If every trial with a false-positive block had otherwise been solved, V would gain at most one task (+0.025) and V-E at most two (+0.05). The trajectories support a smaller effect: only V/071 is plausibly affected. Either way, the correction can only *raise* V and V-E, so it does not threaten the headline comparisons (V − B0, V-E − E).

## 5. Conclusion

- **The always-on rules (G-*) and the hang-prevention rules other than U-INT-03 never triggered**, in 3,094 commands across all 11 configurations. They cost nothing measurable. They also caught nothing: the model never attempted a destructive, secret-probing or grader-reading command. Testing the rules directly does show latent defects, including two safety gaps (§6).
- **U-FMT-03 had 13 blocks and 13 false positives.** Its precision in eval was 0. It mishandles two generic patterns:
  - a heredoc nested in `bash -c "…"`, whose closing line carries the closing quote (7 blocks);
  - a `<<` operator inside a heredoc body or a quoted string, such as Ruby's append (6 blocks).

  The dev review (§7.1) missed it because no dev trial produced either pattern.
- **U-INT-03 had 1 block, a false positive**, on piped input that its own message recommends.
- **U-FMT-04 had 2 blocks**: one true positive and one harmless over-strict match.
- **U-INT-05 logged 3 harmless `sudo` calls.**
- **The effect on results is small**: one trial plausibly affected (V/071), at most +0.025 for V. But in a failed trial a false block is a harness-level failure, and the report should say so.
- **The lesson for the method:** a validation rule needs the same false-positive measurement as any other component, on a sample broad enough to contain the patterns the eval set contains (nested shells, Ruby, `<<` operators).

## 6. Latent defects found by testing the rules directly

None of these fired in eval: there were 0 G-rule events, and only the U-rule events in §1. So they change no result. Each was found by calling the real `harness.guardrails.check_command(cmd, c2_enabled=True)` on a hand-written command, and re-run on 2026-10-27. All are in `harness/guardrails.py`. The first three matter most:
- two are safety gaps;
- one is a false positive that applies in every harness configuration, H0 included, so it could break the H0 ≈ B0 parity check.

| Rule | Command | Result | Problem |
|---|---|---|---|
| G-DST-01 | `rm -rf /app` | allow | Misses the task's input root, which §3.1 says the rule catches. `rm -r -f /` and `rm -rf ~/*` are also allowed |
| G-DST-04 | `python3 -c 'import logging; logging.shutdown()'` | block | Matches the bare word anywhere, including in code and plain text (`echo 'A reboot is required' > …` is blocked too). G-rules also scan heredoc bodies |
| G-SEC-01 | `echo ${MAX_TOKENS}; vim out.txt` | log | A log-only rule checked before every U-rule hides any later block, because the first match wins. `$MAX_TOKENS` matches the secret pattern. `echo $HF_TOKEN && echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT` gets past U-FMT-04 the same way |
| G-INT-01 | `ls /tests;` · `ls ~/tests` | allow · block | A false negative when `;` follows the path; a false positive on a `tests` folder under the home directory |
| G-DST-02 | `dd if=/dev/zero of=/dev/null bs=1 count=1` | block | `/dev/null` is not a disk |
| U-INT-01 | `top -b -n 1 \| head` | block | Batch mode does not hang |
| U-INT-02 | `tail -F /var/log/x` · `journalctl --follow` · `timeout 5 tail -f /var/log/x` | allow · allow · block | Misses two follow-mode variants and blocks a bounded one |
| U-FMT-04 | A heredoc that writes the sentinel string into a file | block | Checks the raw command, not the heredoc-stripped one, contrary to §3 ("`U-*` rules match the command with heredoc bodies removed") |

---

## Proposed addition to `guardrails.md` §7

Not applied: `guardrails.md` is frozen with `harness-v1`. For Isha or Rohit to paste in as §7.2, after §7.1.

> ### 7.2 Eval-phase review result (2026-10-27)
>
> Reviewed: every `guardrail_block` and `guardrail_log` event in all 11 configurations of `results/eval/rohit-eval-pass1/` (438 trials; archived infrastructure attempts excluded). Each blocked command was taken in full from its trajectory and run under bash with stub programs, to test whether it was valid. Full tables: [`docs/guardrail_eval_review.md`](docs/guardrail_eval_review.md).
>
> | Rule | Blocks / logs | Legitimate? | Outcome |
> |---|---|---|---|
> | U-FMT-03 | 13 blocks: V 5, V-E 7, H0+C2 1 | **All 13 false positives.** 7 were heredocs nested in `bash -c "…"` (closing line `PY"`), 6 were `<<` inside a closed heredoc body or quoted string (Ruby append) | One trial plausibly affected (V/071, reward 0, also failed for other reasons). In V-E/015, V-E/068 and H0+C2/039 the model got past the block. Reported as harness-level `guardrail_blocked`. Fix proposed (`docs/harness_bug_review.md` #1); not applied, because it would change V/V-E behaviour after the freeze |
> | U-INT-03 | 1 block (H0+C2/099) | **False positive**: `… \| python3` reads a pipe and cannot hang; the rule's own message recommends piping | Recovered two steps later. Fix proposed (`docs/harness_bug_review.md` #3) |
> | U-FMT-04 | 2 blocks (V-E/040, V-E/074) | 1 true positive (submit chained after `zip`), 1 harmless over-strict match (`bash -c "echo COMPLETE…"`) | Both submitted correctly at the next step |
> | U-INT-05 | 3 logs (H0+C2 1, V-E 2) | All `sudo apt-get …`; each returned `sudo: command not found` at once (these eval images have no `sudo`) | No hang, no timeout |
> | G-DST-01…05, G-INT-01, G-SEC-01, U-INT-01, U-INT-02, U-INT-04, U-FMT-01, U-FMT-02, U-FMT-05 | **0** in every configuration | n/a | An offline replay of the G-rules over all 3,094 commands, B0 and E included, also found **0** matches (the §5 log review) |
>
> Latent defects, found by testing the rules directly; none fired in eval:
> - G-DST-01 allows `rm -rf /app` and `rm -r -f /`.
> - G-DST-04 blocks the bare words "shutdown" and "reboot" in code and text, in every harness configuration including H0.
> - The log-only G-SEC-01 is checked before every U-rule, so a match (even `${MAX_TOKENS}`) hides any later block.
>
> Smaller mismatches in G-INT-01, G-DST-02, U-INT-01, U-INT-02 and U-FMT-04 are listed in `docs/guardrail_eval_review.md` §6.
>
> GuardrailLimit (10 blocks per trial) was never reached; the maximum was 6 (V-E/015). Lesson: the dev review saw no nested-shell or Ruby heredocs, so U-FMT-03's false positives surfaced only in eval. A future rule change should be tested against a replay of all eval commands before the freeze; `docs/harness_bug_review.md` reports such a replay for the proposed fix (12 U-FMT-03 blocks removed, U-FMT-04 kept, no new blocks).
