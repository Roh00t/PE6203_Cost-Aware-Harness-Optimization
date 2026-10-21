# Recovery Plan: Tue 20 → Fri 23 October

Drafted 2026-10-20 by Rohit. It replaces the dates in [`docs/tasks.md`](tasks.md) from today; the step-by-step instructions there still apply.

## Update Wed 21, evening: harness validated, handoff

- **Issue #2 fixed.** The "C2 hangs on the Mac" problem was a deadlock in the code (it hung on every machine): C2 uploaded its helper while the plugin was built on Harbor's event-loop thread. Fixed, with regression tests and a 600 s per-request timeout. Details in `CLAUDE.md`.
- **Live smoke test passed** on Rohit's Windows laptop: C2, C4, C5, V and V-E on dev tasks 020 and 106, 11 trials, no hangs or exceptions, every component's events seen, about $0.02.
- **Guardrail false positive fixed.** U-INT-04 blocked a correct `sudo useradd …`; `sudo` is now logged (U-INT-05), `ssh`/`scp` without BatchMode still blocked.
- **104 offline tests pass.** The eval runs use `main` from this commit on.
- **Darkbloom rate limits are heavy** (up to 14 of 36 calls in one trial): stagger start times by 15+ minutes and rerun infrastructure errors.

| Who | Remaining work |
|---|---|
| Abin | Lead the overnight eval runs (passes 1 → 3 below) and monitor them: rate limits, infrastructure errors, reruns, exports |
| Ulfa | `collect_costs.py`: handle `null` usage (`n_unknown_calls`, `usage_complete`, cross-check with `known_cost_table_usd`; rewrite `tests/test_collect_costs.py`, which still expects a raise); then `scripts/analyze.py` and `scripts/plot_pareto.py` |
| Isha | Final test-suite run on `main`, guardrail documentation (`guardrails.md` §7 false-positive record including U-INT-05, §8 with Asmitha), guardrails section of the report |
| Roshan | Tests for the run tooling (`tests/test_task_list.py`, `tests/test_export_run.py`, …) and `scripts/classify_failures.py` |
| Asmitha | `docs/guardrails_framework_mapping.md` (lecture slides in `docs/Week07…Week12`) and the failure trajectory catalog (`docs/failure_catalog.md`) |
| Rohit | Report framing, final edit, presentation; reachable for decisions only |

**Where we are.** The harness is complete and passes the offline suite (99 tests); V and V-E pass the integration check; the subset, models and budget are frozen. Not done yet: a live run of the full harness on dev, the `harness-v1` freeze, and any eval-split model run. The report is due **Thu 22** and the presentation is **Fri 23**.

**What limits us.** Machine time, not money. Measured so far: the first image build of a task takes about 4–7 minutes (about 1 minute once cached), and agent time is about 1–2 minutes per trial. A trial costs about $0.001, so all 440 eval trials are about $1–2.

---

## Two changes that make this feasible

1. **No separate dev parity run.** Architecture §10.2 defines parity as B0 vs H0 *on the eval split*, and both are among the 11 eval configurations anyway. We check it on the first finished eval tasks on Wednesday morning and report it either way. This saves a day.
2. **Three passes, most important configurations first.** If time runs out, we lose the least important ablations, never the headline comparison. Each pass runs task by task and resumes when rerun with the same run name.

| Pass | Configurations | Why this order |
|---|---|---|
| 1 | B0, E, H0, V, V-E | Headline result, parity check, and whether the gain shrinks with a stronger model |
| 2 | H0+C5, H0+C4, H0+C1 | The components expected to matter most |
| 3 | H0+C0, H0+C2, H0+C3 | The remaining ablations |

