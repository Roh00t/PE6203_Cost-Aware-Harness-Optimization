# Team Tasks: 14–23 October (status refreshed 19 October)

Step-by-step instructions for each of us, from now until the presentation. Each task says what to read, what to build or run, how to check it, and when it is due. Background and history: [`docs/STATUS.md`](STATUS.md). Design: [`system_architecture.md`](../system_architecture.md). Progress page: https://claude.ai/artifact/D1a8FLLj5aqiAAeXWSBWSN

**Status snapshot (Mon 19 Oct):** the subset, models and budget remain frozen. The harness core, C1/C3, guardrails, leak-check gate, C0 prompt, configurations and runner are on `main`. Partial C1/C3 dev logs have been published, but B0/H0 parity and infrastructure-failure reruns are still pending. C2/C4/C5 are not present in the current `main` checkout; Isha's remaining work is summarized in §2 below. See [`docs/STATUS.md`](STATUS.md) and the [partial-run handoff](../results/dev/c1-c3-dev/README.md) for evidence.

| Original target date | Planned milestone (historical; see status sections for actual completion) | Owner |
|---|---|---|
| Thu 15 Oct | Live H0 check done; C2, C4, C5 pushed; collector reads harness logs | Abin, Isha, Ulfa |
| Fri 16 Oct | Harness v1 frozen and tagged; eval runs start | Rohit, then all |
| Mon 19 Oct | All eval runs exported and pushed | All |
| Thu 22 Oct | Report finished | All |
| Fri 23 Oct | Presentation | All |

If anything slips, say so in the group the same day: every later step waits on the one before it.

---

## 0. Everyone: before you start each day

1. Open the Ubuntu terminal (Windows) or Terminal (Mac) and go to the repo:
   ```bash
   cd ~/PE6203_Cost-Aware-Harness-Optimization
   ```
2. Get the latest `main` and the matching Python environment:
   ```bash
   git checkout main && git pull && uv sync --frozen
   ```
3. Check everything still works (offline, free, about 10 seconds). It must end with `passed` and no failures:
   ```bash
   uv run --frozen python -m pytest -q tests
   ```
   Use pytest, not `python -m unittest`: unittest only finds 12 of the tests.
4. Start new work on your own branch from `main`, never on top of an old branch:
   ```bash
   git checkout -b <yourname>/<topic>
   ```

### Rules that protect our results

- **Dev tasks only while building and testing** (`--split dev`). The 40 eval tasks are run only for the recorded results, from Fri 16.
- **Never edit** `data/TUA-Bench/`, `configs/task_subset.json`, `configs/subset_amendments.json`, `configs/pricing.json` or `configs/models/*.yaml`. They are frozen.
- **No task-specific code or text.** Harness code, `configs/harness/` and `agent_instructions.md` must never mention a task ID, a file name from a task, or an expected answer. `scripts/check_no_task_leak.py` checks this and `harbor_run.sh` refuses paid runs if it fails.
- **Money:** use your own OpenRouter key with a credit limit, in `.env` (never in chat or git). Post in the group before any paid run: what you'll run, how many tasks, and the expected cost.
- **Never commit** `.env`, `jobs/` or `data/` (the `.gitignore` already blocks them).

### How to run configurations (everyone will use this)

`scripts/run_all_configs.py` runs a list of configurations task by task, one trial at a time, through `scripts/harbor_run.sh`. Always try a dry run first: it prints the commands and runs nothing.

```bash
uv run --frozen python scripts/run_all_configs.py --split dev --task-id 106-create-charles-ssh-user --configs B0,H0,C1 --run-name smoke --job-budget-usd 0.05 --dry-run
```

- `--configs`: any of `B0`, `E`, `H0`, `C0`…`C5` (short for H0+C0…H0+C5), `V`, `V-E`, or `ALL` (all 11).
- `--task-id`: one or more task IDs, comma-separated. Leave it out to run the whole split.
- `--run-name`: output goes to `jobs/<run-name>/<config>/<task>/`. Run the same command again to resume: finished trials are skipped.
- `--job-budget-usd`: a spend limit shared by all harness trials in the run (B0 and E have no cap by design).
- For a real (paid) run, remove `--dry-run` and put `CONFIRM_PAID=1` in front (eval also needs `CONFIRM_EVAL=1`).
- Results: `jobs/<run-name>/runner.jsonl` has one line per trial (reward, exception, exit code). For a table per configuration:
  ```bash
  python3 scripts/summarize_run.py jobs/<run-name>/<config>
  ```

