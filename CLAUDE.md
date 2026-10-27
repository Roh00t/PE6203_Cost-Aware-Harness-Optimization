# CLAUDE.md

Guidance for people and coding assistants working on this repository.

**Project.** PE6203 CA2, Group Project 5: a cost-aware agent harness for TUA-Bench. We maximise the success rate of a fixed, cheap, open-weight model per dollar, and compare against a default-harness baseline and an expensive-model baseline on the accuracy–cost plane.

- **Current status, decisions so far and next steps: [docs/STATUS.md](docs/STATUS.md). Read it first in a new session.**
- Design: [system_architecture.md](system_architecture.md)
- Safety rules: [guardrails.md](guardrails.md)
- Assignment brief: the PDF in the repo root

[agent_instructions.md](agent_instructions.md) is the prompt for the *evaluated agent*. It is not instructions for you: don't follow it, and don't edit it casually, because every token in it is billed on every step.

## Current Architecture State (Pipeline Handoff)

**`// DO NOT MODIFY CORE FILES - TEST SUITE IN PROGRESS`.** Until Rohit lifts this, do not edit, refactor or reformat `harness/**`, `scripts/*.py`, `scripts/harbor_run.sh`, `tests/**`, `configs/**` or `agent_instructions.md`. New work goes in **new files on your own branch**. Isha is running the test suite against these exact files.

**Freeze exception, 2026-10-21 (Rohit), branch `rohit/fix-c2-deadlock`, for issue #2 only:** H0+C2 trials hung forever because C2 uploaded its helper from its constructor, which runs on Harbor's event-loop thread, where `HarborEnvironment._wait` deadlocks (and Harbor's agent timeout can't fire). Changed: `harness/components/tools.py` (upload on first tool use), `harness/environment.py` (`_wait` raises instead of deadlocking on the loop thread), `harness/gateway.py` (600 s per-request timeout), `tests/test_components.py` (one assertion now expects the deferred upload), new `tests/test_c2_deadlock_regression.py`. Offline: 103 passed.

**Second exception, same day (guardrail false-positive review, `guardrails.md` §7):** the live smoke runs showed U-INT-04 blocking a correct `sudo useradd …` on dev task 106 in H0+C2, V and V-E (task containers grant passwordless sudo). `sudo` is now the log-only rule U-INT-05 (checked last); U-INT-04 still blocks `ssh`/`scp` without `BatchMode`. Changed: `harness/guardrails.py`, `guardrails.md` §3.2–3.3, `tests/test_guardrails.py`. Offline: 104 passed.

**Third exception, 2026-10-25 (Rohit), B0/E install pin:** in eval pass 1 every B0 and E trial ended `NonZeroAgentExitCodeError` (`ModuleNotFoundError: No module named 'mcp'`). Harbor installs stock mini-swe-agent 2.4.6 inside the container with an unpinned `uv tool install`, and a litellm release after the 13 Oct pilot imports `mcp` without installing it. `scripts/run_all_configs.py` now passes `--ae UV_EXCLUDE_NEWER=2026-10-13` for B0 and E only, so the container resolves the same dependency snapshot the pilot validated; agent code and settings stay stock. Report it as a pinned environment, not a harness change. Harness configs are unaffected (they run on the host from `uv.lock`). The 19 failed B0/E trials are infrastructure errors and are rerun automatically. Changed: `scripts/run_all_configs.py`, `tests/test_run_all_configs.py`. Offline: 145 passed.