**Time estimate.** About 55 machine-minutes per task for all 11 configurations, about 37 machine-hours in total. Spread across **6 machines** (Rohit's Mac and Windows laptop, Abin, Isha, Ulfa, plus Roshan or Asmitha once set up), that's about **6–7 hours each: one overnight run.**

---

## Tuesday 20: freeze by the evening

| When | Who | What | Done when |
|---|---|---|---|
| Morning | Isha | Finish the test-suite run and report the result | Suite passes; Rohit lifts the code freeze in `CLAUDE.md` |
| Morning | Everyone | Post laptop specs in the group: OS, RAM, Docker memory, free disk | Rohit has every machine's specs |
| Midday | Rohit | Smoke test on the Mac, which has the TUA-Bench checkout: C2, C4, C5 and V on two dev tasks (8 trials, ~40 min, ~$0.02) | Each component's events appear in `events.jsonl`; V completes without crashing |
| Afternoon | Abin, Isha | Fix anything the smoke test finds | Re-test passes |
| Afternoon | Roshan, Asmitha | Laptop setup ([STATUS.md §5](STATUS.md#5-setting-up-a-laptop), ~40 min), then the free smoke test on task `106` | Reward 1.0 |
| ~18:00 | Rohit | **Freeze:** tests and leak check pass, then `git tag harness-v1 && git push --tags` | Tag on GitHub |
| ~18:00 | Rohit | **Run schedule:** about 7 tasks per machine; job cap `--job-budget-usd 1.00` per machine (rules below) | Schedule posted in the group |
| Evening | Everyone | Start passes 1 → 2 → 3 overnight (commands below). Laptop plugged in, sleep disabled. Stagger start times by ~15 minutes | Runs going on every machine |

**Decision point, Tue 20:00.** If a component still fails its smoke test, freeze without it. Its ablation row is reported as "not run", and V runs without it, with the reason documented. We don't delay everything for one component.

### Run schedule rules

- The 9 eval tasks that need 8 GB (`000`, `004`, `006`, `008`, `011`, `015`, `019`, `075`, `114`) go only to machines with **≥ 10 GB of Docker memory**. Abin's laptop has 7.8 GB, so it gets light tasks only. Nobody uses the memory-check override.
- Browser tasks go to x86 laptops, not the Mac, because Chrome under emulation times out.
- Split by task, never by configuration, so each task's 11 configurations run on the same machine.

### Commands (after `git checkout harness-v1 && uv sync --frozen`)

Pass 1:

```bash
CONFIRM_PAID=1 CONFIRM_EVAL=1 uv run --frozen python scripts/run_all_configs.py --split eval --task-id <your task IDs> --configs B0,E,H0,V,V-E --run-name eval-<yourname> --job-budget-usd 1.00 --prune-cache --keep-going
```

Pass 2 (same run name, so it resumes alongside pass 1's results):

```bash
CONFIRM_PAID=1 CONFIRM_EVAL=1 uv run --frozen python scripts/run_all_configs.py --split eval --task-id <your task IDs> --configs C5,C4,C1 --run-name eval-<yourname> --job-budget-usd 1.00 --prune-cache --keep-going
```

Pass 3:

```bash
CONFIRM_PAID=1 CONFIRM_EVAL=1 uv run --frozen python scripts/run_all_configs.py --split eval --task-id <your task IDs> --configs C0,C2,C3 --run-name eval-<yourname> --job-budget-usd 1.00 --prune-cache --keep-going
```

Run the dry run first (add `--dry-run`, remove the two `CONFIRM_` variables). If interrupted, rerun the same command: finished trials are skipped.

---

## Wednesday 21: finish runs, start the numbers

| When | Who | What |
|---|---|---|
| Morning | Ulfa | Parity check on the first finished tasks: B0 vs H0 reward, exit status and cost. Tasks more than 2 apart out of 40 get flagged in the report |
| By midday | Ulfa | Collector handles `null` usage; `analyze.py` and `plot_pareto.py` run on the dev data |
| Midday | Everyone | **Decision point:** if pass 1 isn't finished on every machine, skip pass 3 and report those ablations as not run |
| Afternoon | Everyone | Rerun infrastructure errors (the same command resumes them). Never delete original attempts |
| By 18:00 | Everyone | Export and push logs, one command per configuration folder (see below) |
| Evening | Ulfa | First full results: success per configuration, Pareto plot, ablation table, cost breakdown |
| All day | Owners | Draft the report sections that don't need results: method (Rohit), harness design (Abin), guardrails (Isha), framework mapping (Asmitha) |

Export command, per configuration folder:

```bash
python3 scripts/export_run.py jobs/eval-<yourname>/<config> results/eval/eval-<yourname>/<config>
```

---

## Thursday 22: report

| When | Who | What |
|---|---|---|
| Morning | Ulfa | Final tables and plots |
| Morning | Isha, with Roshan and Asmitha | Failure classification with one example trajectory per class (Roshan's `classify_failures.py`, Asmitha's `failure_catalog.md`) |
| Afternoon | Rohit | Discussion and conclusions, final edit; **submit Thursday night** |
| Evening | Rohit | Presentation deck, with one slide per owner |

## Friday 23: present

Rehearse in the morning (10 minutes plus 5 of Q&A), then present.

---

## What we drop, in order, if time runs out

1. Repeated runs: a single run per configuration, stated in the report, as the brief allows.
2. Pass 3 ablations (H0+C0, H0+C2, H0+C3), reported as not run.
3. Pass 2 ablations (H0+C5, H0+C4, H0+C1), likewise.
4. **Never dropped:** B0, E, V, V-E, H0, the cost breakdown and the failure classification. The brief requires all of them.

## Risks to watch

| Risk | Mitigation |
|---|---|
| Darkbloom rate limits with six machines at once (Abin's dev runs already lost 9 calls per configuration to them) | Staggered starts; rerun infrastructure errors. Keep the frozen provider: it's the same for every configuration, so the comparison stays fair |
| Out of memory on 8 GB tasks | Schedule them only on machines with ≥ 10 GB of Docker memory; no memory-check override |
| Laptop sleeps mid-run (one dev trial took 6.5 hours because of this) | Plugged in, sleep disabled; on Windows also keep WSL running |
| Live websites drift during the run | Expected; check the trial's `artifacts/` before blaming the harness |
| Disk fills up | `--prune-cache` is in every command; keep 25 GB free |
