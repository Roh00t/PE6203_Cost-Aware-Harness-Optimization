PE6203 CA2 · Group Project 5 · TUA-Bench

# Cost-Aware Harness Progress

Status as of **Wed 14 Oct 2026** Team target **before Sat 24 Oct** (10 days) Team **Rohit, Abin, Isha, Ulfa** Model spend so far **≈ $0.18** of \~$8

Overall, weighted by effort

49.5%

Models and budget are frozen. The harness core is on main with C1, C3 and the guardrails, and the C0 prompt, all 11 configurations and the experiment runner are written. Left before the Fri 16 freeze: C2, C4, C5, the cost collector, and live checks on the dev tasks. Step-by-step instructions for everyone: docs/tasks.md.

Weighted effort done (49.5%)Remaining

## Workstreams

| Workstream | Status | Weight | Done |
| --- | --- | --- | --- |
| **1. Benchmark subset**40 eval + 10 dev tasks, 8 + 2 per family. Frozen Sat 10 after 4 oracle-gate swaps; final eval fingerprint 973635ea… | frozen | 8% | 100% |
| **2. Run infrastructure**Pinned Harbor 0.6.3, per-task runner with all checks, Windows/WSL2 support, amended task lists. New: run_all_configs.py runs any set of the 11 configurations task by task with a shared spend cap, and the leak check now runs before every paid run | done | 10% | 100% |
| **3. Design documents**Architecture now records the frozen models and the $0.01 budget. Open: guardrails §8 from the lecture slides. | in progress | 10% | 90% |
| **4. Oracle gate**Dev 9/10 (one upstream bug). Eval 40/40 settled on Mac + x86. | done | 5% | 100% |
| **5. Model choice and price table**Frozen Tue 13: gpt-oss-20b on Darkbloom (base), gpt-oss-120b on Venice (expensive). pricing.json, model configs, dev pilots with 3 candidates | frozen | 5% | 100% |
| **6. Harness implementation**Done: Harbor agent, loop with hooks, container adapter, OpenRouter gateway and call logging, C1, C3, guardrails, leak check, C0 prompt, all 11 configs (60 offline tests pass). Open: C2, C4, C5, and live checks on dev (H0 vs B0) | in progress | 25% | 50% |
| **7. Baselines B0 and E**Stock mini-swe-agent 2.4.6 with default settings. Dev pilots done; eval runs start Fri 16 | not started | 5% | 0% |
| **8. Experiment runs**11 configurations × 40 tasks, 10 tasks per laptop, Fri 16 – Mon 19 | not started | 12% | 0% |
| **9. Analysis and report**Cost collector prototype exists; analysis, Pareto plot, ablation table and report to come | not started | 15% | 0% |
| **10. Presentation**10 minutes plus 5 of Q&A, Fri 23 | not started | 5% | 0% |

Overall = sum of weight × done. Weights are estimates of relative effort, not hours.

## Harness components

Each component sits behind its own switch so it can be measured alone. Configuration files are in configs/harness/.

| Part | What it does | Owner | Status |
| --- | --- | --- | --- |
| **Core** | Host-side loop, container adapter, OpenRouter gateway with per-call cost logging, guardrail hook | Abin | built · live check Thu 15 |
| **C0** prompt | Task-appropriate prompt. v3 targets the pilot's failure: every response must end in one tool call, and the submit call is the only way to finish | Rohit | written |
| **C1** context | Long outputs saved to a file in the container with head and tail shown; older steps condensed | Abin | built · live check Thu 15 |
| **C2** tools | read_file, write_file, edit_file, search; argument checks; clearer format-error messages | Isha | due Thu 15 |
| **C3** budget | 50 steps and $0.01 per task, status line, nudges at 70% and 90%, 180 s command timeout | Abin | built · live check Thu 15 |
| **C4** recovery | Blocks a command that already failed twice, nudges on repeated output, recipe after a timeout | Isha | due Thu 15 |
| **C5** submit gate | Holds the first submit once: checks the output files the task names, asks the model to confirm each requirement | Isha | due Thu 15 |
| **Guardrails** | 16 rules (7 always on, 9 with C2), task-leak check before paid runs | Isha | on main |

