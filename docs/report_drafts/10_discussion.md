# Draft: Report §10 Discussion

Asmitha, 2026-10-27. This is the draft for the shared report, about 540 words against a target of about 450. If space is short, cut the last paragraph first; §11 also covers limitations.

**Number sources.**
- All reward, cost and confidence-interval figures are from the fact sheet in `docs/report_tasks.md` (from `results/analysis/eval/rohit-eval-pass1/`).
- The `RepeatedFormatError` counts are **not** on the fact sheet. I counted them from the committed trajectories (`info.exit_status` in `results/eval/rohit-eval-pass1/<config>/*/*/agent/mini-swe-agent.trajectory.json`, archived attempts excluded). Rohit to confirm before they go in.
- Relative gains are simple arithmetic on fact-sheet means. The six ablation deltas sum to +0.016 (`ablations.csv`, unrounded).
- H0's 470 calls on C0's 38 tasks are summed from `results/analysis/eval/rohit-eval-pass1/trials.csv`. The overhead and feedback figures are the `harness_injected_cost_usd_estimate` and `format_error_feedback_cost_usd_estimate` columns of `summary.csv` in the same folder.
- "Compaction never triggered": there are 0 `compaction` events in any `events.jsonl` in `results/eval/rohit-eval-pass1/`.
- The overhead figures are the corrected ones (`docs/bug_fixes.md` BF-34): the first estimate (17 %) also counted the stock format-error feedback as harness text.

---

## 10 Discussion

**Which components account for the gain?** Mainly two.

The task-appropriate prompt (C0) is the clearest. It adds +0.046 over H0 (95 % CI 0.000 to +0.110, paired over the 38 tasks both completed), with no task lost, and it needs about half the model calls (247 against H0's 470 on the same tasks). That also makes it the cheapest configuration per task. It works because gpt-oss often answers in plain text instead of calling a tool, and the stock loop stops after three such replies. That ended 32 of 40 H0 trials, but only 12 of 38 with C0.

The tool interface (C2) gains as much (+0.046, CI −0.046 to +0.137) at about twice H0's cost (≥ $0.0763 against ≥ $0.0336 per run), because its longer format-error allowance keeps failing runs going.

C3 is roughly neutral (+0.013). C1 (−0.052), C4 (−0.012) and C5 (−0.024) are slightly negative on their own. Only C0's interval excludes zero, and only just.

The positive components overlap. The full harness V gains +0.033 over H0, less than C0 or C2 alone, though more than the sum of all six single-component changes (+0.016). With one run per configuration we cannot separate interaction from noise.

Some of the shortfall may be harness-induced. C5's checklist marked existing files as missing (35 of 46 ✗ lines in V and V-E were false), and C2's heredoc rule blocked 13 valid commands (§9.2). C1's drop is unexplained. Its compaction step never triggered in eval, so its effect came from output offloading and shortening alone.

**Does the gain shrink with a stronger model?** Not in absolute terms. On the cheap model V − B0 = +0.075 (CI +0.008 to +0.158); on the expensive one V-E − E = +0.091 (CI −0.013 to +0.203). Relative to each baseline the gain is smaller (+84 % on 20b, +54 % on 120b), and the intervals overlap widely. The honest reading is that we see no sign of the gain shrinking, not that it grows.

This fits the failure analysis. gpt-oss-120b has the same format problem on the stock harness: 33 of 40 E trials ended in `RepeatedFormatError`, against 12 of 40 for V-E. So C0 and C2 have as much to fix on the stronger model. Once they do, its capability shows: V-E has the highest reward (0.260) and the most model-level failures of any configuration (§9).

**Can harness engineering substitute for model spending?** On this subset, largely yes. V matches E (V − E = −0.004, CI −0.113 to +0.107) at a lower cost per run (≥ $0.0474 against $0.0558). Weighted to the full benchmark's family mix, V is ahead (0.143 against 0.116), because E succeeds only in Scientific and Multimedia tasks.

The harness makes no model calls of its own. The prompt text it injects is estimated at about 13 % of V's spend ($0.0061 per run). Format-error feedback, which the stock loop sends too, is counted separately ($0.0021).

These conclusions rest on one run per configuration over 40 tasks. Most comparisons are ties, and costs marked "≥" are lower bounds. Fixing the guardrail false positives could only raise V (by at most 0.025) and V-E (by at most 0.05).