Inside each trial folder (`jobs/<run>/<config>/<task>/<task>__<id>/`): `agent/calls.jsonl` (every model call with tokens and cost), `agent/events.jsonl` (guardrail blocks, offloads, budget events), `agent/mini-swe-agent.trajectory.json` (the full conversation), `verifier/reward.txt`.

---

## 1. Abin: live validation of the harness core

**Goal:** show with real runs that our host-side loop (H0) behaves like stock mini-swe-agent (B0), then check C1 and C3 on their own. **Due:** Thu 15 Oct, end of day. **Cost:** about $0.05 in total with gpt-oss-20b.

**Read first:** `system_architecture.md` section 10.2 (parity check) and your own `docs/harness_core.md`, section "Live validation after integration".

1. **Post in the group** before starting: "Running B0 and H0 on the 10 dev tasks, then C1 and C3, about $0.05, job cap $0.10."
2. **Dry run**, check that the commands look right:
   ```bash
   uv run --frozen python scripts/run_all_configs.py --split dev --configs B0,H0 --run-name parity-dev --job-budget-usd 0.10 --dry-run
   ```
3. **Real run** (about 1–2 hours, mostly image builds; you can leave it running):
   ```bash
   CONFIRM_PAID=1 uv run --frozen python scripts/run_all_configs.py --split dev --configs B0,H0 --run-name parity-dev --job-budget-usd 0.10 --keep-going
   ```
   We rerun B0 next to H0 on the same day so live websites and provider behaviour are the same for both.
4. **Compare per task.** Print both tables:
   ```bash
   python3 scripts/summarize_run.py jobs/parity-dev/b0
   ```
   ```bash
   python3 scripts/summarize_run.py jobs/parity-dev/h0
   ```
   For each of the 10 tasks, note: reward, how the run ended (`exit_status` in the trajectory: Submitted, RepeatedFormatError, …), number of model calls, cost. Expected: the same pattern as Ulfa's pilot (20b mostly ends on format errors). Any difference should be explained by the command wrapper (timeouts, output handling), not the loop.
5. **Then C1 and C3 alone**, same way (about $0.03):
   ```bash
   CONFIRM_PAID=1 uv run --frozen python scripts/run_all_configs.py --split dev --configs C1,C3 --run-name c1-c3-dev --job-budget-usd 0.10 --keep-going
   ```
   For C1: check `events.jsonl` for `offload` and `compaction` events. For C3: note at which step each run stopped and why (`cap_reached` = dollar cap, `LimitsExceeded` = 50 steps). We expect the dollar cap to stop long runs a few steps before 50; we need the real numbers for the report.
6. **Export the logs to git** (one command per configuration):
   ```bash
   python3 scripts/export_run.py jobs/parity-dev/h0 results/dev/parity-dev/h0
   ```
   Repeat for `b0`, then for `jobs/c1-c3-dev/h0-c1` and `jobs/c1-c3-dev/h0-c3`.
7. **Write up** a short table (task, B0 reward/exit/cost, H0 reward/exit/cost) in `docs/harness_core.md` under a new heading "Live validation results", commit on a branch, push, and post the summary in the group.
8. **After that:** help Isha integrate C2/C4/C5 (Thu 15) and fix anything the V smoke test finds (Fri 16 morning).

**Done when:** the table is pushed, every H0/B0 difference has an explanation, and C1/C3 events show up in the logs.

---

## 2. Isha: C2, C4 and C5

**Goal:** implement and validate the three remaining components as independent plugins. Original due date: Thu 15 Oct (elapsed). **No paid runs are authorized by this checklist**; obtain approval before the dev smoke test in step 8.

### Isha status (checked 19 Oct)

**Completed**

- Guardrail rules and unit tests are implemented; guardrails are integrated on `main`.
- The task-leak checker and paid-run gate are implemented and covered by tests. The checker’s live scan requires the local `data/TUA-Bench/tasks` checkout, which is not available in every clone.
- C2, C4 and C5 are implemented as independent plugins in `harness/components/tools.py`, `recovery.py`, and `submit_gate.py`; fake-service behavior tests are in `tests/test_components.py`.
- The C2 loop enforces one executed action per response while returning a result for each tool-call ID. A regression test also checks that H0 retains multi-action behavior.
- The full pinned offline suite passes: 99 tests. `scripts/check_harness.py --config configs/harness/V.yaml` reports `OK: integration factories import`.
- The approved C2/C4/C5 dev smoke-test command was attempted for the two planned tasks, but all six trials stopped at the runner preflight because `data/TUA-Bench` is absent. No Harbor trial or model call started; no spend occurred.
- The published C1/C3 trajectories have been reviewed and the limitations documented in [`results/dev/c1-c3-dev/README.md`](../results/dev/c1-c3-dev/README.md). They contain no `guardrail_block` events, so they do not yet provide evidence for the false-positive review.
- Collector regression tests for complete/incomplete usage and provider validation are added in [`tests/test_collect_costs.py`](../tests/test_collect_costs.py). This is supporting test work, not a decision to change Ulfa’s collector policy.