## Next steps and open decisions

Abin · due Thu 15 · about $0.05

### Live check: H0 against B0 on the 10 dev tasks

Run B0 and H0 side by side with run_all_configs.py, compare reward, how each run ended, steps and cost per task, then C1 and C3 alone. For C3, note where runs stop: the $0.01 cap is expected to end long runs a few steps before 50. Steps in docs/tasks.md part 1.

Isha · due Thu 15

### C2, C4 and C5 as three plugins

Branch from fresh main. File names are fixed because the configs already point at them: harness/components/tools.py, recovery.py, submit_gate.py, each with build_hook. Done when check_harness.py --config configs/harness/V.yaml prints OK. Steps in docs/tasks.md part 2.

Ulfa · collector Thu 15

### Cost collector reads the harness logs

collect_costs.py must read the harness's calls.jsonl, where failed calls have usage null: count them, don't drop them. Its totals must match the harness's own numbers on Abin's H0 run. Then analyze.py and plot_pareto.py. Steps in docs/tasks.md part 3.

Team decision · Ulfa proposes

### How to report calls with unknown cost

A failed API call may still be billed but reports no token usage. Proposal to agree: report those trials' cost as a lower bound and say how many there are.

Rohit · Thu 15 – Fri 16

### Merge, test V, freeze

Review and merge C2/C4/C5, run V on two dev tasks, then tag harness-v1 on Fri 16 morning and post the run schedule: 10 eval tasks per laptop, each with its spend cap.

Settled Tue 13 · Ulfa, Rohit

### Models and per-task budget

gpt-oss-20b (base) and gpt-oss-120b (expensive), each pinned to one provider. Our variants get 50 steps and $0.01 per task, sized so 50 steps of about 11,000 prompt tokens fit; V-E gets $0.0167, the same tokens at 120b prices. A multiple of B0's spend was rejected: B0 mostly stops early on format errors ($0.00019 median), so it would cap our variants after a few steps.

Team rule

### One OpenRouter key per person, each with a credit limit

Post in the group before any paid run: what, how many tasks, expected cost.

## Model pilot · 10 dev tasks, stock baseline

Stock mini-swe-agent 2.4.6 (B0) with each candidate, single runs on the dev tasks. Cost from the frozen price table.

| Model · provider | Mean reward | Cost, 10 tasks | Submitted | Decision |
| --- | --- | --- | --- | --- |
| **gpt-oss-20b** · Darkbloom | 0.200 | $0.0063 | 2/10 | base |
| **gpt-oss-120b** · Venice | 0.366 | $0.0110 | 0/10 | expensive |
| **Qwen3-Coder-30B** · SiliconFlow | 0.319 | $0.1592 | 10/10 | rejected: 25× the cost |

