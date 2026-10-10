# Project Status and Handoff

Last updated **2026-10-10 evening** (Rohit's Windows laptop, WSL2). Read this first when picking the project up on another machine or in a new Claude Code session, then [`CLAUDE.md`](../CLAUDE.md) and [`system_architecture.md`](../system_architecture.md).

> **For a new Claude Code session:** this file holds the context of the earlier sessions. Start with: *"Read docs/STATUS.md, CLAUDE.md and system_architecture.md, then continue from 'Next steps'."*

---

## 1. Where the project stands

| Area | Status |
|---|---|
| Evaluation subset | **Done and frozen** (2026-10-10). 40 eval + 10 dev tasks. Sampled fingerprint `08cef024…`; after the oracle-gate swaps the **final eval fingerprint is `973635ea…`** (§2) |
| Run tooling | **Done.** `scripts/harbor_run.sh` (per-task jobs, pause/resume, `--only`, `--rerun`, `--split dev|eval|reserve`, asset/memory/disk checks, paid-run gates), `task_list.py`, `summarize_run.py`, `export_run.py`. Works on macOS and on Windows via WSL2 |
| Design docs | **Done**, checked line by line against the brief. `guardrails.md` §8 waits for the lecture slides |
| Dev oracle check | **Done: 9/10.** `100-name-mountain-photos` fails because of a bug in the benchmark's reference solution (agents can still solve it). Logs: `results/oracle-gate/dev-mac*/` |
| Eval oracle gate | **Done.** 40/40 settled on Mac + x86, 4 tasks swapped for reserves that pass (§2). Logs: `results/oracle-gate/eval-mac/`, `eval-x86/`, `reserve-x86/` |
| Model choice, B_task, harness code, experiments, report | Not started. Owners and dates in §4 |

Overall about **32 %** of the weighted plan (foundations done; harness, experiments and report are the remaining 68 %). Model spend so far: **$0.00**.

Team progress page: https://claude.ai/artifact/D1a8FLLj5aqiAAeXWSBWSN (still shows Fri 9 Oct numbers)

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
| Our variants run under a fixed per-task budget: 50 steps and **B_task** = 2× B0's median per-task cost on the dev pilot | architecture §5 (C3), §6 |
| **V-E** (our harness with the expensive model) is required, for 11 configurations in total | architecture §2 |
| C2 includes separate `read_file` / `write_file` / `edit_file` / `search` tools | architecture §5 |
| Model pilot uses **B0** on the dev split (no code needed) | architecture §7.3 |
| Shortlist: gpt-oss-20b (base) / gpt-oss-120b (expensive); final pick from the pilot | architecture §7.2 |
| All task images build as `linux/amd64`; one trial at a time unless memory allows more | README, `harbor_run.sh` |
| Oracle-gate swaps only for infrastructure/environment failures; subset frozen 2026-10-10 | architecture §10.1, `subset_amendments.json` |
| `CLAUDE.md` is for developers; `agent_instructions.md` is the evaluated agent's prompt | both files |

**Open:** final model pair and B_task (Ulfa, after the pilot); `guardrails.md` §8 (needs the lecture slides).

---

## 4. Roles and next steps

| Person | Role | Next deliverable |
|---|---|---|
| Rohit | Lead: infrastructure, integration, C0 prompt, freeze, presentation | Oracle gate **done**. Next: kickoff Mon 12 (three interfaces), multi-config job runner, lecture slides to Isha |
| Abin | Harness core: agent, container adapter, gateway and logs, H0 parity, C1, C3 | Laptop setup now; hook interfaces by Tue 13 Oct, H0 parity Wed 14 |
| Isha | Guardrails with tests, C2/C4/C5, task-leak check, false-positive review, guardrails §8 | Laptop setup now; guardrail rules + leak check (no dependencies) this weekend |
| Ulfa | Price table, model pilot (B0 on dev), B_task, cost and statistics scripts, results section | Laptop setup now; `pricing.json` and pilot (~$0.30, dev split only), frozen model configs by Mon 12 Oct |

Kickoff on **Mon 12 Oct** agrees three interfaces: loop hook points, log fields, and the harness config format. Harness v1 freezes **Fri 16 Oct**, eval runs **16–19 Oct**, report **by 22 Oct**, presentation **23 Oct**.

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
