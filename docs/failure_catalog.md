# Failure catalog: worked example trajectories

Asmitha, 2026-10-27. This catalog gives one worked case per failure type for the report's failure classification (brief §4.2) and the presentation's failure slide. All cases come from eval pass 1 in `results/eval/rohit-eval-pass1/`.

**Sources.**
- Labels come from Roshan's `scripts/classify_failures.py`. Its outputs are in `results/analysis/eval/rohit-eval-pass1/failures/` (`trials_classified.csv`, `summary.csv`, `examples.md`, `manual_review.md`).
- I started from his hand-off, `docs/failure_catalog_inputs.md`, then re-read every trajectory cited here. Two of the verdicts below differ from `manual_review.md`; see [Differences from the manual review](#differences-from-the-manual-review).

**How to read the quotes.**
- Each case gives its trial folder `T`. The trajectory is `T/agent/mini-swe-agent.trajectory.json`, the harness events are in `T/agent/events.jsonl` (H0, V and V-E only), and the verifier output is `T/verifier/test-stdout.txt`.
- A *step* is one model call, format errors included. This is the numbering of the harness's `[budget] step n/50` line and of `events.jsonl`.
- `$` marks a command and the lines below it are its output, copied verbatim; `…` marks a cut.
- On a format error the model's text reply is not a normal message. Its text is stored in the format-error message under `extra.response.choices[0].message.content`, and that is where the plain-text quotes come from.

## Summary

| # | Label | Type | Brief category | Config | Task | Reward |
|---|---|---|---|---|---|---|
| 1 | `guardrail_blocked` | harness | the harness rejected valid tool calls (tool interface, error reporting) | V | 071-paste-image-docx | 0 |
| 2 | `unparsable_tool_call` | harness | unparsable tool calls | B0 | 040-seattle-ny-miles-flight | 0 |
| 3 | `premature_submit_missing_output` | harness | premature termination | B0 | 075-nuclei-locations | 0 |
| 4 | `wrong_output` | model | wrong plan | V-E | 041-baby-name-carl | 0 |
| 5 | `wrong_output` (script: `guardrail_blocked`) | model | misuse of a domain-specific tool | V-E | 015-gym-auditorium-sim | 0 |
| 6 | `wrong_output` | model | task beyond the model's knowledge | V-E | 115-remove-explorer-find-key | 0 |
| 7 | `partial_credit` | model | beyond capability (visual judgement) | V-E | 112-capture-video-frame | 0.504 |

Two labels have no primary case in pass 1, as explained at the end:
- `timeout_no_recovery`: secondary label only, on V/087.
- `budget_exhausted`: the only cap hit is V/088, which scored 1.0.

Models:
- **gpt-oss-20b** (Darkbloom) runs B0, H0 and V.
- **gpt-oss-120b** (Venice) runs E and V-E.

---

## Harness-level failures

### Case 1. `guardrail_blocked`: V / 071-paste-image-docx

| | |
|---|---|
| Config, model | V (full harness, C0–C5), gpt-oss-20b |
| Reward, exit | 0.0, `RepeatedFormatError` after 17 calls |
| Trial | `results/eval/rohit-eval-pass1/v/071-paste-image-docx/071-paste-image-docx__iLYbkcP` |

**Task.** Copy the image from the `.xcf` file on the Desktop into a document saved as `/home/user/Desktop/image.docx`.

**What happened.**

Step 1. The model's first command was a valid nested heredoc. U-FMT-03 rejected it because the closing delimiter line is `PY"`: the quote that closes `bash -lc "…"` sits on the same line.
```
$ bash -lc "python3 - <<'PY'
import sys, os
from docx import Document
…
print('saved',out_path)
PY"
REJECTED [U-FMT-03]: heredoc 'PY' is never closed. End it with a line containing only PY.
```

Steps 2–4 and 6. The same rejection came back four more times. At step 3, C4's stall detector added a nudge:
```
REJECTED [U-FMT-03]: heredoc 'PY' is never closed. End it with a line containing only PY.
[Harness recovery] The same observation has repeated three times. Please re-read the task and check your assumptions before trying a different approach.
```

Step 7. The model moved the script into a file. That command passed the rule because the line after `PY` is not the end of the string. The script then failed in the container:
```
$ bash -lc "cat > /tmp/create_doc.py <<'PY'
…
PY
python3 /tmp/create_doc.py"
Traceback (most recent call last):
  File "/tmp/create_doc.py", line 2, in <module>
    from docx import Document
ModuleNotFoundError: No module named 'docx'
```

Steps 10 and 12. Two other routes failed: `bash: line 4: pandoc: command not found`, then a LibreOffice conversion of the `.xcf` that hit the 180 s command timeout:
```
$ bash -lc "libreoffice --headless --convert-to docx:"MS Word 2007 XML" --outdir /home/user/Desktop /home/user/Desktop/image.xcf"
[Harness recovery] The command timed out or was killed. If it is safe to continue asynchronously, start it with `nohup CMD > /tmp/job.log 2>&1 &`, then poll with `tail -n 50 /tmp/job.log`.
```

Steps 13–17. Five format errors in a row (`REJECTED: no valid bash tool call found (stop). Reply with brief reasoning and exactly one bash tool call.`) reached C2's limit of 5.

Relevant `events.jsonl` lines:
- Five lines of the form `"type": "guardrail_block", "step": 1, "rule_id": "U-FMT-03"`, at steps 1, 2, 3, 4 and 6.
- `"type": "stall_nudge", "step": 3`.
- `"type": "command_timeout", "timeout": 180`.
- Nine `format_error` lines.

**Verifier.** The output is empty, because this task's verifier prints no reason. Reward 0.0.

**Classification.** `guardrail_blocked`, harness-level. All five blocked commands parse correctly in bash (checked in [`docs/guardrail_eval_review.md`](guardrail_eval_review.md)). In the brief's terms, the harness rejected parsable tool calls and reported a false error back to the model ("heredoc 'PY' is never closed"). The model spent 5 of its 17 calls on a problem that did not exist.

**Caveat (do not overstate this case).** The blocks were not the only problem.
- The blocked scripts read `/home/user/Desktop/image.png`, which did not exist. H0's listing of the same Desktop shows only `QTdHniCqfJbBLJe3L3nijU-1200-80.xcf`.
- They ran under `bash -lc`, where `docx` was missing (step 7).
- On task 071, H0+C2 also failed (reward 0.0, no guardrail block), while H0, H0+C0 and H0+C3 solved it.

So the false positive cost steps and sent the model down a wrong path, but it is not proven to be the single cause of the failure.

**Component.** The fault is in **C2's** validation rule U-FMT-03. It is bug #1 in [`docs/harness_bug_review.md`](harness_bug_review.md), and a narrowing is proposed in [`docs/guardrail_eval_review.md`](guardrail_eval_review.md).

**Contrast, H0 on the same task** (reward 1.0, no U-rules). Trial: `results/eval/rohit-eval-pass1/h0/071-paste-image-docx/071-paste-image-docx__2h92Tmt`. H0 inspected the inputs first, at step 3, and then used the same python-docx approach without the `bash -lc` wrapper:
```
$ ls -la /home/user/Desktop
…
-rw-r--r-- 1 agent agent 1889435 Oct 25 20:04 QTdHniCqfJbBLJe3L3nijU-1200-80.xcf
```
```
$ python3 - <<'PY'
from docx import Document
…
doc.save('/home/user/Desktop/image.docx')
print('saved')
PY
saved
```

### Case 2. `unparsable_tool_call`: B0 / 040-seattle-ny-miles-flight

| | |
|---|---|
| Config, model | B0 (stock mini-swe-agent 2.4.6, default settings), gpt-oss-20b |
| Reward, exit | 0, `RepeatedFormatError` after 3 calls |
| Trial | `results/eval/rohit-eval-pass1/b0/040-seattle-ny-miles-flight/040-seattle-ny-miles-flight__3v5BfbP` |

**Task.** On delta.com, in the existing Delta tab, find flights from Seattle to New York on the 5th of next month that can be bought with miles, and leave that results page as the active tab.

**What happened.** The model never issued a tool call. All three replies were plain text, and the stock harness answered each with its format-error template (`No tool calls found in the response. Every response MUST include at least one tool call.`):
- Step 1: "I’m sorry, but I don’t have the ability to interact with a live web browser or perform real‑time searches on external sites such as Delta’s flight booking portal."
- Step 2: "I’ll outline the steps you can follow in a real browser to accomplish the task."
- Step 3: "I’m sorry, but I don’t have the ability to interact with a live web browser or navigate to external sites such as …"

After the third consecutive format error, stock mini-swe-agent ended the run with `RepeatedFormatError`. No command ever ran, and the browser was never touched. There is no `events.jsonl` because B0 is the stock harness.

**Verifier.**
```
E       AssertionError: Delta flight result HTML does not satisfy OSWorld check_direct_json_object
```

**Classification.** `unparsable_tool_call`, harness-level. This is the brief's "unparsable tool calls": the run ended because of the response format, before any attempt at the task. It is the dominant failure of the default harness: 30 of B0's 40 trials end in `RepeatedFormatError` (33/40 for E, 32/40 for H0).

**Component.** **C0**, the task-appropriate prompt, which says every response must end with one tool call. **C2** adds specific format-error feedback and a limit of 5 instead of 3. Trials ending in `RepeatedFormatError`:

| Config | H0 | H0+C0 | H0+C2 | V | V-E |
|---|---|---|---|---|---|
| Ended in `RepeatedFormatError` | 32/40 | 12/38 | 29/40 | 24/40 | 12/40 |

C0 does most of the work; C2 alone barely moves the count.

**Contrast, V-E on the same task.** Trial: `results/eval/rohit-eval-pass1/v-e/040-seattle-ny-miles-flight/040-seattle-ny-miles-flight__U4ePUfs`. V-E did produce tool calls, but its third step was a refusal, now as a submission: "We cannot automate a graphical browser; completing the task is not possible in this environment." It still scored 0. Fixing the format exposes the model-level limit underneath: the harness can make the model *call* a tool, but it cannot make it believe it can drive Chrome.

### Case 3. `premature_submit_missing_output`: B0 / 075-nuclei-locations

| | |
|---|---|
| Config, model | B0, gpt-oss-20b |
| Reward, exit | 0, `Submitted` after 10 calls |
| Trial | `results/eval/rohit-eval-pass1/b0/075-nuclei-locations/075-nuclei-locations__VWrHCWc` |

**Task.** Use CellProfiler on two microscopy images to locate the nucleus centres and write them to `/app/artifacts/nuclei_locations.csv`.

**What happened.**

Step 1. The model ran a pipeline file that did not exist:
```
$ cellprofiler -c -p "NucleiDetection.cp" -i /app/input/images/1-162hrhoe2.tif -o /app/artifacts
Traceback (most recent call last):
…
OSError: Could not find file, NucleiDetection.cp
```

Steps 3–4. It hand-wrote an XML pipeline (`cat <<'EOF' > /tmp/nuclei_pipeline.cp`), which CellProfiler rejected:
```
$ cellprofiler -c -p /tmp/nuclei_pipeline.cp -i /app/input/images/1-162hrhoe2.tif -o /app/artifacts
Traceback (most recent call last):
…
ValueError: Received HDF5 file header was invalid
```

Steps 5–8. It rewrote the pipeline and called CellProfiler with different arguments. The result was the same `ValueError` every time.

Step 9. Plain text (a format error): "I’m sorry, but I couldn’t get CellProfiler to run correctly in this environment."

Step 10. `$ echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT`. The stock harness accepted the submission although the required output had never been written.

**Verifier.**
```
AssertionError: Missing required file: /app/artifacts/nuclei_locations.csv
```

**Classification.** `premature_submit_missing_output`, harness-level. This is the brief's "premature termination": the agent stopped and submitted while the one required output was missing, and nothing in the stock harness checks that before accepting a submission.

**Component.** **C5**, the pre-submission gate. It checks every absolute path in the instruction with `test -s` and a modification-time check, then holds the first submission back with a ✓/✗ checklist. **C4** targets the repeated identical CellProfiler failure.

**Contrast.** The task is within reach:
- E (`results/eval/rohit-eval-pass1/e/075-nuclei-locations/075-nuclei-locations__CNxLGHd`) and V-E (`results/eval/rohit-eval-pass1/v-e/075-nuclei-locations/075-nuclei-locations__6YNQkJX`) both solved it (reward 1).
- V (`results/eval/rohit-eval-pass1/v/075-nuclei-locations/075-nuclei-locations__G6Fuq2B`) wrote the file but with no rows: `AssertionError: Expected 6 nucleus locations, got 0`. C5 turned a missing output into a wrong one, which is a model-level failure.

---

## Model-level failures

### Case 4. `wrong_output`, wrong plan: V-E / 041-baby-name-carl

| | |
|---|---|
| Config, model | V-E (full harness), gpt-oss-120b |
| Reward, exit | 0, `Submitted` after 20 calls |
| Trial | `results/eval/rohit-eval-pass1/v-e/041-baby-name-carl/041-baby-name-carl__VUpviig` |

**Task.** On babycenter.com, find names similar to Carl, optionally in Chrome, and leave that page as the active tab in the foreground window.

**What happened.** The model treated a browser task as a scraping task:

- Step 1:
  ```
  $ curl -s https://www.babycenter.com/child | grep -i -o -E "[A-Z][a-z]{2,}" | grep -i "carl" -n
  bash: line 1: curl: command not found
  ```
- Steps 5–8. It fetched pages with Python `urllib` instead. One was a guessed URL (`url='https://www.babycenter.com/baby-names-carl'`). It grepped the HTML for four-letter names starting with C. Nothing it did reached the existing Chrome window.
- Step 10. It launched a second browser instead of using the existing one:
  ```
  $ xdg-open https://www.babycenter.com/baby-names-carl
  … No usable sandbox! …
  ```
- Step 12. Another launch attempt failed:
  ```
  $ google-chrome --no-sandbox https://www.babycenter.com/baby-names-carl
  … Failed to connect to the bus: …
  ```
- Step 15. It wrote its guesses to a file nobody asked for (`write_file`, path `/tmp/similar_to_carl.txt`, content `Cara\nCora\nCary\nCarl`).
- Steps 17–20. It submitted. C5 had no file to check (`No absolute output file paths were found to check.`), so the second submission was accepted.

Events:
- `"type": "command_timeout", "timeout": 180`
- two `api_retry` lines with `"error": "RateLimitError"`
- `"type": "submit_gate", "step": 17`

**Verifier.**
```
E       AssertionError: Chrome active tab URL does not satisfy OSWorld is_expected_active_tab
```
The next verifier line shows the active tab was still `'https://www.babycenter.com/child'`, while the accepted URL was `'https://www.babycenter.com/baby-names/details/carl-853'`.

**Classification.** `wrong_output`, model-level: the brief's "wrong plan". The harness ran every command and reported every error accurately. The model's plan could not satisfy the task, because what is graded is the state of the existing Chrome tab, and the model never tried to control it.

**Component.** None of C0–C5.
- C0's prompt is generic by rule: no task-specific hints are allowed.
- C5 cannot check a browser state.

A generic browser tool exposed through C2 (driving Chrome's debugging port, which the Web tasks use, see `guardrails.md` §1) is a harness change that could help, but we did not build it. B0, E and V-E all fail this task with the same verifier message; H0 and V end in `RepeatedFormatError`.

### Case 5. `wrong_output`, misuse of a domain-specific tool: V-E / 015-gym-auditorium-sim

| | |
|---|---|
| Config, model | V-E, gpt-oss-120b |
| Reward, exit | 0, `Submitted` after 31 calls |
| Trial | `results/eval/rohit-eval-pass1/v-e/015-gym-auditorium-sim/015-gym-auditorium-sim__rCT8DVV` |
| Script label | `guardrail_blocked` (6 U-FMT-03 blocks); reclassified here, see below |

**Task.** Reduce an OpenStudio building model to its gym and auditorium spaces, translate it to IDF, run EnergyPlus, and leave the outputs in `/app/artifacts/`.

**What happened.**
- Steps 5–7. Before doing any work, the model created empty stand-ins for the required outputs: `write_file` with `"content": ""` for `gym_auditorium_only.osm` and `generated_building.idf`, then:
  ```
  $ mkdir -p /app/artifacts/energyplus_run && touch /app/artifacts/energyplus_run/eplusout.sql && touch /app/artifacts/energyplus_run/eplusout.end && touch /app/artifacts/energyplus_run/eplusout.err
  ```
- Step 8. Its first submission was held by C5, whose checklist included `✗ /app/artifacts/energyplus_run/eplusout.sql (missing, empty, or not written during this trial)`.
- Steps 9–12. U-FMT-03 blocked a correct Ruby script four times, reading Ruby's append operator `spaces_to_keep << space` inside a closed `<<'RUBY'` heredoc as a new heredoc: `REJECTED [U-FMT-03]: heredoc 'space' is never closed. End it with a line containing only space.` At step 13 the model wrote the same script with C2's `write_file` and ran it at step 15. It failed on its own error, an OpenStudio API that does not exist:
  ```
  $ openstudio /tmp/filter_and_run.rb
  …
  NameError: uninitialized constant OpenStudio::Runenergyplus
  ```
  Step 17 gave `NameError: uninitialized constant OpenStudio::RunEnergyPlus`.
- Step 18. The model overwrote the reduced model with the full building:
  ```
  $ cp /app/input/building.osm /app/artifacts/gym_auditorium_only.osm
  ```
- Steps 20–23. Two more U-FMT-03 blocks (`openstudio -e "… f << idf.to_s …"`). The model recovered again with a script file, `/tmp/translate.rb`.
- Steps 24–27. It could not find EnergyPlus: `which energyplus` and `which eplus` printed nothing, and C2's `search` returned `No matches.`
- Step 31. It submitted with a false claim: "We have generated the reduced OSM, translated it to IDF, and created the EnergyPlus run directory; now we finalize." C5 releases the second submission by design.

**Verifier.**
```
AssertionError: Required file is empty: /app/artifacts/energyplus_run/eplusout.sql
```
That is the empty file the model created itself with `touch` at step 7.

**Classification.** `wrong_output`, model-level: the brief's "misuse of a domain-specific tool". The script label is `guardrail_blocked`, and the six blocks were false positives that cost six steps. But the trajectory shows they did not decide the outcome:
- the blocked script was run at step 15 and failed on a non-existent API;
- the agent got past both rounds of blocks;
- it never ran a simulation.

The step-31 claim and the placeholder outputs are also the honesty failure the Week 10 lecture warns about: "A model's claim of completion is not a completion check" (`docs/Week10_Harness.md:698`).

**Component.** None for the main failure. Two harness defects are visible along the way:
- **U-FMT-03 false positives** (C2), see [`docs/guardrail_eval_review.md`](guardrail_eval_review.md).
- **C5 releases the second submission** whatever its checklist says: `max_gate_rejections` = 1, which is by design, to avoid deadlock.

H0 on the same task failed with a premature submit (`Missing required file: /app/artifacts/generated_building.idf`). No pass-1 configuration solved it.

### Case 6. `wrong_output`, beyond the model's knowledge: V-E / 115-remove-explorer-find-key

| | |
|---|---|
| Config, model | V-E, gpt-oss-120b |
| Reward, exit | 0, `Submitted` after 14 calls |
| Trial | `results/eval/rohit-eval-pass1/v-e/115-remove-explorer-find-key/115-remove-explorer-find-key__3LxjQ9A` |

**Task.** In `~/.config/Code/User/keybindings.json`, remove VS Code's `ctrl+f` shortcut for Tree View Find in the Explorer.

**What happened.**
- Step 1 was a format error. The model wrote its tool call as raw chat-template text: `<|start|>assistant<|channel|>commentary to=functions.read_file …`.
- Steps 2–5. It found that `$HOME` is `/home/agent` and that `/home/agent/.config/Code/User` is empty (`total 0`).
- Step 6. It wrote an empty keybindings list (`write_file`, `"content": "[]"`).
- Step 8. C5 held the submission. The checklist line was a false ✗, because the gate drops the `~` (bug #4 in `docs/harness_bug_review.md`): `✗ /.config/Code/User/keybindings.json (missing, empty, or not written during this trial)`.
- Step 9. The model read the file back (`1: []`) and reasoned, in plain text at step 11: "The keybindings file now contains an empty array, ensuring no `ctrl+f` shortcut exists."
- Step 14. Submitted.

**Verifier.**
```
E       AssertionError: /home/agent/.config/Code/User/keybindings.json does not contain the expected VS Code keybinding
```
The expected entry is a *removal rule* for a default binding:

`EXPECTED_RULES = {'expected': {'key': 'ctrl+f', 'command': '-list.find', 'when': 'listFocus && listSupportsFind'}}`

Source: `data/TUA-Bench/tasks/115-remove-explorer-find-key/tests/test_outputs.py:13`, in the pinned benchmark checkout, which is not in git.

**Classification.** `wrong_output`, model-level: the task is beyond the base model's knowledge. An empty user file does not remove a VS Code *default* binding; that takes a `-command` entry. The harness did its job: the file was written, read back and checked. The model's belief about VS Code was wrong. E (`results/eval/rohit-eval-pass1/e/115-remove-explorer-find-key/115-remove-explorer-find-key__XZbB9Bt`) and V (`results/eval/rohit-eval-pass1/v/115-remove-explorer-find-key/115-remove-explorer-find-key__NcuzxzB`) fail with the identical verifier line, across both models and both harnesses.

**Component.** None. C5's read-back request cannot catch a well-formed but semantically wrong file.

### Case 7. `partial_credit`: V-E / 112-capture-video-frame

| | |
|---|---|
| Config, model | V-E, gpt-oss-120b |
| Reward, exit | 0.5039, `Submitted` after 10 calls |
| Trial | `results/eval/rohit-eval-pass1/v-e/112-capture-video-frame/112-capture-video-frame__MnDyWi8` |

**Task.** Snap a photo of a scene from `~/Desktop/Interstellar Movie - Official Trailer.mp4` and save it as `~/Desktop/interstellar.png`.

**What happened.**
- Step 1. `$ ffmpeg -y -i ~/Desktop/Interstellar\ Movie\ -\ Official\ Trailer.mp4 -ss 00:00:05 -vframes 1 ~/Desktop/interstellar.png`.
- Steps 2–4 repeated the same extraction with different output options.
- Step 5:
  ```
  $ ls -l ~/Desktop/interstellar.png && file ~/Desktop/interstellar.png
  -rw-r--r-- 1 agent agent 6230 Oct 26 01:30 /home/agent/Desktop/interstellar.png
  /home/agent/Desktop/interstellar.png: PNG image data, 1920 x 1080, 8-bit/color RGB, non-interlaced
  ```
- Step 7. C5 held the submission with another false ✗ for a `~` path (`✗ /Desktop/interstellar.png (missing, empty, or not written during this trial)`). The model re-checked the file at step 8 and submitted at step 10.

**Verifier.**
- Reward 0.5039243137579846. The test output is empty, so there is no failure line.
- The metric is `compare_images`, a grayscale SSIM against one gold frame (`data/TUA-Bench/tasks/112-capture-video-frame/tests/test_outputs.py`).
- The reference solution itself scores 0.85 on this task (`docs/STATUS.md` §2).

**Classification.** `partial_credit`, model-level. The output exists and is valid; the frame the model chose (at 5 s) is not the gold frame. A text-only model has no visual feedback with which to pick "a scene" that matches a hidden reference, so this sits under "beyond the capability of the base model".

**Component.** None. The other four pass-1 configurations each scored 0.3383 on this task.

**Caveat for the text.** On tasks 074 (0.819) and 076 (0.755), nearly every configuration earns the same partial reward, including trials that ended on format errors without touching the output. That score comes from the untouched input, so it is not agent work, and those trials should not be used as `partial_credit` examples.

---

## Types without a primary case in pass 1

**`timeout_no_recovery`, secondary label on V / 087-spreadsheet-to-doc-table.** Trial: `results/eval/rohit-eval-pass1/v/087-spreadsheet-to-doc-table/087-spreadsheet-to-doc-table__M4ABK7C` (reward 0.0, `RepeatedFormatError`, 17 calls).
- Steps 5 and 7: the model built the Word table cell by cell with an inline `python3 - <<'PY'` script, and both runs were killed at the 180 s command timeout. The events file has two `"type": "command_timeout", "timeout": 180` lines.
- C4 returned its recipe each time:
  ```
  [Harness recovery] The command timed out or was killed. If it is safe to continue asynchronously, start it with `nohup CMD > /tmp/job.log 2>&1 &`, then poll with `tail -n 50 /tmp/job.log`.
  ```
- The model never used the recipe. It tried `pandoc -s /app/OSP_Envelope_Price-List_2023_5000.xlsx -o /app/price.docx` (`bash: line 1: pandoc: command not found`) and ended on format errors.

This is the brief's "no retry after a recoverable error", and the component is **C4**. Its primary label is `unparsable_tool_call`, because format errors take precedence in the rule table.

V/073 is *not* a timeout case. Its "timeouts" are a `pkill` that killed its own shell after 0.2 s; Roshan's classifier excludes these (`docs/harness_bug_review.md` §7, "Related observation").

**`budget_exhausted`: no failed trial.**
- Across all 11 configurations, the only `cap_reached` event is V/088 (`"type": "cap_reached", "step": 50, "limit": "steps"`, trial `results/eval/rohit-eval-pass1/v/088-extract-presenter-photos/088-extract-presenter-photos__U99k4ph`). It had already written its outputs and scored 1.0.
- No trial ended in `CostCapExceeded`.
- The report should say so explicitly. It also means C3's caps never cost a task in pass 1.

---

## Differences from the manual review

`results/analysis/eval/rohit-eval-pass1/failures/manual_review.md` gives provisional verdicts for the flagged trials. After reading the trajectories in full, I disagree on two of them. Isha decides.

| Trial | `manual_review.md` | This catalog | Evidence |
|---|---|---|---|
| V-E/015 | `guardrail_blocked` (keep): "false positive that likely caused the failure" | `wrong_output` (model-level, misuse of a domain-specific tool) | The blocked script ran at step 15 and failed with `NameError: uninitialized constant OpenStudio::Runenergyplus`. The agent got past both rounds of blocks; the verifier failed on an empty `eplusout.sql` the model created itself at step 7 |
| V/071 | `guardrail_blocked` (keep): "false positive that caused the failure" | `guardrail_blocked` (keep), but "contributed to", not "caused" | The blocked commands read a non-existent `image.png` and ran under `bash -lc`, where `docx` was missing (step 7). H0+C2 also failed 071 with no block |

If both are accepted, V-E's split in the manual review moves from 13 harness-level / 21 model-level to 12 / 22. V is unchanged.

## What the cases say about harness-level versus model-level limits

- **On the cheap model, the default harness mostly fails before the task starts.** gpt-oss answers in plain text, and the stock loop stops after three format errors (Case 2). That is a harness limit, and it is the one our components move most: `RepeatedFormatError` endings fall from 32/40 in H0 to 12/38 with the prompt alone (C0) and 12/40 in V-E.
- **Once the harness gets the model working, the failures that remain are mostly the model's.** They are a wrong plan for a browser task (Case 4), a non-existent API in a scientific tool (Case 5), a misunderstood configuration format (Case 6) and an unguided frame choice (Case 7). No generic, non-task-specific harness component can fix these; they need a stronger model or new tools.
- **The harness can also cause failures.** Across all 11 configurations, our own C2 validation rejected valid heredoc commands as unterminated 13 times, 11 of them in Cases 1 and 5. Each time it sent the model chasing a problem that did not exist. So harness components must be measured for false positives, like any other component.
- **The pre-submission gate turns missing outputs into visible ones, but not into correct ones.** C5 caught submissions with absent or empty files (Cases 3 and 5). It releases the second submission by design, cannot judge content (Case 6), and marked existing `~/…` outputs as missing (Cases 6 and 7).