The main finding: gpt-oss often finishes with plain text or a markdown block instead of a tool call, so the stock harness stops with RepeatedFormatError. B0 and E keep that behaviour (it's the default harness); our C0 prompt and C2 are built to fix it, which gives the harness a clear, measurable target.

Eval oracle gate · 40 of 40 settled (Sat 10)

**31** passed on the first try **4** swapped, replacements pass **3** kept: reference-solution bug **2** kept: similarity metric

### Swapped for the next reserve in the family

0.0

032-compare-iphones → 077-corresponding-scholar-urlApple redirects the iPhone compare page to its home page.

0.0

042-black-sale-coffee-makers → 039-manchester-forecastGoogle Shopping no longer shows the filter chips the grader checks.

0.0

046-restore-tripadvisor-tab → 113-add-folders-workspaceEvery site times out, and Airbnb redirects to .com.sg.

0.0

069-linux-ls-tutorial → 071-paste-image-docxThe grader's OCR reads a clean "ls" image as empty, on Mac and x86.

### Kept below reward 1

0.0

004-place-heater-for-sensorsReference solution reads grader files that arrive only after the agent finishes. Agents can solve it.

0.0

019-prostate-red-overlaySame reference-solution bug as 004.

0.0

110-rotate-macintosh-videoReference flips both ways; the expected video is only flipped vertically. Agents can pass.

0.83

111-set-video-wallpaperImage-similarity grader, never exactly 1.

0.85

112-capture-video-frameImage-similarity grader, never exactly 1.

Causes and evidence: configs/subset_amendments.json. Logs: results/oracle-gate/. Dev oracle check: 9 of 10, the one failure (100-name-mountain-photos) is an upstream grader bug.

## Plan to 24 October

Sat 10 – Tue 13 Oct

### Foundations

Oracle gate done and subset frozen (Sat 10). Model pilot, price table, model pair and budget frozen (Tue 13).

Mon 12 – Thu 15 Oct

### Build the harness

Core, C1, C3, guardrails, C0, configs and runner done. Thu 15: C2, C4, C5, live H0 check on dev, cost collector.

Fri 16 Oct

### Freeze harness v1

V smoke test on dev, guardrail false-positive review, tag harness-v1, post the run schedule. No harness, prompt or config changes after this.

Fri 16 – Mon 19 Oct

### Eval runs

About 440 trials (11 configurations × 40 tasks). Split by task, never by configuration: 10 tasks per laptop, all 11 configurations each, Scientific tasks on the machines with the most memory. Export and push logs by Mon 19.

Mon 19 – Thu 22 Oct

### Analysis and report

Costs from the price table, Pareto plot, ablation table, cost breakdown, failure classification with example trajectories.

Thu 22 – Fri 23 Oct

### Presentation

10-minute deck and a run-through.

## Team and roles

Full step-by-step instructions, commands and "done when" checks for each person: docs/tasks.md in the repo.

Rohit: subset frozen **Sat 10 ✓** Ulfa: models, B_task frozen **Tue 13 ✓** Abin: core and hooks **Wed 14 ✓** Abin: live H0 check **Thu 15** Isha: C2, C4, C5 **Thu 15** Rohit: harness v1 frozen **Fri 16** All four: eval runs **Fri 16 – Mon 19** Ulfa: analysis **Mon 19 – Wed 21** All four: report **to Thu 22**, presentation **Fri 23**

Every link waits on the one before it. A slip anywhere on this chain moves the eval runs, so flag it in the group chat the same day.

Lead

### Rohit · Infrastructure and integration

Owns the benchmark setup, the run tooling, the agent prompt and the final integration. Makes the freeze calls. Leads the report's framing and the presentation.

| When | Task | Effort |
| --- | --- | --- |
| Sat 10 | Eval oracle gate, swaps, subset frozen | 3 h + 2 h machine |
| Wed 14 | C0 prompt v3, all 11 harness configs, run_all_configs.py with tests, docs updated for the frozen budget, docs/tasks.md | 4 h |
| Thu 15 | Review Abin's validation and Isha's branch, merge C2/C4/C5, V smoke test on 2 dev tasks (≈ $0.01) | 3–4 h |
| Fri 16 | Freeze: tag harness-v1; run schedule with 10 tasks and a spend cap per laptop | 2 h |
| Fri 16 – Mon 19 | Own share of the eval runs | 1 h + 3–5 h machine |
| Mon 19 – Thu 22 | Report: introduction, method, conclusions; final edit | 6 h |
| Thu 22 – Fri 23 | Presentation deck and rehearsal | 5 h |

Waiting on

**Isha** (C2/C4/C5, Thu 15) and **Abin** (live H0 check, Thu 15) before the freeze.

Also

Send the lecture slides to Isha for guardrails §8.

Critical path

### Abin · Harness core

Owns the code everything else plugs into: the Harbor agent, the bridge into the task container, the model gateway and its logs, H0, and the context and budget components.

| When | Task | Effort |
| --- | --- | --- |
| Mon 12 – Wed 14 | Harbor agent, loop with hooks, config loader, prompt renderer, container adapter, OpenRouter gateway with call logging, C1, C3, guardrail integration, leak gate, 41 tests | 20 h |
| Thu 15 | Live check: B0 and H0 on the 10 dev tasks, compare per task; then C1 and C3 alone, note where C3 stops; export logs and post the table | 3–4 h + 2 h machine |
| Thu 15 – Fri 16 | Help integrate C2/C4/C5; fix what the V smoke test finds | 2–4 h |
| Fri 16 – Mon 19 | Own share of the eval runs | 1 h + 3–5 h machine |
| Mon 19 – Thu 22 | Report: harness design and how it wires into Harbor | 4 h |

Needs

Nothing: the configs and runner are ready. About $0.05 of model spend; post in the group first.

Safety

### Isha · Safety, recovery and verification

Owns what the harness blocks, checks and recovers from: the guardrail rules, the tool interface, failure recovery, the submit gate and the integrity checks. Writes the safety and failure-analysis parts of the report.

| When | Task | Effort |
| --- | --- | --- |
| Sat 10 – Tue 13 | Guardrails (16 rules with tests) and the task-leak check | 7 h |
| Wed 14 – Thu 15 | C2 tools and validation (tools.py), C4 recovery (recovery.py), C5 submit gate (submit_gate.py), with tests | 8–10 h |
| Thu 15 | Dev smoke test of C2, C4, C5 alone on 2 tasks (≈ $0.02) | 1 h |
| Thu 15 – Fri 16 | False-positive review of every guardrail block in the dev logs; narrow rules | 2–3 h |
| When the slides arrive | guardrails §8: map the rules to the lecture frameworks | 2 h |
| Fri 16 – Mon 19 | Own share of the eval runs | 1 h + 3–5 h machine |
| Mon 19 – Thu 22 | Report: guardrails, failure classification with example trajectories | 5–6 h |

Needs

Start from fresh main, not isha/guardrails. Hook contract: docs/harness_core.md.

Waiting on

**Abin**'s dev logs for the false-positive review. **Rohit**: lecture slides.

Numbers

### Ulfa · Experiments, cost and analysis

Owns the money and the numbers: the price table, the model choice, the per-task budget, cost accounting, the statistics and every figure and table in the results section.

| When | Task | Effort |
| --- | --- | --- |
| Mon 12 – Tue 13 | Price table, cost collector prototype, pilots with 3 models, model pair frozen | 8 h + machine |
| Wed 14 – Thu 15 | collect_costs.py reads the harness calls.jsonl, handles unknown usage, matches the harness's own totals on Abin's H0 run | 3–4 h |
| Thu 15 – Sun 18 | analyze.py (paired bootstrap, family reweighting, ablation table) and plot_pareto.py, built on dev data | 6–8 h |
| Ongoing | Budget ledger across everyone's keys; warn the group at 70% of the $8 | 1 h |
| Fri 16 – Mon 19 | Own share of the eval runs | 1 h + 3–5 h machine |
| Mon 19 – Thu 22 | Collect all runs, Pareto plot, ablation table, cost breakdown, results section | 8–10 h |

Waiting on

**Abin**: first real H0 logs (Thu 15) to test the collector. **Everyone**: eval logs (Mon 19).

## Budget and time

Model spend≈ $0.18All on Ulfa's dev pilots; $0.16 of it was the rejected Qwen model

Capped configs, eval≤ $1.47Most H0+C3, V and V-E can spend over 40 tasks ($0.40 + $0.40 + $0.67)

Uncapped configsmeasure ThuB0, E, H0 and the five ablations without C3 have no cap by design. The pilot suggests cents per 40 tasks; Abin's dev runs give the real figure

Docker memory10 GBScientific tasks need 8 GB each, so one trial at a time on 16 GB laptops

Built from main at 757f71a (harness core and guardrails) plus Rohit's Wed 14 changes: C0 prompt v3, configs/harness/, scripts/run_all_configs.py, docs/tasks.md. Details: docs/STATUS.md, docs/tasks.md, docs/harness_core.md, docs/model_selection.md.