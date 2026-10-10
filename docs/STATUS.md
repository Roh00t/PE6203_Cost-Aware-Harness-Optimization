# Project Status and Handoff

Last updated **2026-10-10** (Rohit's Mac). Read this first when picking the project up on another machine or in a new Claude Code session, then [`CLAUDE.md`](../CLAUDE.md) and [`system_architecture.md`](../system_architecture.md).

> **For a new Claude Code session:** this file holds the context of the earlier sessions. Start with: *"Read docs/STATUS.md, CLAUDE.md and system_architecture.md, then continue from 'Next steps'."*

---

## 1. Where the project stands

| Area | Status |
|---|---|
| Evaluation subset | **Done.** 40 eval + 10 dev tasks, fingerprint `08cef024…` ([README](../README.md#evaluation-subset)) |
| Run tooling | **Done.** `scripts/harbor_run.sh` (per-task jobs, pause/resume, `--only`, `--rerun`, asset/memory/disk checks, paid-run gates), `summarize_run.py`, `export_run.py` |
| Design docs | **Done**, checked line by line against the brief. `guardrails.md` §8 waits for the lecture slides |
| Dev oracle check | **Done: 9/10.** `100-name-mountain-photos` fails because of a bug in the benchmark's reference solution (agents can still solve it). Logs: `results/oracle-gate/dev-mac*/` |
| Eval oracle gate | **In progress: 28 of 40 settled, 12 to run on an x86 machine** (§2) |
| Model choice, B_task, harness code, experiments, report | Not started. Owners and dates in §4 |

Team progress page: https://claude.ai/artifact/D1a8FLLj5aqiAAeXWSBWSN

---

## 2. Eval oracle gate (reference solutions on the 40 eval tasks)

Mac run `eval-oracle-gate`, exported to `results/oracle-gate/eval-mac/`.

| Group | Tasks | Cause | Decision |
|---|---|---|---|
| Passed (26) | 000, 006, 008, 011, 015, 016, 037, 040, 041, 047, 052, 057, 068, 073, 074, 075, 076, 080, 085, 087, 088, 089, 099, 101, 102, 117 | n/a | Locked in |
| Reference-solution bug (2) | 004-place-heater-for-sensors, 019-prostate-red-overlay | The solution reads `/tests/reference/…`, which Harbor only uploads after the agent finishes | **Keep.** Not an infrastructure failure, and agents can still solve them |
| Network outage on the Mac (7) | 105-search-cell-b6, 110-rotate-macintosh-video, 111-set-video-wallpaper, 112-capture-video-frame, 114-nuclei-csv-open, 115-remove-explorer-find-key, 116-bottom-left-page-numbers | Internet dropped ~17:14 SGT (Docker could not resolve `registry-1.docker.io`) | **Rerun** on x86 |
| Browser/OCR failures on the Mac (5) | 032-compare-iphones, 036-license-eligibility, 042-black-sale-coffee-makers, 046-restore-tripadvisor-tab, 069-linux-ls-tutorial | Chrome timed out or failed to start (e.g. "Timed out connecting to Chromium over CDP"); Tesseract OCR read a clean image as empty. Most likely Apple Silicon's x86 emulation | **Recheck** on x86 |

**Swap rule (decided by Rohit):** swap an eval task for the next reserve of its family **only for infrastructure/environment failures**. Upstream benchmark bugs stay in and are noted in the report.

**How the x86 results will be read:**
- Passes on x86 → keep the task. Browser and OCR-graded tasks then run on x86 laptops in the eval phase.
- Fails on x86 too → swap it for the next reserve (`configs/task_subset.json` → `families.<family>.reserve`, in order) and log it in `configs/subset_amendments.json`.

After that, set `"frozen": true` in `configs/subset_amendments.json`. No changes to the subset after the first model run.

---

## 3. Decisions already made

| Decision | Where it's documented |
|---|---|
| Baselines B0 and E run stock mini-swe-agent 2.4.6 with **default settings** (no step or cost cap) | architecture §2, §6; CLAUDE.md |
| Our variants run under a fixed per-task budget: 50 steps and **B_task** = 2× B0's median per-task cost on the dev pilot | architecture §5 (C3), §6 |
| **V-E** (our harness with the expensive model) is required, for 11 configurations in total | architecture §2 |
| C2 includes separate `read_file` / `write_file` / `edit_file` / `search` tools | architecture §5 |
| Model pilot uses **B0** on the dev split (no code needed) | architecture §7.3 |
| Shortlist: gpt-oss-20b (base) / gpt-oss-120b (expensive); final pick from the pilot | architecture §7.2 |
| All task images build as `linux/amd64`; one trial at a time unless memory allows more | README, `harbor_run.sh` |
| `CLAUDE.md` is for developers; `agent_instructions.md` is the evaluated agent's prompt | both files |

**Open:** final model pair and B_task (Ulfa, after the pilot); `guardrails.md` §8 (needs the lecture slides).

---

## 4. Roles and next dates

| Person | Role | Next deliverable |
|---|---|---|
| Rohit | Lead: infrastructure, integration, C0 prompt, freeze, presentation | Finish the eval oracle gate on x86 and freeze the subset (§5) |
| Abin | Harness core: agent, container adapter, gateway and logs, H0 parity, C1, C3 | Hook interfaces by Tue 13 Oct, H0 parity Wed 14 |
| Isha | Guardrails with tests, C2/C4/C5, task-leak check, false-positive review, guardrails §8 | Guardrail rules and leak check now; components after Abin's interfaces |
| Ulfa | Price table, model pilot (B0 on dev), B_task, cost and statistics scripts, results section | Pilot and frozen model configs by Mon 12 Oct |

Kickoff on **Mon 12 Oct** agrees three interfaces: loop hook points, log fields, and the harness config format. Harness v1 freezes **Fri 16 Oct**, eval runs **16–19 Oct**, report **by 22 Oct**, presentation **23 Oct**.

---

## 5. Continuing on a Windows laptop

Everything below runs inside **WSL2 (Ubuntu)**. `data/` and `jobs/` are never pulled from git:

- `data/` is rebuilt with the commands in step 3;
- `jobs/` is created fresh by every run;
- curated logs travel through git in `results/`.

### Step 1: Windows prerequisites (once)

You need at least 16 GB RAM, at least 40 GB free on `C:`, and virtualisation enabled in the BIOS.

1. In **PowerShell as administrator**, install WSL with Ubuntu, then reboot and create your Linux user when Ubuntu opens:

   ```powershell
   wsl --install -d Ubuntu
   ```

2. Install **Docker Desktop for Windows**, then set:
   - Settings → General: turn on **Use the WSL 2 based engine**;
   - Settings → Resources → WSL integration: turn on **Ubuntu**.

3. Give Docker enough memory. Create `C:\Users\<you>\.wslconfig` containing the lines below. Use `memory=10GB` if the laptop has exactly 16 GB of RAM.

   ```ini
   [wsl2]
   memory=12GB
   processors=6
   ```

4. Restart WSL, then restart Docker Desktop:

   ```powershell
   wsl --shutdown
   ```

### Step 2: Tools inside Ubuntu (once)

Open the **Ubuntu** app and install git, curl and Python:

```bash
sudo apt update && sudo apt install -y git curl python3
```

Install uv:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Put uv on your path in this terminal:

```bash
source $HOME/.local/bin/env
```

Check that Docker is reachable from WSL. It should print a version, not an error:

```bash
docker version --format '{{.Server.Version}}'
```

### Step 3: Get the code and rebuild `data/` (once)

Clone into your Linux home folder, **not** under `/mnt/c`. Windows folders can break the scripts' line endings and slow Docker down.

```bash
cd ~ && git clone https://github.com/Roh00t/PE6203_Cost-Aware-Harness-Optimization.git
```

Enter the repo and install its Python environment:

```bash
cd ~/PE6203_Cost-Aware-Harness-Optimization && uv sync --frozen
```

Clone the benchmark:

```bash
git clone https://github.com/facebookresearch/TUA-Bench data/TUA-Bench
```

Pin it to the subset's commit:

```bash
git -C data/TUA-Bench checkout 3497fd320abcafaf4797424192c891a593fd7964
```

Install the benchmark's environment and download its assets (~0.9 GB, about 10 minutes):

```bash
(cd data/TUA-Bench && uv sync --frozen && uv run setup-env)
```

Create `.env`. No keys are needed for oracle runs.

```bash
cp .env.example .env
```

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

This must print `eval fingerprint 08cef02483250faee37a4e7d599fe9c8998b8ca256dfeb3de8455babf0687524`:

```bash
python3 scripts/sample_tasks.py --out-dir /tmp/subset-check | grep fingerprint
```

Smoke test (free, about 2 minutes, expect reward 1.0):

```bash
bash scripts/harbor_run.sh --split dev --mode oracle --only 106-create-charles-ssh-user -- --job-name smoke-x86
```

### Step 5: Run the 12 unresolved eval tasks

Free, roughly 30–60 minutes on x86:

```bash
bash scripts/harbor_run.sh --split eval --mode oracle --only 032-compare-iphones,036-license-eligibility,042-black-sale-coffee-makers,046-restore-tripadvisor-tab,069-linux-ls-tutorial,105-search-cell-b6,110-rotate-macintosh-video,111-set-video-wallpaper,112-capture-video-frame,114-nuclei-csv-open,115-remove-explorer-find-key,116-bottom-left-page-numbers -- --job-name eval-oracle-gate-x86
```

To pause, press Ctrl+C. To resume, run the same command. If the network drops, rerun with `--rerun <ids>` (see the README).

### Step 6: Bring the results back through git

Export the run's logs into `results/` (no browser profiles, refuses if it finds an API key):

```bash
python3 scripts/export_run.py jobs/eval-oracle-gate-x86 results/oracle-gate/eval-x86
```

Print the summary table:

```bash
python3 scripts/summarize_run.py jobs/eval-oracle-gate-x86
```

Then commit and push `results/oracle-gate/eval-x86`, and pull on the Mac (or continue on Windows). Next: apply the §2 rule, write `configs/subset_amendments.json`, and freeze the subset.

### Step 7: Continue with Claude Code on Windows

Install Claude Code inside WSL (see https://docs.claude.com/en/docs/claude-code), start it in `~/PE6203_Cost-Aware-Harness-Optimization`, and give it the first message suggested at the top of this file. It reads `CLAUDE.md` automatically. This file gives it the history.
