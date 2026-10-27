# Draft: Slides 11 and 12 (Asmitha)

Asmitha, 2026-10-27. Content and speaker notes for the shared deck. Each slide gets about 45 seconds, so each set of notes is about 110 words. Numbers come from the fact sheet in `docs/report_tasks.md`, with three exceptions:
- the `RepeatedFormatError` counts, counted from the committed logs;
- H0's 470 calls on C0's 38 tasks, summed from `results/analysis/eval/rohit-eval-pass1/trials.csv`;
- the 13 U-FMT-03 false positives, from `docs/guardrail_eval_review.md`.

`docs/report_drafts/10_discussion.md` lists the sources in full.

---

## Slide 11: Representative failure trajectories

**Title:** Where runs fail: harness vs model

**Content (three panels):**

| Harness-level | Model-level | Harness-induced |
|---|---|---|
| **B0 · Delta flights (040)** | **V-E · VS Code shortcut (115)** | **V · image to .docx (071)** |
| 3 plain-text replies, no tool call → stock harness quits (`RepeatedFormatError`) | Wrote `[]` to `keybindings.json`, checked it, submitted; the task needs a `-list.find` removal rule | Valid heredoc rejected 5× as "never closed" by our own rule U-FMT-03 |
| 30 of 40 B0 trials end this way | E and V fail identically | 13 of 13 U-FMT-03 blocks were false positives |

**Speaker notes:**
> Three trajectories show the three kinds of failure we found. On the left is the default harness: the model never calls a tool and just apologises in plain text, so stock mini-swe-agent stops after three tries. Thirty of the forty B0 trials end like this, before the task even starts. In the middle, our full harness works perfectly: the file is written, checked and submitted. But the model doesn't know that VS Code removes a default shortcut with a minus rule, so it fails, and so does every other configuration. On the right, our own validation rule rejected a valid command five times. We report that honestly as a harness-level failure.

---

## Slide 12: Discussion

**Title:** What drives the gain, and does it last with a stronger model?

**Content:**
- **The prompt (C0) is the clearest gain:** +0.046 over H0, no losses, about half the model calls (247 vs 470 on the same 38 tasks).
- **The tool interface (C2) gains as much,** at about twice the cost. C1, C4 and C5 alone are slightly negative. All together, V gains +0.033 over H0: less than C0 or C2 alone.
- **The gain does not shrink with the stronger model:** V − B0 = +0.075, V-E − E = +0.091. The intervals overlap, so this is "no sign of shrinking".
- **The cheap model plus our harness matches the expensive model:** V − E = −0.004 at lower cost per run (≥ $0.0474 vs $0.0558). On the family-reweighted score, V is ahead (0.143 vs 0.116).

**Speaker notes:**
> Most of the gain comes from two components. The task-appropriate prompt adds about five points, loses no task, and halves the number of model calls, because it stops the model answering in plain text. The tool interface gains as much, but doubles the cost. The other components don't help on their own, and the full harness gains less over H0 than the prompt alone, so the gains overlap. Does the gain shrink with a stronger model? We see no sign of it: on 120b the harness adds 9 points, against 7.5 on 20b, though the intervals are wide. The bottom line: gpt-oss-20b with our harness matches 120b on the default harness at lower cost, and is ahead of it when weighted to the benchmark's full task mix.
