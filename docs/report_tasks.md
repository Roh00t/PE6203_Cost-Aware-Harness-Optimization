# Report and Presentation Tasks: Tue 27 Oct → Sun 1 Nov

All code, runs and analysis are done and on `main`. What remains is the **report** and the **10-minute presentation** (plus 5 min Q&A). This file says who writes what, by when, and how.

**Report and presentation lead: Ulfa.** She owns the shared documents, the template, the outline and the final assembly. Rohit reviews everything after the deadline.

## Timeline

| When | What | Who |
|---|---|---|
| **Tue 27 Oct, tonight** | Shared Word report + PowerPoint deck set up in NTU OneDrive, edit links posted in the group | Ulfa |
| Tue 27 Oct, tonight | Roshan's branch merged into `main` (classifier and failure examples) | Rohit |
| **Wed 28 Oct, 23:59** | **Every section and every slide below written into the shared documents** | Everyone |
| Thu 29 – Fri 30 Oct | Rohit reads the whole report and deck; owners fix comments the same day | Rohit, then owners |
| **Sat 31 Oct** | **Mock presentation** (time set by Ulfa), timed to 10 min | Everyone |
| **Sun 1 Nov, 9:00** | **Presentation to the professor** | Everyone |

If you can't make your deadline, say so in the group the same day.

## How to work

1. **Pull the repo** so you have the final results: `git pull` (Windows) or `git switch main && git pull --ff-only` (Ubuntu).
2. **Use Claude to draft your part.** Open Claude Code in the repo folder and paste the prompt given under your name below. Read what it writes, check every number against the fact sheet, then paste it into the shared Word report and PowerPoint deck under your section.
3. **Only use numbers from the fact sheet** (or from `results/analysis/eval/rohit-eval-pass1/`). Don't round differently from the table, don't invent figures.
4. **Don't edit code, configs or results.** They are frozen; the report describes what was run.
5. **Mark your section done** in the shared document (e.g. "✓ Abin, Wed 28 Oct") so Ulfa can track progress.

## Fact sheet (the only numbers to use)

Sources: [`results/eval/rohit-eval-pass1/README.md`](../results/eval/rohit-eval-pass1/README.md), [`results/analysis/eval/rohit-eval-pass1/`](../results/analysis/eval/rohit-eval-pass1/) (`summary.csv`, `comparisons.csv`, `ablations.csv`, `trials.csv`, `pareto_include_lower_bounds.png`).

**Setup.** 40 eval tasks, 8 per family, from TUA-Bench commit `3497fd3`; frozen subset, fingerprint `973635ea…`. Base model gpt-oss-20b (Darkbloom), expensive model gpt-oss-120b (Venice), both via OpenRouter, reasoning effort low, max_tokens 8192. Prices: 20b $0.018 / $0.09 per M input/output tokens; 120b $0.03 / $0.15. One run per configuration (single run, as the brief allows). Task wall-clock limit 2,400 s for all. B0, E, H0 and the ablations without C3: no step or cost cap (stock defaults). C3, V: 50 steps, $0.01 per task; V-E: 50 steps, $0.0167 per task. Command timeout 30 s (stock), 180 s with C3. **A "run" = all 40 tasks.**

**Main results** (mean reward on 40 tasks; cost per run = 40 tasks; "≥" = lower bound because a few rate-limited calls have unknown cost):

| Config | Model | Mean reward | Family-reweighted | Cost per run | Prompt / completion tokens per run | Model calls |
|---|---|---|---|---|---|---|
| B0 (default harness) | 20b | 0.089 | 0.086 | $0.0286 | 1.19 M / 79 k | 449 |
| H0 (our loop, no components) | 20b | 0.131 | 0.145 | ≥ $0.0336 | 1.44 M / 84 k | 496 |
| **V (full harness)** | 20b | **0.164** | **0.143** | **≥ $0.0474** | 2.22 M / 84 k | 659 |
| E (expensive-model baseline) | 120b | 0.169 | 0.116 | $0.0558 | 1.56 M / 60 k | 514 |
| V-E (full harness, expensive model) | 120b | 0.260 | 0.219 | ≥ $0.0919 | 2.71 M / 71 k | 795 |

