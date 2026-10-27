# Manual review of flagged trials (provisional)

Roshan, 2026-10-27. These are provisional labels for the 26 trials that `trials_classified.csv` marks `needs_review = yes`: 21 `unclassified` and 5 `guardrail_blocked`. **Isha to confirm or change them.** Each verdict comes from reading the trajectory (`agent/mini-swe-agent.trajectory.json`) and, for V/V-E, the C5 checklist the agent received. No verifier reason is available for these tasks.

How the labels were decided:
- If the agent wrote or changed the output and the verifier still failed it, the label is `wrong_output` (model-level).
- If the agent submitted without producing or changing the output, the label is `premature_submit_missing_output` (harness-level, the class C5 targets). This includes refusals, giving up, and fabricating a stand-in file.

## Unclassified (21)

| Trial | Provisional label | Evidence (step numbers are model calls) |
|---|---|---|
| B0/016-count-invoice-pivot | premature_submit_missing_output | Never touched the workbook: 23 calls, only `ls`, `echo` and repeated `cp /app/Invoices.xlsx /tmp/…`, then submit |
| B0/068-strike-first-two-lines | wrong_output | A python-pptx script printed `done` (step 3) and the model claimed the first two lines were struck through; the verifier disagrees |
| B0/089-install-recommended-exts | premature_submit_missing_output | Refused ("I can't help with that"), echoed "please install plugins manually", submitted |
| B0/105-search-cell-b6 | premature_submit_missing_output | **Task defect:** the instruction reads "Given the file `{path}`" (an unfilled placeholder, in all 5 configs). The model tried `/path/to/file.xlsx`, then gave up. V-E solved it anyway by searching `/home` |
| B0/117-comma-text-to-table | premature_submit_missing_output | `pandoc` missing; converted to text in `/tmp`, said "I'm unable to complete this task", submitted with the document unchanged |
| H0/016-count-invoice-pivot | wrong_output | An openpyxl script wrote counts to Sheet2 ("Pivot table created", run 14 times): a static table, not the pivot table the task asks for |
| H0/101-rearrange-warm-tiles | wrong_output | Wrote `/app/rearranged.png`, but cropped unequal widths (320/320/322) and tinted the tiles with `-colorize` instead of reordering them by warmth |
| H0/110-rotate-macintosh-video | wrong_output | `ffmpeg -vf rotate=PI` flips both axes; the gold output is a vertical flip only (same mistake as the reference solution) |
| H0/111-set-video-wallpaper | premature_submit_missing_output | Extracted a frame, but `gsettings: command not found`, so the wallpaper was never set; submitted anyway |
| V/080-convert-novel-epub | wrong_output | No pandoc or ebooklib; built `Pass_Through.epub` (20 KB) with a hand-written script (step 15), confirmed it exists, submitted |
| V/085-webext-happy-scaffold | wrong_output | The webext.eu download wasn't a zip; hand-wrote `manifest.json` and the files instead of the generated scaffold. C5 showed ✓ for `background_script.js` |
| V/101-rearrange-warm-tiles | wrong_output | Wrote `/app/rearranged.png` (C5 ✓) with an ImageMagick crop and append; the verifier disagrees with the ordering or tint |
| V-E/016-count-invoice-pivot | wrong_output | Computed counts with openpyxl and saved the workbook (C5 ✓); a static table, not a pivot table |
| V-E/071-paste-image-docx | wrong_output | Exported the XCF to PNG, wrote `doc.md` containing `![](image.png)`, and converted it with LibreOffice to a 4.3 KB `image.docx`. LibreOffice reads `.md` as plain text, so the document almost certainly holds that literal text, not the image |
| V-E/080-convert-novel-epub | wrong_output | Installed ebooklib, created `Pass Through.epub` (21 KB); the verifier disagrees with its content or structure |
| V-E/085-webext-happy-scaffold | premature_submit_missing_output | Hand-wrote the manifest and popup only. C5 reported `✗ …/background_script.js` (a required file); the model resubmitted at once, and the gate only fires once |
| V-E/087-spreadsheet-to-doc-table | wrong_output | Wrote `/app/price.docx` with one table (python-docx); the formatting wasn't preserved |
| V-E/089-install-recommended-exts | premature_submit_missing_output | Read the plugin list, then said installation is impossible and **fabricated** `installed_extensions.txt` with placeholder IDs (`aaaa…`, `bbbb…`). Nothing was installed |
| V-E/101-rearrange-warm-tiles | wrong_output | Wrote `/app/rearranged.png` (C5 ✓, `identify` checked); the verifier disagrees |
| V-E/116-bottom-left-page-numbers | wrong_output | Added a left-aligned PAGE field to `word/footer1.xml` and saved in place (C5 ✓); the verifier disagrees, possibly about other sections or footers |
| V-E/117-comma-text-to-table | wrong_output | Rewrote the paragraphs as tables with python-docx and saved in place (C5 ✓); the verifier disagrees |

## Guardrail-blocked (5)

These verdicts restate `docs/harness_bug_review.md` §1 and the rule events.

| Trial | Provisional label | Evidence |
|---|---|---|
| V/071-paste-image-docx | guardrail_blocked (keep): false positive that caused the failure | 5 U-FMT-03 blocks on a valid nested heredoc; H0 solved the same task with the same approach |
| V-E/015-gym-auditorium-sim | guardrail_blocked (keep): false positive that likely caused the failure | 6 U-FMT-03 blocks on Ruby `<<`; the required outputs were never written |
| V-E/068-strike-first-two-lines | wrong_output | 1 U-FMT-03 block (false positive), recovered next step by writing the script to a file; the saved deck still failed |
| V-E/040-seattle-ny-miles-flight | wrong_output | 1 U-FMT-04 block of `bash -c "echo COMPLETE…"` (per spec, harmless); submitted next step, verifier: wrong flight results |
| V-E/074-apa-references-review | unparsable_tool_call | 1 correct U-FMT-04 block (submit chained after `zip`); the trial then ended on format errors (0.819 is the untouched-input score) |

## Counts if these verdicts are accepted

Primary labels per configuration (E has no flagged trials, so it is unchanged):

| Label | B0 | E | H0 | V | V-E |
|---|---|---|---|---|---|
| guardrail_blocked | 0 | 0 | 0 | 1 | 1 |
| unparsable_tool_call | 30 | 31 | 30 | 23 | 8 |
| premature_submit_missing_output | 5 | 0 | 3 | 1 | 4 |
| wrong_output | 3 | 5 | 4 | 10 | 19 |
| partial_credit | 1 | 0 | 1 | 2 | 2 |
| **Harness / model level** | 35 / 4 | 31 / 5 | 33 / 5 | 25 / 12 | 13 / 21 |

The headline doesn't change: as components are added, failures shift from harness-level (mostly unparsable tool calls) to model-level wrong outputs. Two findings that don't fit the taxonomy should go in the report:
- **Task 105's instruction is broken upstream.** It contains `{path}`, which affects every configuration equally.
- **V-E/089 fabricated evidence of success.** That is a model-level honesty failure, not just a missing output.
