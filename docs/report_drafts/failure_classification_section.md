# Draft: Failure classification (report §9)

Drafted by Asmitha, 2026-10-27, for Isha to edit. `docs/report_tasks.md` splits this material into §9.1, classes and counts (Roshan), and §9.2, examples (Asmitha).
- Asmitha's own section is `docs/report_drafts/9.2_example_trajectories.md`.
- This file covers all of §9 and is offered as input for Roshan's §9.1.

**Caveats on the numbers.**
- The counts cover **pass 1 only** (B0, E, H0, V, V-E). The committed `failures/` outputs were not rerun on the six ablation configurations.
- The `RepeatedFormatError` counts (32/40, 12/38, 24/40, 12/40) are not on the fact sheet. They were counted from the committed trajectories (see `docs/report_drafts/10_discussion.md`).

Sources:
- `results/analysis/eval/rohit-eval-pass1/failures/summary.csv` (counts);
- `docs/failure_catalog.md` (cases);
- `docs/guardrail_eval_review.md` (guardrail events).

Body length is about 580 words, excluding the tables.

---

## 9 Failure classification

The brief defines two failure types:
- **Harness-level failures**: "premature termination, truncated or lost context, unparsable tool calls, or no retry after a recoverable error".
- **Model-level failures**: "a wrong plan, misuse of a domain-specific tool, or a task beyond the capability of the base model".

We label every failed trial of pass 1 (B0, E, H0, V, V-E; 40 tasks each) with a deterministic rule table (`scripts/classify_failures.py`). The first matching rule gives the primary label.

The harness-level labels are:
- `guardrail_blocked`: a guardrail block precedes the failure;
- `unparsable_tool_call`: the trial ended in `RepeatedFormatError`;
- `budget_exhausted`: a step, cost or time cap was hit;
- `timeout_no_recovery`: a command timeout with no recovery afterwards;
- `premature_submit_missing_output`: submitted while the verifier reports a required output missing.

The model-level labels are:
- `wrong_output`: submitted, and the verifier rejects the content;
- `partial_credit`: reward strictly between 0 and 1.

Trials whose verifier prints no reason are `unclassified` and were reviewed by hand. The 28 archived infrastructure attempts are excluded.

| Primary label | Type | B0 | E | H0 | V | V-E |
|---|---|---|---|---|---|---|
| Success (reward 1) | | 1 | 4 | 2 | 3 | 6 |
| `guardrail_blocked` | harness | 0 | 0 | 0 | 1 | 4 |
| `unparsable_tool_call` | harness | 30 | 31 | 30 | 23 | 7 |
| `budget_exhausted` | harness | 0 | 0 | 0 | 0 | 0 |
| `timeout_no_recovery` | harness | 0 | 0 | 0 | 0 | 0 |
| `premature_submit_missing_output` | harness | 1 | 0 | 2 | 1 | 2 |
| `wrong_output` | model | 2 | 5 | 1 | 7 | 10 |
| `partial_credit` | model | 1 | 0 | 1 | 2 | 2 |
| Unclassified (verifier silent) | | 5 | 0 | 4 | 3 | 9 |
| **Harness / model** | | **31 / 3** | **31 / 5** | **32 / 2** | **25 / 9** | **13 / 12** |

With the provisional manual verdicts for the 26 flagged trials (`manual_review.md`, pending review), the splits become:

| | B0 | E | H0 | V | V-E |
|---|---|---|---|---|---|
| Harness / model | 35 / 4 | 31 / 5 | 33 / 5 | 25 / 12 | 13 / 21 |

**What the counts show.** On the default harness, failures are almost entirely harness-level. In 30–31 of 40 trials on B0, E and H0, the run ended because gpt-oss replied without a valid tool call: mostly plain text, sometimes malformed arguments. The stock loop stops after three such replies in a row. In the shortest case, B0 on the Delta flight task (040), the model replied three times that it does not "have the ability to interact with a live web browser", and the run ended before any command ran.

Our components shrink this class: `RepeatedFormatError` endings fall from 32/40 (H0) to 12/38 with the prompt alone (C0), 24/40 in V and 12/40 in V-E. As they shrink, model-level failures become the larger share. For V-E they are about half of all failures by the script's labels, and most of them after manual review. No trial failed on a step or cost cap. The only cap hit (V/088, step 50) scored 1.0.

**Model-level example.** On task 115, V-E's agent was asked to remove VS Code's `ctrl+f` Explorer binding. It wrote an empty `keybindings.json`, read it back, and submitted. The verifier expects a removal rule (`"command": "-list.find"`), which is VS Code knowledge the model lacked. E and V fail the same way. Here the harness worked as intended: the output was written, checked and submitted. No generic component can supply the missing knowledge.

**Harness-induced failures.** The harness can also cause failures, and we report this as a harness-level result. C2's heredoc rule (U-FMT-03) blocked 13 commands across all configurations, and all 13 were valid bash: heredocs nested in `bash -c "…"`, and Ruby's `<<` operator read as a heredoc. On V/071 it rejected a correct python-docx command five times with "heredoc 'PY' is never closed", while H0, with no such rule, solved the task.

We do not claim the guardrail alone caused that failure. The blocked commands also pointed at a non-existent input file, and H0+C2 failed the task without any block. In V-E/015 the agent got past all six blocks, and failed because it used an OpenStudio API that does not exist.

If every affected trial had otherwise succeeded, V would gain at most 0.025 and V-E at most 0.05. Both would rise, so the headline comparisons are conservative. The rule's false positives were not caught in the dev review because no dev trial produced these patterns.

---

## Slide bullets (slide 11, Asmitha)

- **Default harness: the model rarely gets to the task.** gpt-oss replies in plain text, and stock mini-swe-agent quits after 3 format errors: 30 of 40 B0 trials end this way.
- **Full harness: what's left is mostly the model.** Wrong plans, a non-existent tool API and missing domain knowledge (V-E/115: an empty `keybindings.json` instead of a `-list.find` removal rule). No generic harness fix exists for these.
- **Our guardrail produced false positives.** U-FMT-03 rejected 13 valid commands as unterminated heredocs. We report this as a harness-level failure: at most +0.025 for V if fixed.