**Paired comparisons** (bootstrap over tasks, 95 % CI): V − B0 = +0.075 (+0.008 to +0.158); V − E = −0.004 (−0.113 to +0.107); V-E − B0 = +0.170 (+0.045 to +0.304); V-E − E = +0.091 (−0.013 to +0.203); E − B0 = +0.079 (−0.012 to +0.183); H0 − B0 = +0.042 (−0.008 to +0.108).

**Ablations** (each component alone on top of H0):

| Config | Component | Mean reward | Δ vs H0 (95 % CI) | Cost per run | Model calls |
|---|---|---|---|---|---|
| H0+C0 | Task-appropriate prompt | 0.166 (38 tasks) | +0.046 (0.000 to +0.110), paired on its 38 tasks (H0: 0.120 there), no losses | ≥ $0.0126 (38 tasks) | 247 (H0: 470 on the same 38 tasks) |
| H0+C1 | Context management | 0.079 | −0.052 (−0.143 to +0.029) | ≥ $0.0307 | 486 |
| H0+C2 | Tool interface + validation | 0.176 | +0.046 (−0.046 to +0.137) | ≥ $0.0763 | 945 |
| H0+C3 | Budget caps + awareness | 0.143 | +0.013 (−0.041 to +0.079) | $0.0307 | 487 |
| H0+C4 | Failure recovery | 0.118 | −0.012 (−0.092 to +0.063) | $0.0379 | 548 |
| H0+C5 | Pre-submission gate | 0.106 | −0.024 (−0.129 to +0.083) | $0.0444 | 564 |

**Cost breakdown.** Harness-made model calls: none ($0). Harness-injected prompt text (status lines, nudges, recovery and gate messages), estimated by character share: V ≈ $0.0061 per run (13 % of its cost), V-E ≈ $0.0126 (14 %), ablations $0–$0.0015 (H0 and H0+C0: $0). Format-error feedback, which the stock loop sends too, is not harness overhead and is reported separately: V ≈ $0.0021, V-E ≈ $0.0025. (Corrected 2026-10-27, `docs/bug_fixes.md` BF-34; the first figures, 17 % and 16 %, counted that feedback as harness text.) Unknown-cost calls (all HTTP 429 rate-limit rejections): H0 3, V 2, V-E 7, H0+C0 1, H0+C1 3, H0+C2 2.

**Pareto frontier** (`pareto_include_lower_bounds.png`, lower-bound costs admitted and labelled): B0 → H0+C3 → V → E → H0+C2 → V-E. Strict version (`pareto.png`): B0, H0+C3, E.

**Coverage.** 438 of 440 trials scored. Missing: H0+C0 on tasks 004 and 099 (Docker build credential error, infrastructure). Infrastructure failures were rerun and the failed attempts kept as evidence.

**Key messages** (use the same wording in report and slides):
1. Our full harness on the cheap model (V) clearly beats the default harness on the same model (B0) and matches the expensive model on the default harness (E) at a lower cost per run.
2. Weighted to the full benchmark's family mix, V (0.143) is ahead of E (0.116): E only succeeds in Scientific and Multimedia tasks.
3. The harness gain does **not** shrink with a stronger model: V-E − E (+0.091) is larger than V − B0 (+0.075).
4. The prompt (C0) is the clearest single gain and halves model calls; tool interface (C2) gains as much but doubles cost; context management (C1) hurts; the full harness gains less than C0 or C2 alone, so the positive components overlap. Only C0's interval excludes zero, and only just.
5. gpt-oss models often answer in plain text instead of calling a tool; that format failure dominates the default harness's losses and is what C0 and C2 target.

## Report outline and owners

Aim for about 12 pages plus appendices (Ulfa to confirm against the template). Each section header in the shared document carries the owner's name.