**Still open**

- Run `scripts/check_no_task_leak.py` once the pinned TUA-Bench task checkout is present. The command was attempted but this checkout does not contain `data/TUA-Bench/tasks`.
- Push the implementation branch and request review from Abin and Rohit.
- Restore the pinned TUA-Bench checkout, then coordinate before retrying the two-task C2/C4/C5 dev smoke test. The approved attempt stopped before trials began; preserve its runner record and verify component events on a successful run.
- Complete a false-positive review when dev logs contain `guardrail_block` events. The published partial C1/C3 logs contain none.
- Complete guardrails §8 after Rohit supplies the course lecture slides.

The implementation instructions below document the acceptance criteria and validation steps; the historical dates are not evidence that a task was completed.

**Read first:**
- `system_architecture.md` section 5, the parts "C2 · Tool interface", "C4 · Failure detection and recovery", "C5 · Pre-submission verification gate". These are the specs.
- `docs/harness_core.md`, section "Integration contract for Isha": the hooks, what each receives and returns, and the `Decision` and observation formats.
- `harness/hooks.py` (the `Hook` base class and `Decision`), and `harness/components/context.py` as an example of a component.
- `tests/test_harness_core.py`: copy its fake container and fake services for your tests.

**File names are fixed** (the configs already point at them; `configs/harness/c2.yaml`, `c4.yaml`, `c5.yaml`, `V.yaml`, `V-E.yaml`):

| Component | File | Factory | Declares |
|---|---|---|---|
| C2 | `harness/components/tools.py` | `build_hook(config, services)` | `components = frozenset({"C2"})` |
| C4 | `harness/components/recovery.py` | `build_hook(config, services)` | `components = frozenset({"C4"})` |
| C5 | `harness/components/submit_gate.py` | `build_hook(config, services)` | `components = frozenset({"C5"})` |

1. **Branch** from fresh `main` for the component implementation (the earlier `isha/guardrails` work is already integrated into `main`):
   ```bash
   git checkout main && git pull && git checkout -b isha/c2-c4-c5
   ```
2. **C2: tools and validation** (`tools.py`):
   - Four function tools with argument schemas, advertised in the hook's `tools` list: `read_file(path, start_line?, end_line?)` (numbered lines, at most 200), `write_file(path, content)`, `edit_file(path, old, new)` (one exact, unique match, otherwise fail and say how many matches), `search(pattern, path, glob?)` (`file:line: text`, at most 100 hits).
   - They run inside the container through one helper script uploaded to `/tmp/harness/bin/tools.py` (use `services` to write it). Pass arguments base64-encoded so shell quoting can't break them. Implement them in the `execute_tool` hook.
   - Validate arguments before anything runs; a bad call gets a short error naming the problem and a valid example.
   - `on_missing_tool_call`: return the C2 recovery message (the exact text is in `guardrails.md` section 3.3, row "Format error (C2)"). The loop already raises the format-error allowance from 3 to 5 when C2 is on.
   - The U-rules (interactive programs, long commands, unclosed heredocs, submit combined with other work) are already applied by your guardrails through `harness/isha_adapter.py` when C2 is on. Don't duplicate them.
   - If the model sends several tool calls, only the first runs; the others get a blocked result so every call gets an answer.
3. **C4: failure recovery** (`recovery.py`):
   - Repeat-failure intercept (`before_execute` + `after_execute`): hash each command with sha256 of its whitespace-normalised text; remember which hashes failed (return code not 0). If a hash already failed twice, don't run it: return `Decision(allowed=False, feedback=…)` with the last error and "state in one sentence why it failed, then try a different approach". Log a `repeat_intercept` event.
   - Stall detection (`after_execute`): three identical observations in a row → append one nudge to re-read the task and check assumptions. Log `stall_nudge`.
   - Timeout recovery (`after_execute`): when a command was killed by the timeout (return code 124 or 137), append the fixed message with the background-job recipe (`nohup CMD > /tmp/job.log 2>&1 &`, then poll the log). Log `command_timeout`.
   - Mark every text you add: `extra.harness_chars` (or `extra.origin = "harness"` for fully injected messages) so Ulfa can count harness overhead.
