# Project Status and Handoff

Base snapshot **2026-10-14** (Rohit's Windows laptop, WSL2); update **2026-10-19**. Read this first when picking the project up on another machine or in a new Claude Code session, then [`CLAUDE.md`](../CLAUDE.md) and [`system_architecture.md`](../system_architecture.md).

> **For a new Claude Code session:** this file holds the context of the earlier sessions. Start with: *"Read docs/STATUS.md, CLAUDE.md and system_architecture.md, then continue from 'Next steps'."*

### Update — 2026-10-19

- Abin's partial C1/C3 dev runs and logs are published on `main`. C1 has 7 scored trials out of 10 attempts; C3 has 8. This is not a completed B0/H0 parity study. See the [trajectory review and limitations](../results/dev/c1-c3-dev/README.md).
- Trajectory review found 40 `format_error` events per configuration, two C1 offloads (both in task 009), and no C3 `cap_reached` event. Do not draw component-effectiveness conclusions from these partial runs.
- Regression tests now cover the cost collector's complete call-log and mini-swe trajectory inputs, null usage rejection, provider validation, and empty logs. The policy for reporting calls with unknown usage remains open; missing usage must not be presented as zero cost.
- The C2/C4/C5 implementation passes the full pinned offline suite (99 tests); V's integration preflight imports all plugin factories. The task-leak scan is blocked because `data/TUA-Bench/tasks` is absent from this checkout.
- The approved six-trial C2/C4/C5 smoke-test invocation stopped at the runner preflight because `data/TUA-Bench` is absent; no trial or model call started, so no spend occurred.
- Next validation steps: obtain team approval for the C2/C4/C5 dev smoke test, review guardrail blocks from suitable logs, complete matched B0/H0 dev runs, rerun infrastructure/API failures without replacing the original attempts, and finish component checks before drawing comparisons.

---

## 1. Where the project stands

| Area | Status |
|---|---|
| Evaluation subset | **Done and frozen** (2026-10-10). 40 eval + 10 dev tasks. Sampled fingerprint `08cef024…`; after the oracle-gate swaps the **final eval fingerprint is `973635ea…`** (§2) |
| Run tooling | **Done.** `scripts/harbor_run.sh` (per-task jobs, pause/resume, `--only`, `--rerun`, `--split dev|eval|reserve`, asset/memory/disk checks, paid-run gates), `task_list.py`, `summarize_run.py`, `export_run.py`. Works on macOS and on Windows via WSL2 |
| Design docs | **Done**, checked line by line against the brief. `guardrails.md` §8 waits for the lecture slides |
| Dev oracle check | **Done: 9/10.** `100-name-mountain-photos` fails because of a bug in the benchmark's reference solution (agents can still solve it). Logs: `results/oracle-gate/dev-mac*/` |
| Eval oracle gate | **Done.** 40/40 settled on Mac + x86, 4 tasks swapped for reserves that pass (§2). Logs: `results/oracle-gate/eval-mac/`, `eval-x86/`, `reserve-x86/` |
| Model choice and price table | **Done and frozen** (2026-10-13, Ulfa). gpt-oss-20b on Darkbloom (base), gpt-oss-120b on Venice (expensive); `configs/pricing.json`, `configs/models/`, evidence in `docs/model_selection.md` and `results/pilots/` |
| B_task | **Frozen:** $0.01 per task (base), $0.0167 (V-E), with the 50-step cap. Reasoning in architecture §6 |
| Harness core | **On `main`** (2026-10-14, Abin): Harbor agent, loop with hooks, container adapter, OpenRouter gateway with call logging, C1, C3, guardrails (Isha) wired in, leak check before paid runs. Partial C1/C3 dev results are published; B0/H0 parity and infrastructure-failure reruns remain pending. Hook contract: `docs/harness_core.md`; results: [`results/dev/c1-c3-dev/`](../results/dev/c1-c3-dev/) |
| C0 prompt, V/V-E configs, multi-config runner | **Written** (2026-10-14, Rohit): `agent_instructions.md` v3, `configs/harness/` (all 11 configurations), `scripts/run_all_configs.py`. V and V-E plugin factories are now present on `isha/c2-c4-c5`; full integration validation remains pending |
| C2, C4, C5 | Implemented on `isha/c2-c4-c5`; full pinned suite passes (99 tests), and V integration factories import. Task-leak scan and approved paid smoke test are blocked by the missing TUA-Bench checkout; broader false-positive review awaits suitable logs. See [`docs/tasks.md` §2](tasks.md#2-isha-c2-c4-and-c5) |
| Experiments, report | Not started. Owners and dates in §4 |

### Progress by workstream (2026-10-14 snapshot)

| Workstream | Weight | Done | Weighted |
|---|---|---|---|
| 1. Benchmark subset | 8 % | 100 % | 8.0 |
| 2. Run infrastructure | 10 % | 100 % | 10.0 |
| 3. Design documents (open: guardrails §8, needs the lecture slides) | 10 % | 90 % | 9.0 |
| 4. Oracle gate | 5 % | 100 % | 5.0 |
| 5. Model choice and price table | 5 % | 100 % | 5.0 |
| 6. Harness implementation (core, C1, C3, guardrails, C0, configs done; C2/C4/C5 and live validation open) | 25 % | 50 % | 12.5 |
| 7. Baselines B0 and E on eval | 5 % | 0 % | 0 |
| 8. Experiment runs | 12 % | 0 % | 0 |
| 9. Analysis and report | 15 % | 0 % | 0 |
| 10. Presentation | 5 % | 0 % | 0 |
| **Overall** | | | **49.5 %** |

Weights are relative effort estimates, not hours. Model spend so far: about **$0.18** at table prices (Ulfa's dev pilots, $0.16 of it the rejected Qwen candidate; figures in `docs/model_selection.md` and `results/pilots/`).

Team progress page: https://claude.ai/artifact/D1a8FLLj5aqiAAeXWSBWSN

---

## 2. Eval oracle gate: final result

Reference solutions on all 40 eval tasks: 28 settled on the Mac (`eval-oracle-gate`), the 12 left open (network outage, browser/OCR trouble under emulation) rerun on an x86 Windows laptop (`eval-oracle-gate-x86`). Swap rule (Rohit): swap **only** for infrastructure/environment failures, i.e. when no agent could pass the task on our machines.

| Outcome | Tasks |
|---|---|
| Passed, reward 1 (31) | 000, 006, 008, 011, 015, 016, 036, 037, 040, 041, 047, 052, 057, 068, 073, 074, 075, 076, 080, 085, 087, 088, 089, 099, 101, 102, 105, 114, 115, 116, 117 |
| Kept, reference-solution bug (3) | 004-place-heater-for-sensors, 019-prostate-red-overlay (solution reads `/tests/reference/` before Harbor uploads it); **110-rotate-macintosh-video** (solution flips both axes, gold is a vertical flip only; checked: the oracle output flipped back matches gold, so agents can pass) |
| Kept, continuous metric (2) | 111-set-video-wallpaper (0.83), 112-capture-video-frame (0.85): SSIM image similarity, never exactly 1 |
| **Swapped** (4) | 032-compare-iphones → **077-corresponding-scholar-url** (Apple redirects the compare URL to the home page) · 042-black-sale-coffee-makers → **039-manchester-forecast** (Google Shopping no longer shows the graded filter chips) · 046-restore-tripadvisor-tab → **113-add-folders-workspace** (every tab times out, Airbnb redirects to `.com.sg`) · 069-linux-ls-tutorial → **071-paste-image-docx** (grader's OCR reads a clean image as empty, on Mac and x86) |

All four replacements passed the oracle (`results/oracle-gate/reserve-x86/`). Causes and evidence per swap: [`configs/subset_amendments.json`](../configs/subset_amendments.json), now `"frozen": true`. The final list per family is in the [README](../README.md#evaluation-subset). Report these numbers in the method section: oracle ceiling on the final subset is 35 full passes + 2 partial (0.83, 0.85) + 3 known reference bugs.

**How the swaps are applied.** `task_subset.json` and `eval_tasks.args` stay exactly as sampled (fingerprint `08cef024…`). `scripts/task_list.py eval` applies the amendments (and refuses any swap that isn't the next unused reserve of the family), and `harbor_run.sh --split eval` runs that list. `--split reserve` exists only for oracle checks of replacements.

---

## 3. Decisions already made

| Decision | Where it's documented |
|---|---|
| Baselines B0 and E run stock mini-swe-agent 2.4.6 with **default settings** (no step or cost cap) | architecture §2, §6; CLAUDE.md |
| Our variants (C3 on) run under a fixed per-task budget: 50 steps and **B_task = $0.01**, sized to the step cap (50 × ~11k prompt tokens × $0.018/M). V-E: **$0.0167** (120b/20b price ratio 1.67). A multiple of B0's median spend was rejected because B0 mostly stops early on format errors ($0.00019 median) | architecture §5 (C3), §6; `docs/model_selection.md` |
| **V-E** (our harness with the expensive model) is required, for 11 configurations in total | architecture §2 |
| C2 includes separate `read_file` / `write_file` / `edit_file` / `search` tools | architecture §5 |
| Models frozen 2026-10-13: **gpt-oss-20b on Darkbloom** (base), **gpt-oss-120b on Venice** (expensive), reasoning effort low, max_tokens 8192, no provider fallback. Qwen3-Coder-30B rejected (25× the cost of 20b) | `configs/models/`, `configs/pricing.json`, `docs/model_selection.md` |
| B0/E keep stock behaviour, including ending on `RepeatedFormatError` when gpt-oss answers in plain text; C0 and C2 target this | `docs/model_selection.md`, architecture §13 |
| Each C2/C4/C5 is its own plugin (`harness/components/{tools,recovery,submit_gate}.py`, factory `build_hook`) so each can be ablated alone | `docs/harness_core.md`, `configs/harness/` |
| All task images build as `linux/amd64`; one trial at a time unless memory allows more | README, `harbor_run.sh` |
| Oracle-gate swaps only for infrastructure/environment failures; subset frozen 2026-10-10 | architecture §10.1, `subset_amendments.json` |
| `CLAUDE.md` is for developers; `agent_instructions.md` is the evaluated agent's prompt | both files |

**Open:** how the cost report treats calls with unknown usage (Ulfa's collector rejects them; the gateway logs them as `null`); `guardrails.md` §8 (needs the lecture slides).

---

## 4. Roles and next steps

| Person | Role | Next deliverable |
|---|---|---|
| Person | Role | Done | Next |
|---|---|---|---|
| Rohit | Lead: infrastructure, integration, C0 prompt, freeze, presentation | Oracle gate, subset freeze, C0 prompt v3, all 11 harness configs, `run_all_configs.py` | Review C2/C4/C5 when they land; dev smoke test of V; tag harness v1 Fri 16; run schedule; lecture slides to Isha |
| Abin | Harness core: agent, container adapter, gateway and logs, H0 parity, C1, C3 | Core, gateway, C1, C3, guardrail integration, leak gate (41 tests) | Live H0 on the 10 dev tasks vs Ulfa's B0 pilot; then C1 alone and C3 alone (note where C3 stops) |
| Isha | Guardrails with tests, C2/C4/C5, task-leak check, false-positive review, guardrails §8 | Guardrails and leak check integrated on `main`; C2/C4/C5 plugins, 99 passing offline tests, and V factory preflight on pushed `isha/c2-c4-c5`; partial-trajectory review and collector regression tests documented | Restore benchmark checkout and complete task-leak scan and approved dev smoke test; request Abin/Rohit review; false-positive review when guardrail events are available; §8 after lecture slides |
| Ulfa | Price table, model pilot, B_task, cost and statistics scripts, results section | Pricing, pilots, frozen model pair, `collect_costs.py` prototype | Make `collect_costs.py` read the harness `calls.jsonl`, including `null` usage; then `analyze.py` and `plot_pareto.py` |

Harness v1 freezes **Fri 16 Oct**, eval runs **16–19 Oct**, report **by 22 Oct**, presentation **23 Oct**.

**Running experiments.** `scripts/run_all_configs.py` runs a list of configurations task by task, one at a time, through `harbor_run.sh`:

```bash
uv run --frozen python scripts/run_all_configs.py --split dev --task-id 106-create-charles-ssh-user --configs B0,H0 --run-name smoke-b0-h0 --job-budget-usd 0.05 --dry-run
```

Drop `--dry-run` and set `CONFIRM_PAID=1` (plus `CONFIRM_EVAL=1` on eval) once the run and its cost are agreed. Harness configurations need `--job-budget-usd`, the per-run kill switch shared by every harness trial in the run; B0 and E have no cap by design and rely on the key's credit limit.

Things learned on x86 that matter for everyone's runs:

- **Browser tasks depend on live sites.** Three of the four swaps were websites that changed or redirect from Singapore. If a browser task fails on one laptop but passed the oracle here, look at the trial's `artifacts/` before blaming the harness.
- **Linux/WSL hosts need `umask 000`** (now set in `harbor_run.sh`). Without it the task's `agent` user can't write Harbor's log files and every trial ends without a reward. Anyone writing a new runner must keep this.
- Image builds dominate time: 1–15 min per task on first build (Scientific and LibreOffice images are the slowest).

---

## 5. Setting up a laptop

macOS and Linux: follow the README "Team Setup". Windows: everything runs inside **WSL2 (Ubuntu)**; tested on 2026-10-10 on a 16 GB Windows 11 laptop. `data/` and `jobs/` are never pulled from git.

### Step 1: Windows prerequisites (once)

At least 16 GB RAM, 40 GB free on `C:`, virtualisation enabled in the BIOS, and Docker Desktop installed.

1. In PowerShell, install Ubuntu and create your Linux user when it asks:

   ```powershell
   wsl --install -d Ubuntu
   ```

2. Docker Desktop → Settings → Resources → **WSL integration**: turn on **Ubuntu**, Apply & Restart.

3. Give Docker 10 GB. On WSL2, Docker's memory comes from `C:\Users\<you>\.wslconfig`, **not** the Docker Desktop slider. Create that file with:

   ```ini
   [wsl2]
   memory=10GB
   ```

4. Apply it: quit Docker Desktop, run the command below, then start Docker Desktop again. `docker info` should then report about 10 GB (`MemTotal` ≈ 10.4e9).

   ```powershell
   wsl --shutdown
   ```

### Step 2: Inside Ubuntu (once)

Ubuntu already has git, curl and python3. Install uv and put it on your path:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

```bash
source $HOME/.local/bin/env
```

Check Docker is reachable (prints a version):

```bash
docker version --format '{{.Server.Version}}'
```

### Step 3: Code and benchmark (once)

Clone into the Linux home, **not** under `/mnt/c` (a Windows checkout gets CRLF line endings and the scripts fail):

```bash
cd ~ && git clone https://github.com/Roh00t/PE6203_Cost-Aware-Harness-Optimization.git
```

```bash
cd ~/PE6203_Cost-Aware-Harness-Optimization && uv sync --frozen
```

```bash
git clone https://github.com/facebookresearch/TUA-Bench data/TUA-Bench
```

```bash
git -C data/TUA-Bench checkout 3497fd320abcafaf4797424192c891a593fd7964
```

About 0.9 GB of assets, roughly 10 minutes:

```bash
(cd data/TUA-Bench && uv sync --frozen && uv run setup-env)
```

```bash
cp .env.example .env
```

Then put **your own** `OPENROUTER_API_KEY` (created with a credit limit) in `.env`. Oracle runs need no key.

### Step 4: Check the setup

All four must print `OK`:

```bash
python3 scripts/check_assets.py configs/eval_tasks.args
```

```bash
python3 scripts/check_assets.py configs/dev_tasks.args
```

```bash
uv run python scripts/check_harbor_filter.py configs/eval_tasks.args
```

```bash
uv run python scripts/check_harbor_filter.py configs/dev_tasks.args
```

Sampled fingerprint, must print `08cef02483250faee37a4e7d599fe9c8998b8ca256dfeb3de8455babf0687524`:

```bash
python3 scripts/sample_tasks.py --out-dir /tmp/subset-check | grep fingerprint
```

Final eval fingerprint, must print `973635ea4e6a477e2fbfffd1045494cb69e0678c02ceea2276c56c63fa0468b8`:

```bash
python3 scripts/task_list.py eval --fingerprint
```

Smoke test, free, about 3 minutes, expect reward 1.0:

```bash
bash scripts/harbor_run.sh --split dev --mode oracle --only 106-create-charles-ssh-user -- --job-name smoke
```

### Step 5: Claude Code

Start Claude Code in `~/PE6203_Cost-Aware-Harness-Optimization` (inside WSL, or from Windows with commands run through `wsl -d Ubuntu -- …`) and give it the first message suggested at the top of this file.