| § | Section | Owner | Brief requirement it covers |
|---|---|---|---|
| 1 | Introduction: problem, central question, our answer | Rohit | |
| 2 | Experimental setup: subset, oracle gate, models, prices, budgets and limits, baselines, single run, infrastructure incidents (C2 deadlock fix, B0/E install pin) | Rohit | Protocol, budget reporting |
| 3 | Harness architecture and wiring to Harbor | Abin | Codebase, wiring to the official runner |
| 4.1 | Components C0, C1, C3 | Abin | Optimization surface |
| 4.2 | Components C2, C4, C5 | Isha | Optimization surface |
| 5 | Guardrails and safety (rules, false-positive review, U-INT-05) | Isha | |
| 6 | Results: accuracy–cost plot with Pareto frontier, comparison with both baselines | Ulfa | **Accuracy–cost plot** |
| 7 | Component ablation table and reading | Roshan | **Component ablation** |
| 8 | Cost breakdown: tokens and dollars per run, agent inference vs harness overhead | Ulfa | **Cost breakdown** |
| 9.1 | Failure classification: classes, counts, harness- vs model-level | Roshan | **Failure classification** |
| 9.2 | Example trajectories, at least one per class | Asmitha | **Failure classification** examples |
| 10 | Discussion: which components account for the gain; does it shrink with a stronger model | Asmitha | **Discussion** |
| 11 | Conclusions, limitations, lessons learned | Rohit | |
| A | Reproduction: commands, configs, where the logs are | Roshan | Reproduction material |
| B | Price table and per-configuration limits | Ulfa | Cost accounting |
| C | Guardrail rules mapped to the course frameworks | Asmitha | |

## Slide outline and speakers (10 minutes, about 45 s per slide)

| # | Slide | Speaker |
|---|---|---|
| 1 | Title, team, the central question | Rohit |
| 2 | Setup: 40-task subset, models, budget, B0 and E baselines | Rohit |
| 3 | Harness architecture and how it plugs into Harbor | Abin |
| 4 | Components C0, C1, C3 | Abin |
| 5 | Components C2, C4, C5 | Isha |
| 6 | Guardrails and the false-positive we fixed | Isha |
| 7 | **Accuracy–cost plot** with Pareto frontier | Ulfa |
| 8 | Baseline comparison and cost breakdown | Ulfa |
| 9 | Component ablation | Roshan |
| 10 | Failure classes (harness- vs model-level) | Roshan |
| 11 | Representative failure trajectories | Asmitha |
| 12 | Discussion: what drives the gain, stronger model | Asmitha |
| 13 | Conclusions and lessons learned | Rohit |

Everyone also prepares one or two likely Q&A questions about their own part.

---

## Ulfa: report and presentation lead

**Today (Tue 27 Oct):**
1. Find a clean academic **Word report template** and **PowerPoint template** online (simple, readable, 16:9 slides).
2. Put both in your **NTU OneDrive**, set sharing to "People in NTU with the link can edit", and post both links in the group.
3. In the Word file, create the section headings from the report outline above, each with the owner's name; in the deck, create the 13 slide titles with the speaker's name in the notes.
4. Insert the two figures from `results/analysis/eval/rohit-eval-pass1/`: `pareto_include_lower_bounds.png` (main) and `pareto.png` (appendix).

**By Wed 28 Oct, 23:59:** your sections §6, §8 and Appendix B, slides 7 and 8.

**Thu 29 – Sat 31 Oct:** chase missing parts, make terminology and number formats consistent, apply Rohit's comments, run the mock presentation (set the time), export the final report to PDF.

**Prompt for Claude:**
> Read docs/report_tasks.md, results/eval/rohit-eval-pass1/README.md and results/analysis/eval/rohit-eval-pass1/summary.csv and comparisons.csv. Draft report §6 "Results: accuracy–cost" (about 500 words, with the accuracy–cost plot as the figure and the comparison table), §8 "Cost breakdown" (tokens and dollars per run, agent inference vs harness overhead, about 300 words with a table) and Appendix B (price table and per-configuration limits). Then draft bullet content and speaker notes for slides 7 and 8. Use only numbers from the fact sheet.

## Rohit

**Today:** merge Roshan's branch into `main` (`git merge origin/roshan/my-tasks`, then push).

**By Wed 28 Oct, 23:59:** §1, §2, §11; slides 1, 2, 13.

**Thu 29 – Fri 30 Oct:** read the full report and deck, leave comments for owners.

