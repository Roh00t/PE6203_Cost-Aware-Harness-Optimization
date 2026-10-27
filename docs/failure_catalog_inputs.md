# Failure catalog: inputs for Asmitha

Roshan, 2026-10-27. Source material for `docs/failure_catalog.md` (the report's failure classification: harness-level vs model-level, at least one example trajectory per type). Everything here comes from eval pass 1, `results/eval/rohit-eval-pass1/` (B0, E, H0, V, V-E × 40 tasks).

- **Labels for every trial:** `results/analysis/eval/rohit-eval-pass1/failures/trials_classified.csv`. Counts are in `summary.csv`, and up to 3 ranked candidates per label, with steps quoted, are in `examples.md`.
- **Regenerate:** `uv run --frozen python scripts/classify_failures.py`. The rule table at the top of that script is the taxonomy; Isha owns it.
- **Known harness bugs behind some failures:** `docs/harness_bug_review.md`.

Each example below lists its trial folder `T`. Inside it:
- the trajectory is `T/agent/mini-swe-agent.trajectory.json`;
- the harness events are `T/agent/events.jsonl` (H0, V, V-E only);
- the verifier output is `T/verifier/test-stdout.txt` and `T/verifier/reward.txt`.

## Counts (primary label per trial)

| Label | Type | B0 | E | H0 | V | V-E |
|---|---|---|---|---|---|---|
| success (reward 1) | | 1 | 4 | 2 | 3 | 6 |
| guardrail_blocked | harness | 0 | 0 | 0 | 1 | 4 |
| unparsable_tool_call | harness | 30 | 31 | 30 | 23 | 7 |
| budget_exhausted | harness | 0 | 0 | 0 | 0 | 0 |
| timeout_no_recovery | harness | 0 | 0 | 0 | 0 | 0 (secondary in 3 V trials) |
| premature_submit_missing_output | harness | 1 | 0 | 2 | 1 | 2 |
| wrong_output | model | 2 | 5 | 1 | 7 | 10 |
| partial_credit | model | 1 | 0 | 1 | 2 | 2 |
| unclassified (verifier printed nothing) | | 5 | 0 | 4 | 3 | 9 |
| **Harness-level / model-level** | | 31 / 3 | 31 / 5 | 32 / 2 | 25 / 9 | 13 / 12 |

28 archived infrastructure attempts are excluded and not scored. The headline is the shift from harness-level to model-level failures as components are added: B0 has 31 harness-level and 3 model-level failures, V-E has 13 and 12. Unparsable tool calls dominate the stock harness and shrink with C0 + C2.

---

## Harness-level

### guardrail_blocked: V / 071-paste-image-docx (showcase, guardrail false positive)

`T = results/eval/rohit-eval-pass1/v/071-paste-image-docx/071-paste-image-docx__iLYbkcP` · reward 0 · exit RepeatedFormatError · 17 calls

**What happened.**
- The agent's first command was a correct `bash -lc "python3 - <<'PY' … PY"` that builds `image.docx` with python-docx.
- U-FMT-03 rejected it as an *unterminated heredoc* because the closing line reads `PY"`: the closing quote of the enclosing `bash -lc` string is on the same line.
- The same rejection hit 5 times (steps 1–4 and 6, plus a C4 stall nudge). The model then slid into 9 format errors and a 180 s command timeout, and the trial ended without the document.

**Contrast.**
- H0, which has no U-rules, solved this task (reward 1.0) with the same `python3 - <<'PY'` approach: `results/eval/rohit-eval-pass1/h0/071-paste-image-docx/071-paste-image-docx__2h92Tmt`, step 5.
- This is a harness-caused failure. The fix belongs in **C2's validation rule U-FMT-03** (bug #1 in `docs/harness_bug_review.md`).

The other guardrail trials:
- **V-E/015:** 6 false-positive blocks on Ruby `<<` inside a closed heredoc; plausibly caused the failure.
- **V-E/068:** 1 false positive; it recovered the next step.
- **V-E/040 and V-E/074:** correct U-FMT-04 blocks of a submit combined with other work; not the cause of failure.

### unparsable_tool_call: E / 116-bottom-left-page-numbers

`T = results/eval/rohit-eval-pass1/e/116-bottom-left-page-numbers/116-bottom-left-page-numbers__o7jtJFa` · reward 0 · exit RepeatedFormatError · 3 calls

**What happened.** On the stock harness, gpt-oss-120b never produced a usable tool call:
1. Its first call had malformed JSON arguments (`Expecting ',' delimiter … Missing 'command' argument`).
2. Its second reply was plain prose.
3. Its third reply wrote the command as plain-text JSON (`{"command":"sed -i …"}`) instead of a tool call.

Stock mini-swe-agent ends the run after 3 consecutive format errors, so the agent never touched the document.

**Which component.** **C2**: specific format-error feedback and a limit of 5 instead of 3, helped by C0's prompt. Across configurations, RepeatedFormatError endings drop from 30–33/40 (B0, E, H0) to 24 (V) and 12 (V-E).

A plainer variant for the text: **B0/040**, where the model wrote three refusals ("I don't have the ability to interact with a live web browser") and no tool call.

### timeout_no_recovery: V / 087-spreadsheet-to-doc-table (secondary label)

`T = results/eval/rohit-eval-pass1/v/087-spreadsheet-to-doc-table/087-spreadsheet-to-doc-table__M4ABK7C` · reward 0 · exit RepeatedFormatError · 17 calls

**What happened.**
- The agent converted a large price-list spreadsheet into a Word table with python-docx, cell by cell. That command hit the 180 s command timeout twice (steps 5 and 7, events show ~185–198 s).
- C4 appended its recovery recipe (run in the background with `nohup` and poll), but the model never ran another successful command. It went through format errors and a missing `pandoc` to RepeatedFormatError.
- Its primary label is `unparsable_tool_call`, because format errors take precedence. No pass-1 trial has `timeout_no_recovery` as its primary label.

**Which component.** **C4** timeout recovery (the recipe was given but not followed) and **C3**'s longer timeout (180 s was still too short for this approach).

V/073 is not in this type: its two "timeouts" are `pkill -f soffice -9` killing its own shell after 0.2 s (rc 137). The harness logs them as `command_timeout`, but the classifier counts a timeout only when the command ran for at least 90% of its limit (bug review, #7).

### premature_submit_missing_output: B0 / 075-nuclei-locations

`T = results/eval/rohit-eval-pass1/b0/075-nuclei-locations/075-nuclei-locations__VWrHCWc` · reward 0 · exit Submitted · 10 calls

**What happened.**
- CellProfiler failed on every attempt (4 tracebacks, with pipeline files rewritten in between).
- The model then wrote "I couldn't get CellProfiler to run correctly in this environment" and submitted anyway.
- The verifier reports `Missing required file: /app/artifacts/nuclei_locations.csv`.

**Which component.** **C5** (the pre-submission gate checks that the named output exists). In V, the same task got a C5 checklist with ✓ for the CSV: the agent wrote the file but with 0 rows, which moves the failure to `wrong_output`. V-E solved the task. C4 targets the repeated CellProfiler failures.

### budget_exhausted: no failed trial in pass 1

Only V/088 reached a cap: the 50-step cap, ending in `LimitsExceeded`. It had already written its outputs and scored 1.0. No trial hit the dollar cap (`CostCapExceeded`). State this explicitly in the catalog.

---

## Model-level

### wrong_output: E / 115-remove-explorer-find-key (clean model-level case)

`T = results/eval/rohit-eval-pass1/e/115-remove-explorer-find-key/115-remove-explorer-find-key__XZbB9Bt` · reward 0 · exit Submitted · 8 calls

**What happened.**
- The agent found that `~/.config/Code/User/keybindings.json` didn't exist, wrote one with a heredoc, read it back, and submitted.
- The file exists and parses, but the verifier says it *"does not contain the expected VS Code keybinding"*: the model wrote the wrong rule for removing the Explorer's Ctrl+F binding.
- The harness did its job; the model's knowledge was the limit.

**Which component.** None. This is a model-level failure: wrong plan or beyond capability. C5's read-back request can't catch a semantically wrong but well-formed file.

A second clean example: **V-E/000-count-nuclei** (`results/eval/rohit-eval-pass1/v-e/000-count-nuclei/000-count-nuclei__XKxdphG`). The model's thresholding script counted 27 nuclei, the verifier expected 6, and the model confirmed its own wrong number with `read_file` before submitting.

### partial_credit: V-E / 112-capture-video-frame

`T = results/eval/rohit-eval-pass1/v-e/112-capture-video-frame/112-capture-video-frame__MnDyWi8` · reward 0.50 · exit Submitted · 10 calls

**What happened.**
- The agent extracted a frame with `ffmpeg -ss 00:00:05` and saved it as the requested PNG.
- The grader scores image similarity (SSIM) against the reference frame, so the wrong timestamp earned 0.50. The oracle itself scores only 0.85 on this task.

**Which component.** None; model-level.

Caveat for the text: tasks 074 (0.819) and 076 (0.755) give nearly the same partial reward in almost every configuration, including trials that ended on format errors without touching the output. Partial credit there reflects the untouched input file, not agent work.

### unclassified: H0 / 110-rotate-macintosh-video (needs manual review)

`T = results/eval/rohit-eval-pass1/h0/110-rotate-macintosh-video/110-rotate-macintosh-video__8UZcG6W` · reward 0 · exit Submitted · 2 calls

**What happened.**
- The agent ran a single `ffmpeg … -vf "rotate=PI"`, a 180° rotation, and submitted.
- The gold output is a vertical flip only. A 180° rotation flips both axes, the same mistake as the benchmark's own reference solution (`configs/subset_amendments.json`, `kept_below_reward_1`). On manual review this is a model-level `wrong_output`.
- The verifier printed nothing, which is why the script can't tell.

21 trials are unclassified for the same reason: 18 tasks' verifiers print no failure reason. Provisional verdicts for all 21 trials, and for the 5 guardrail trials, are in `results/analysis/eval/rohit-eval-pass1/failures/manual_review.md`, pending Isha's check. If accepted: 14 are `wrong_output` and 7 `premature_submit_missing_output`. That gives harness/model splits of B0 35/4, E 31/5, H0 33/5, V 25/12, V-E 13/21.