4. **C5: submit gate** (`submit_gate.py`, hook `before_submit`):
   - Hold back the **first** submission only. Never gate once 90 % of the steps are used, and never more than once (`max_gate_rejections = 1`).
   - Take absolute file paths from the task text with a generic regex (backticked or bare `/…/name.ext`). For each, run `test -s` in the container and compare the file's modification time with the trial start.
   - Return `Decision(allowed=False, feedback=…)` with a ✓/✗ line per path, the first 600 characters of the task, and a request to confirm each requirement by reading the outputs back. Tasks without paths get the checklist without file checks. Log `submit_gate`.
   - The next submission is accepted.
5. **Tests** in `tests/test_components.py`: for every behaviour, one case where it triggers and one where it must not (for example: a command that failed twice is blocked, a command that failed once is not). Use fakes, no Docker, no API.
6. **Check** (all must pass):
   ```bash
   uv run --frozen python -m pytest -q tests
   ```
   ```bash
   uv run --frozen python scripts/check_no_task_leak.py
   ```
   ```bash
   uv run --frozen python scripts/check_harness.py --config configs/harness/V.yaml
   ```
   The last one must print `OK: integration factories import`, not `BLOCKED`.
7. **Push** the branch and tell Abin and Rohit in the group:
   ```bash
   git push -u origin isha/c2-c4-c5
   ```
8. **Dev smoke test** (after approval in the group, about $0.02): run each component alone on two dev tasks and check its events appear:
   ```bash
   CONFIRM_PAID=1 uv run --frozen python scripts/run_all_configs.py --split dev --task-id 020-calculate-period-rate,106-create-charles-ssh-user --configs C2,C4,C5 --run-name c245-smoke --job-budget-usd 0.05 --keep-going
   ```