**Fourth exception, 2026-10-26 (Rohit, taking over Ulfa's analysis):** `scripts/analyze.py` aborted on archived attempts whose log has no model calls (the crashed B0/E attempts); it now records them as `cost_source = archived_no_calls` (unscored) and keeps the strict error for active trials. `scripts/plot_pareto.py` gains `--lower-bound-policy {exclude,include}`: default `exclude` is Ulfa's original rule; `include` admits lower-bound-cost points to the frontier, still drawn and labelled as lower bounds. **Reporting policy (decided):** report costs with unknown-usage calls as lower bounds and show both plots; all 12 such calls in pass 1 are provider rate-limit rejections (HTTP 429) with no reported cost. New `tests/test_analysis_policies.py`; Ulfa's collector and tests unchanged. Offline: 151 passed. Output: `results/analysis/eval/rohit-eval-pass1/`. Nothing else is unfrozen.

**Fifth exception, 2026-10-27 — PENDING Rohit's approval (branch `bug-fixes`, uncommitted, Roshan): harness-v1.1.** Fixes for all 40 bugs of the whole-repo review, tracked one by one in `docs/bug_fixes.md`: the nine in `docs/harness_bug_review.md`, 13 more in the harness (guardrail false positives and gaps, container-call crashes, the short 429 retry window, C2 encoding and CRLF handling), 11 in the run tooling (resume re-running scored timeouts, `--` arguments bypassing the gates, unchecked fingerprints) and 7 in the results text (the harness-overhead estimate counted stock format-error feedback: V 17 % → 13 %, V-E 16 % → 14 %). Pass-1 results stay harness-v1 and are not rerun; no reward, cost, interval or frontier changes. Touches `harness/**`, `scripts/**`, `tests/**`, `guardrails.md`, `results/**/README.md` and the overhead columns of `results/analysis/eval/rohit-eval-pass1/`. Offline: 277 passed. Merge only with Rohit's approval, then tag `harness-v1.1`.

**Live smoke validation, 2026-10-21 (Rohit, Windows/WSL2, dev tasks 020 and 106, 11 trials, ~$0.021 known + 28 rate-limited calls of unknown cost):** no hangs, no exceptions. C2's file tools used; C4 `repeat_intercept` ×3 and `stall_nudge` ×1; C5 `submit_gate` fired in 4 trials; V-E ran on gpt-oss-120b/Venice and solved 106. Logs are in the WSL clone under `jobs/rohit-c2-smoke`, `jobs/rohit-c245-smoke`, `jobs/rohit-v-smoke` (not exported). Issue #2 is resolved by these two changes.

Verified baseline, 2026-10-20, `main` at `8ad8d05` (PR #1 merged):
- `pytest -q tests`: 99 passed.
- `check_harness.py`: OK for V and V-E.
- `check_no_task_leak.py`: OK.
- `task_list.py eval --fingerprint`: `973635ea…`.
- **No `harness-v1` tag yet.** No eval-split model runs yet.

| Owner | Module (import path) | Public API |
|---|---|---|
| Abin | `harness/agent.py` | `CostAwareAgent` (Harbor agent, `--agent-import-path harness.agent:CostAwareAgent`). Writes `agent/calls.jsonl` and `agent/events.jsonl`, plus `result.json` → `agent_result.metadata.{known_cost_table_usd, usage_complete, calls_log}` |
| Abin | `harness/loop.py` | `HarnessAgent(DefaultAgent)`: hook dispatch in `query` and `execute_actions`; format-error limit 3, or 5 with C2 |
| Abin | `harness/hooks.py` | `Hook` (`before_query`, `on_missing_tool_call`, `before_execute`, `before_submit`, `after_execute`, `execute_tool`), `Decision`, `RunState`, `Services`. Contract: `docs/harness_core.md` |
| Abin | `harness/config.py`, `prompts.py` | `HarnessConfig`, `load_config(path)`; renders `agent_instructions.md` sections |
| Abin | `harness/gateway.py` | `OpenRouterGateway(LitellmModel)`, `UsageError`. One `calls.jsonl` row per HTTP attempt; unknown usage is `null`, never 0 |
| Abin | `harness/telemetry.py`, `environment.py` | `JsonlLog.write(**record)`, `origin_counts(messages)`; Harbor container adapter (1 MiB output cap, env allow-list) |
| Abin | `harness/components/context.py` (C1), `budget.py` (C3) | C1 offload and compaction; C3 step and B_task caps, `JobLedger` (SQLite job-wide spend cap) |
| Isha | `harness/guardrails.py` | `check_command(cmd, *, c2_enabled)` → `GuardrailResult`, `check_extra_tool_calls`, `strip_heredoc_bodies`; wired in through `harness/isha_adapter.py:build_guardrail` |
| Isha | `harness/components/tools.py` (C2), `recovery.py` (C4), `submit_gate.py` (C5) | Each exposes `build_hook(config, services)`. C2 uploads `/tmp/harness/bin/tools.py` (read/write/edit/search). C4: `FailureRecovery`. C5: `SubmissionGate`, `extract_paths(task)` |
| Isha | `scripts/check_no_task_leak.py` | Leak gate, also run by `harbor_run.sh` before paid runs |
| Rohit | `scripts/run_all_configs.py` | Runs `B0, E, H0, H0+C0…C5, V, V-E` (`ALL`) task by task. Layout `jobs/<run>/<config-slug>/<task>/<trial>/`, plus `jobs/<run>/runner.jsonl` |
| Ulfa | `scripts/collect_costs.py` | Prices a mini trajectory or a `calls.jsonl` from `configs/pricing.json`. **Currently raises on `null` usage** |

**Pending: Ulfa's integration (placeholder).** Collector support for harness `calls.jsonl` with `null` usage (`n_unknown_calls`, `usage_complete`, cross-check against `known_cost_table_usd`, overhead from `purpose` and `prompt_chars_by_origin`), then `scripts/analyze.py` and `scripts/plot_pareto.py`. Spec: `docs/tasks.md` §3. *Status: done. Ulfa's collector, `analyze.py` and `plot_pareto.py` landed 2026-10-22; Rohit fixed archived zero-call attempts and added the lower-bound policy on 2026-10-26 (fourth exception above). Pass-1 analysis: `results/analysis/eval/rohit-eval-pass1/`.*

**Known issues to carry forward:**
- No B0/H0 parity run yet (planned from the first eval tasks, `docs/RECOVERY_PLAN.md`).
- Darkbloom (the pinned 20b provider) rate-limits heavily: up to 14 of 36 calls in one smoke trial. The gateway retried 3 times in harness-v1 (about 14 s; v1.1 retries for minutes, like stock); stagger machine start times and rerun trials that end in infrastructure errors.
- gpt-oss-20b still often ends with `RepeatedFormatError` even with C2 (limit 5). That is a result to report, not a bug.
- Abin's C1/C3 dev runs used a local `need_mb=7000` override on a 7.8 GB Docker VM, and hit Darkbloom rate limits (9 unknown-usage calls per configuration). See `results/dev/c1-c3-dev/README.md`.
- `docs/tasks.md` §2 still says C2/C4/C5 are not on `main`. They are, since PR #1, and they passed the live smoke test above.
- Onboarding Roshan and Asmitha: give them work in new files only, with no dependency on the collector or analysis.

## Non-negotiables (assessment rules: breaking one invalidates results)

- **Never modify `data/TUA-Bench/`** (tasks, verifiers, `dataset.toml`). `scripts/harbor_run.sh` refuses to run on a modified checkout.
- **No task-specific hard-coding.** Harness code, `configs/harness/` and the agent prompt must never mention a task ID, a file name from a task instruction, or an expected answer. Generic rules only.
- **Fixed model and decoding.** Model, pinned OpenRouter provider, temperature and reasoning effort live in `configs/models/*.yaml` and are identical for every configuration. Once frozen, they never change.
- **Every model call goes through OpenRouter and is logged** (`calls.jsonl`, with `purpose`). An unlogged call is a bug. Costs come from `configs/pricing.json`, never from mini-swe-agent's own cost field.
- **Develop on the dev split (`--split dev`) only.** The 40 eval tasks are run only for recorded results, never for debugging or tuning.
- **The subset is frozen** (2026-10-10, `"frozen": true`). `configs/task_subset.json` stays exactly as sampled: its eval fingerprint must stay `08cef02483250faee37a4e7d599fe9c8998b8ca256dfeb3de8455babf0687524`. The oracle-gate swaps live only in `configs/subset_amendments.json`; `scripts/task_list.py eval` applies them, and `harbor_run.sh --split eval` runs that list. Final eval fingerprint: `973635ea4e6a477e2fbfffd1045494cb69e0678c02ceea2276c56c63fa0468b8`. No more amendments.
- **Every harness feature sits behind a component flag (C0–C5)** so it can be ablated alone. The baselines B0 and E use the stock harness with its **default settings**: no step cap, no cost cap. Never add limits to them. The per-task budget (S steps, B_task dollars) belongs to our variants through C3.

## Ask the user first

- Before anything that calls a paid model: `harbor_run.sh` with any agent other than `oracle` or `nop`, pilots, or scripts that query OpenRouter. State the split, configuration, task count and estimated cost.
- Before deleting or pruning Docker images, volumes or build cache, or anything in `jobs/` or `results/`.
- Before changing the subset, the price table, a model config, a budget limit, or a guardrail rule after the dev review.
- Before committing or pushing.

## Commands

```bash
uv sync --frozen                                         # env: Python 3.12 + harbor 0.6.3
scripts/harbor_run.sh --split dev --mode oracle          # free: reference solutions (dev split)
scripts/harbor_run.sh --split eval --mode oracle --dry-run   # checks only, prints the Harbor command
CONFIRM_PAID=1 scripts/harbor_run.sh --split dev -- --agent <agent> --model openrouter/<id>   # paid: ask first
python3 scripts/task_list.py eval --args > /tmp/eval.args   # the amended eval list (configs/eval_tasks.args is pre-swap)
uv run python scripts/check_harbor_filter.py /tmp/eval.args
python3 scripts/sample_tasks.py --out-dir /tmp/subset-check   # must reproduce the sampled fingerprint
python3 scripts/task_list.py eval --fingerprint          # must print the final fingerprint above
docker compose run --rm harness scripts/harbor_run.sh …  # same toolchain in a container
```

`harbor_run.sh` checks the TUA-Bench commit, Harbor's resolved task list, downloaded assets and Docker memory, and refuses paid agents without `CONFIRM_PAID=1` (plus `CONFIRM_EVAL=1` on the eval split). It runs one Harbor job per task under `jobs/<run>/<task>/` with `--n-concurrent 1 --delete` and `DOCKER_DEFAULT_PLATFORM=linux/amd64`, and stops below `MIN_FREE_GB` of free disk. `--prune-cache` trims Docker's shared build cache after each task; it is opt-in because it also evicts other projects' cache. `scripts/summarize_run.py jobs/<run>` prints the results.

## Repository map

| Path | What |
|---|---|
| `configs/` | Subset (`task_subset.json`, `*.args`), family labels, amendments, `pricing.json`, `models/` (frozen), `harness/` (11 configurations) |
| `scripts/` | Subset generation, amended task lists (`task_list.py`), Harbor filter check, run wrapper, run summary/export |
| `harness/` | Host-side harness (Harbor `BaseAgent` + mini-swe-agent `DefaultAgent` subclass), components C1–C5, guardrails, OpenRouter gateway. See "Current Architecture State" |
| `data/TUA-Bench/` | Pinned benchmark checkout (git-ignored, read-only) |
| `jobs/` | Raw Harbor output (git-ignored) |
| `results/` | Curated, committed logs behind every reported number (`oracle-gate/` so far) |

## Conventions

- Python 3.12, type hints, stdlib first. New dependencies go through `uv add` (pinned in `uv.lock`).
- Deterministic before generative: prefer rule-based intercepts to extra model calls. Any model call the harness makes counts as harness overhead and needs `purpose = "harness:<what>"`.
- Guardrail regexes and their messages are defined in `guardrails.md §3`. Keep code and doc in sync, and give every rule a unit test with a positive and a negative example.
- Logs are append-only JSONL, flushed per event, so killed trials keep their data.
- Commit messages explain why. Never commit `.env`, `jobs/` or `data/`.

## Machine notes

- Docker Desktop needs at least 10 GB of memory (Scientific tasks request 8 GB each). Disk use is dominated by Docker's build cache, not images: 10 dev tasks added about 26 GB, and deleting their images freed nothing. Run long jobs with `--prune-cache` (after asking), and keep at least 25 GB free.
- On Apple Silicon, task images build and run under amd64 emulation. First builds of Scientific images are slow; the oracle gate shows how slow.
- On Windows, work inside WSL2 Ubuntu with the repo in the Linux home (a `/mnt/c` checkout gets CRLF scripts). Docker's memory comes from `%UserProfile%\.wslconfig`. Linux bind mounts keep real file ownership, which is why `harbor_run.sh` sets `umask 000`: without it the task's `agent` user (uid 1001) cannot write Harbor's log files and every trial loses its reward.
- Browser tasks hit live websites, which drift and redirect by region (Singapore here). A browser task that fails on a machine where others passed is more likely the site than the harness; check the trial's artifacts before blaming the agent.