**Prompt for Claude:**
> Read docs/report_tasks.md, the brief (the PDF in the repo root), system_architecture.md §1–2 and §6–7, docs/model_selection.md, configs/subset_amendments.json and CLAUDE.md (the freeze exceptions). Draft report §1 Introduction (about 350 words), §2 Experimental setup (about 600 words: subset and oracle gate, models and prices, budgets and limits per configuration, baselines, single run, and the infrastructure incidents we fixed) and §11 Conclusions, limitations and lessons (about 350 words). Then draft slides 1, 2 and 13 with speaker notes. Use only numbers from the fact sheet.

## Abin

**By Wed 28 Oct, 23:59:** §3, §4.1; slides 3 and 4.

**Prompt for Claude:**
> Read docs/report_tasks.md, docs/harness_core.md, system_architecture.md §3–5, harness/agent.py, harness/loop.py, harness/components/context.py and harness/components/budget.py. Draft report §3 "Harness architecture and wiring to Harbor" (about 500 words, with a simple diagram description: Harbor → CostAwareAgent → HarnessAgent loop → OpenRouter gateway → container adapter) and §4.1 "Components C0, C1, C3" (about 450 words: what each does, its flag, its ablation result from the fact sheet). Then draft slides 3 and 4 with speaker notes.

## Isha

**By Wed 28 Oct, 23:59:** §4.2, §5; slides 5 and 6.

**Prompt for Claude:**
> Read docs/report_tasks.md, system_architecture.md §5 (C2, C4, C5), harness/components/tools.py, recovery.py, submit_gate.py, and guardrails.md (§3, §7.1 and §8). Draft report §4.2 "Components C2, C4, C5" (about 450 words: design, flag, ablation result from the fact sheet) and §5 "Guardrails and safety" (about 400 words: always-on vs C2 rules, the dev false-positive review that narrowed sudo to U-INT-05, the trust boundaries). Then draft slides 5 and 6 with speaker notes.

## Roshan

**By Wed 28 Oct, 23:59:** §7, §9.1, Appendix A; slides 9 and 10.

**Prompt for Claude:**
> Read docs/report_tasks.md, results/analysis/eval/rohit-eval-pass1/ablations.csv, results/eval/rohit-eval-pass1/README.md, scripts/classify_failures.py, results/analysis/eval/rohit-eval-pass1/failures/summary.csv and trials_classified.csv. Draft report §7 "Component ablation" (the ablation table from the fact sheet plus about 350 words of reading), §9.1 "Failure classification" (classes, counts per configuration, harness-level vs model-level, about 400 words) and Appendix A "Reproduction" (commands, configs, where the logs are). Then draft slides 9 and 10 with speaker notes.

## Asmitha

**By Wed 28 Oct, 23:59:** §9.2, §10, Appendix C (`docs/guardrails_framework_mapping.md` content); slides 11 and 12.

**Prompt for Claude:**
> Read docs/report_tasks.md, results/analysis/eval/rohit-eval-pass1/failures/examples.md, docs/failure_catalog_inputs.md, results/eval/rohit-eval-pass1/README.md, guardrails.md §8 and the lecture notes docs/Week08_Tools.md, docs/Week10_Harness.md, docs/Week12_Industry_Applications.md. Draft report §9.2 "Example trajectories" (at least one harness-level and one model-level example, each with task, configuration, what happened step by step and why it failed, about 450 words), §10 "Discussion" (which components account for most of the gain; whether the gain shrinks with the stronger model: compare V − B0 with V-E − E; about 450 words) and Appendix C (each guardrail rule mapped to the lecture frameworks and OWASP 2025). Then draft slides 11 and 12 with speaker notes.

---

## Definition of done (Wed 28 Oct, 23:59)

- [ ] Every section in the outline exists in the shared report, with its owner's ✓.
- [ ] Every slide 1–13 has content and speaker notes.
- [ ] Every number matches the fact sheet; costs say "per run (40 tasks)".
- [ ] The accuracy–cost plot, the ablation table, the cost breakdown, the failure classes with examples, and the discussion are all present (the five items the brief requires).
- [ ] Links to the repo (`results/`, configs, commands) are in Appendix A.