9. **False-positive review** (Thu 15–Fri 16, after Abin's H0 runs): look at every `guardrail_block` event in the dev logs (`grep -h guardrail_block jobs/*/*/*/*/agent/events.jsonl`). Any block of a legitimate command means the rule is too broad: narrow it and add a test.
10. **When Rohit sends the lecture slides:** `guardrails.md` section 8, mapping our rules to the course frameworks.

**Done when:** all three plugins are on your branch, the tests and checks pass, and `check_harness.py` reports V as OK.

---

## 3. Ulfa: cost collector and analysis

**Goal:** turn every run's logs into costs and the results tables and plots. **Due:** collector Thu 15; analysis scripts ready before the eval logs arrive (Mon 19). **Cost:** free.

**Read first:** `docs/harness_core.md`, section "Logs and Ulfa's collector"; `system_architecture.md` section 8 (cost accounting) and section 10.4 (analysis).

1. **Branch:**
   ```bash
   git checkout main && git pull && git checkout -b ulfa/collector
   ```
2. **Make `scripts/collect_costs.py` read both kinds of runs:**
   - **B0 and E** (stock mini-swe-agent): as now, tokens from the trajectory × `configs/pricing.json`.
   - **Harness configurations:** read `agent/calls.jsonl`. Each line is one HTTP attempt (retries are separate lines). Sum `cost_table_usd` over lines with known usage.
   - **Unknown usage:** failed calls have `prompt_tokens`/`completion_tokens` = `null` (never 0). Don't drop them and don't treat them as free: count them per trial (`n_unknown_calls`) and mark the trial `usage_complete = false`. Report these trials separately in the results.
   - Per trial output: config, task, reward, known cost, number of calls, unknown calls, usage complete (yes/no). Per configuration: success rate, total and mean cost.
   - **Cross-check:** the harness also writes its own total to the trial's `result.json` (`agent_result.metadata.known_cost_table_usd`). Your total must match it to the cent.
   - **Harness overhead:** sum `cost_table_usd` where `purpose` starts with `harness:` (should be $0), and estimate the harness-injected share of prompts from `prompt_chars_by_origin` (architecture section 8.3).
3. **Test** on a small hand-made `calls.jsonl` in `tests/` (one normal call, one retry, one with `null` usage), then on Abin's first real H0 run (`jobs/parity-dev/h0` once he has it).
4. **Propose in the group** how the report shows trials with unknown usage (for example: "cost is a lower bound for N trials"). This is still an open decision.
5. **`scripts/analyze.py`:** success rate per configuration over the 40 eval tasks; each configuration against B0 with a paired bootstrap over tasks (95 % interval); the family-reweighted estimate (Office 46, Web 22, System 19, Scientific 17, Multimedia 16, out of 120); the ablation table (each H0+Cn against H0).
6. **`scripts/plot_pareto.py`:** success rate against mean cost per task for all 11 configurations, with the Pareto frontier marked.
7. **Build both on the dev data** (Abin's runs) so they're ready when the eval logs arrive Mon 19.
8. **Budget ledger, ongoing:** keep a running total of spend across everyone's keys (ask each person after their runs); warn the group at 70 % of the $8.
9. **Push** the branch and post in the group.

**Done when:** the collector reproduces the harness's own totals on Abin's H0 run, handles `null` usage, and the analysis scripts produce a table and a plot from dev data.

---

## 4. Rohit: integration and freeze

1. **Today (Wed 14):** commit and push the C0 prompt (`agent_instructions.md` v3), the 11 configs (`configs/harness/`), `scripts/run_all_configs.py` with its tests, this file and the updated docs.
2. **Thu 15:** review Abin's validation table and Isha's branch; merge C2/C4/C5 into `main`.
3. **Thu 15 evening:** V smoke test on two dev tasks (about $0.01), after posting in the group:
   ```bash
   CONFIRM_PAID=1 uv run --frozen python scripts/run_all_configs.py --split dev --task-id 020-calculate-period-rate,106-create-charles-ssh-user --configs V --run-name v-smoke --job-budget-usd 0.05
   ```
4. **Fri 16 morning: freeze.** All tests and the leak check pass; tag the commit (`git tag harness-v1 && git push --tags`). No harness, prompt or config changes after this.
5. **Fri 16: run schedule.** Assign the 40 eval tasks to laptops by task, never by configuration: 10 each, Scientific tasks (8 GB) to the machines with the most memory and disk. Post the list and each laptop's `--job-budget-usd`.
6. **Send the lecture slides** to Isha for `guardrails.md` section 8.

---

## 5. Everyone: eval runs (Fri 16 – Mon 19)

Only after the `harness-v1` tag. Each person runs all 11 configurations on their own 10 tasks.

1. Pull and check out the frozen version:
   ```bash
   git checkout main && git pull && git checkout harness-v1
   ```
   ```bash
   uv sync --frozen && uv run --frozen python -m pytest -q tests
   ```
2. Make sure there's at least 25 GB free and Docker has 10 GB of memory.
3. Dry run with your task list from the schedule:
   ```bash
   uv run --frozen python scripts/run_all_configs.py --split eval --task-id <your 10 task IDs, comma-separated> --configs ALL --run-name eval-<yourname> --job-budget-usd <from the schedule> --prune-cache --dry-run
   ```
4. Real run (several hours; it can be stopped with Ctrl+C and resumed with the same command):
   ```bash
   CONFIRM_PAID=1 CONFIRM_EVAL=1 uv run --frozen python scripts/run_all_configs.py --split eval --task-id <your 10 task IDs> --configs ALL --run-name eval-<yourname> --job-budget-usd <from the schedule> --prune-cache --keep-going
   ```
5. Trials that ended in an infrastructure error (Docker crash, network outage, provider down) are not task failures. Rerun them (the same command resumes them); if it keeps failing, post in the group.
6. Export and push your logs (one command per configuration folder):
   ```bash
   python3 scripts/export_run.py jobs/eval-<yourname>/<config> results/eval/eval-<yourname>/<config>
   ```
   Commit `results/eval/eval-<yourname>/` on a branch, push, and post in the group. Deadline Mon 19.

---

## 6. Report and presentation (Mon 19 – Fri 23)

| Part | Owner |
|---|---|
| Introduction, method (subset, oracle gate, models, budget), conclusions, final edit | Rohit |
| Harness design and how it plugs into Harbor | Abin |
| Guardrails, failure classification with example trajectories | Isha |
| Results: Pareto plot, ablation table, cost breakdown | Ulfa |
| Presentation deck (10 min + 5 Q&A) and rehearsal | Rohit, with everyone's slides |

---

## If something goes wrong

| Problem | What to do |
|---|---|
| A trial has no reward and a `RewardFileNotFoundError` | On Linux/WSL this was a file-permission problem, fixed in `harbor_run.sh` (`umask 000`). Make sure you pulled `main` and run through `harbor_run.sh` or `run_all_configs.py`, not plain `harbor run`. |
| `harbor_run: Docker VM has … MB` | Give Docker 10 GB (Windows: `.wslconfig`, see STATUS section 5). |
| `check_no_task_leak` fails | Remove the task ID or file name it names from your code or prompt. Never weaken the check. |
| `BLOCKED for live runs` from `check_harness.py` | A plugin file named in the config doesn't exist yet (expected for V until C2/C4/C5 are merged). |
| A browser task fails | Live websites change and redirect from Singapore. Look at the trial's `artifacts/` first; post in the group if the site itself looks broken. |
| Ran out of disk | Use `--prune-cache` (it trims Docker's build cache after each task). Keep 25 GB free. |
