# Cost-Aware Agent Harness Optimization

**PE6203 Continuous Assessment 2 (CA2): Agentic AI Implementation Project**

## The Problem

The problem we are solving is not a lack of artificial intelligence; it is a lack of operational efficiency.

Meta AI’s TUA-Bench exposes a critical vulnerability in modern agentic workflows. A frontier setup like Claude Code with Claude Opus 4.8 solves only 65.8% of these 120 real-world terminal tasks, yet it burns a massive $173.61 per run doing so. Conversely, cheaper open-weight models crash at a ~47% success rate. Standard wrappers let these lightweight models drown in their own context window, hallucinate tool calls, and loop endlessly on simple terminal errors.

## The Mission

Our mission is to decouple capability from cost. We are building a hyper-efficient, cost-aware agent harness that wraps a cheap, fixed base model and forces it to operate on the accuracy-cost Pareto frontier.

We will prove that a ruthlessly optimized execution loop—one that manages context, intercepts errors, and budgets tokens dynamically—can make a lightweight open-weight model rival an expensive proprietary model.

---

## Tech Stack

To achieve this, we bypass bloated, stateful frameworks (like LangChain or AutoGen) and build on **`mini-swe-agent`**, wired directly into the **Harbor** orchestration framework.

* **The Execution Substrate (Harbor + Docker):** Harbor natively orchestrates TUA-Bench. Every task runs in an isolated, resettable Docker Linux container. This provides a safe, ephemeral sandbox to execute raw terminal commands without risking host system corruption.


* **The Harness Layer (`mini-swe-agent`):** We utilize a radically minimal Python scaffold. Instead of using fragile JSON function-calling, it forces the agent to interact purely via Bash (`subprocess.run`) with a strictly linear history. This gives us complete programmatic control to inject our own state compaction algorithms, budget trackers, and stall detectors directly into the message loop before the model ever sees it.

---

## System Architecture

Our architecture relies on a strict separation of concerns. We separate the agent's cognitive instructions from the runtime execution and safety constraints.

### 1. Documentation & Theoretical Blueprints

* **`system_architecture.md`**: The engineering blueprint. This defines the finite state machine of our harness loop (Assemble Context → Validate → Execute → Write Back) and documents explicit optimization strategies, such as how context history is compressed and massive terminal outputs are offloaded.
* **`guardrails.md`**: The safety and execution boundary. This defines our deterministic intercepts. It outlines blocked commands (e.g., preventing irreversible deletes), sets strict retry limits (e.g., maximum 3 attempts on a malformed command), and dictates the exact error strings the harness will inject if the agent hallucinates a tool.

### 2. Cognitive Prompting & Procedural Memory

* **`agent_instructions.md`**: The evaluated agent's prompt (system prompt, command rules, submission criteria), split into sections that switch on with each harness component. **`CLAUDE.md`** is separate: it holds the rules for people and coding assistants working on this repo.

### 3. The Runtime Implementation

* **`harness.py`**: The brain of the operation. This Python script manages the loop. This is where we write the code to truncate observations, inject the "Remaining Budget: X Tokens" counter into the prompt, and programmatically detect if the agent is stuck in an error loop (e.g., comparing the hash of the current proposed command against the previous three).
* **`evaluate.py`**: The telemetry and benchmarking runner. It fires up the Harbor Docker containers, runs `harness.py` against the TUA-Bench tasks, records the execution-based verifier results, and outputs the raw token/dollar logs needed to plot our final Accuracy-Cost Pareto curve.



---

## Target Optimization Surfaces

This stack gives us absolute programmatic control over every token the model consumes and every command it executes across the five core optimization surfaces:

1. **Context Management**
2. **Tool Interface**
3. **Budget Allocation**
4. **Failure Detection & Recovery**
5. **Pre-Submission Verification**
---

## Evaluation Subset

Every configuration (default-harness baseline, each ablation, our harness, and the expensive-model baseline) runs on the **same 40 tasks**: 8 per task family, from TUA-Bench commit [`3497fd3`](https://github.com/facebookresearch/TUA-Bench/tree/3497fd320abcafaf4797424192c891a593fd7964).

* **Families:** `task.toml` only has a fine-grained `category`, so the five families and 20 subcategories are parsed from the paper's Appendix B ([arXiv 2606.28480v1](https://arxiv.org/html/2606.28480v1)) into [`configs/task_families.json`](configs/task_families.json). The parse is checked against `dataset.toml`, and the population is Office 46 / Web 22 / System 19 / Scientific 17 / Multimedia 16.
* **Sampling:** within each family, tasks are ranked by `sha256("tua-subset-v1:42:<task_id>")`. Ranks 1–8 are the **eval** split, ranks 9–10 the **dev** split (used only for harness development and model pilots), and the rest are ordered **reserves**. Hash ranking gives the same output on Python 3.11, 3.12 and 3.14, which `random.sample` does not guarantee.
* **Eval fingerprint (as sampled):** `08cef02483250faee37a4e7d599fe9c8998b8ca256dfeb3de8455babf0687524`. `sample_tasks.py` must always reproduce it.
* **Substitution rule:** before any model run, the oracle agent runs on all 40 tasks. A task that fails for an infrastructure or environment reason (no agent could pass it on our machines) is replaced by the next reserve in its family, which must pass the oracle too, and logged in [`configs/subset_amendments.json`](configs/subset_amendments.json). Reference-solution bugs that agents can work around, and continuous metrics that score the oracle below 1, stay in.
* **Frozen 2026-10-10** after the oracle gate (Mac + x86): 4 swaps, all live-website or grader failures. **Final eval fingerprint: `973635ea4e6a477e2fbfffd1045494cb69e0678c02ceea2276c56c63fa0468b8`** (`python3 scripts/task_list.py eval --fingerprint`). Logs: [`results/oracle-gate/`](results/oracle-gate/).
* **Reporting:** the headline success rate is the subset mean (equal weight per family). We also report a family-reweighted estimate (46/22/19/17/16 ÷ 120) as a projection to the full benchmark.

Final eval split (swapped-in reserves in **bold**):

| Family | Eval tasks |
|---|---|
| Multimedia & Design | 008-find-bird-chase-frames, 076-make-src-gif-clip, 080-convert-novel-epub, 088-extract-presenter-photos, 101-rearrange-warm-tiles, 110-rotate-macintosh-video, 111-set-video-wallpaper, 112-capture-video-frame |
| Office & Productivity | 016-count-invoice-pivot, 068-strike-first-two-lines, **071-paste-image-docx**, 074-apa-references-review, 087-spreadsheet-to-doc-table, 102-daily-email-report, 116-bottom-left-page-numbers, 117-comma-text-to-table |
| Scientific & Engineering | 000-count-nuclei, 004-place-heater-for-sensors, 006-extract-gym-auditorium, 011-epw-parquet-check, 015-gym-auditorium-sim, 019-prostate-red-overlay, 075-nuclei-locations, 114-nuclei-csv-open |
| System & Software Operations | 047-set-bing-search, 052-vignette-filter-window, 057-set-undo-steps-100, 073-force-quit-frozen-doc, 085-webext-happy-scaffold, 089-install-recommended-exts, **113-add-folders-workspace**, 115-remove-explorer-find-key |
| Web & Information | 036-license-eligibility, 037-electric-cars-under-50k, **039-manchester-forecast**, 040-seattle-ny-miles-flight, 041-baby-name-carl, **077-corresponding-scholar-url**, 099-professor-contact-info, 105-search-cell-b6 |

Swapped out: 032-compare-iphones, 042-black-sale-coffee-makers, 046-restore-tripadvisor-tab, 069-linux-ls-tutorial (causes in `subset_amendments.json`). Oracle below 1 but kept: 004, 019, 110 (reference-solution bugs), 111, 112 (continuous image-similarity metrics).

Dev split: 009-repair-org-chart-layout, 056-move-textbox-left, 020-calculate-period-rate, 086-futian-checkin-addresses, 003-rebuild-energy-model, 033-prostate-volume-est, 072-save-speedtest-results, 106-create-charles-ssh-user, 095-save-apple-searching-page, 100-name-mountain-photos.

### Reproduce

```bash
git clone https://github.com/facebookresearch/TUA-Bench data/TUA-Bench
git -C data/TUA-Bench checkout 3497fd320abcafaf4797424192c891a593fd7964
uv sync --frozen                          # repo env: Python 3.12 + harbor==0.6.3
python3 scripts/extract_families.py       # regenerates configs/task_families.json
python3 scripts/sample_tasks.py           # regenerates configs/task_subset.json + *.args
uv run python scripts/check_harbor_filter.py configs/eval_tasks.args
```

---

## Team Setup (each laptop)

**Prerequisites:** git, [uv](https://docs.astral.sh/uv/getting-started/installation/), and [Docker Desktop](https://www.docker.com/products/docker-desktop/) with **Memory ≥ 10 GB** and **CPUs ≥ 6** (Settings → Resources). Keep **≥ 25 GB of free disk**. macOS and Linux work as-is. On Windows, run everything inside WSL2 (Ubuntu) with Docker Desktop's WSL integration on. Clone into the Linux home folder, not `/mnt/c`: a Windows checkout gets CRLF line endings that break the scripts. On WSL2, Docker's memory is set by `%UserProfile%\.wslconfig` (`[wsl2]` / `memory=10GB`, then `wsl --shutdown`), not by the Docker Desktop slider. Full walkthrough: [docs/STATUS.md §5](docs/STATUS.md#5-continuing-on-a-windows-laptop).

Run these once, from the folder where you keep your repos:

```bash
git clone https://github.com/Roh00t/PE6203_Cost-Aware-Harness-Optimization.git
cd PE6203_Cost-Aware-Harness-Optimization
uv sync --frozen
```

```bash
git clone https://github.com/facebookresearch/TUA-Bench data/TUA-Bench
git -C data/TUA-Bench checkout 3497fd320abcafaf4797424192c891a593fd7964
```

```bash
(cd data/TUA-Bench && uv sync --frozen && uv run setup-env)
```

```bash
cp .env.example .env
```

Then edit `.env`: add **your own** `OPENROUTER_API_KEY`, created with a credit limit. `GEMINI_API_KEY` is optional and is only used by one dev task's grader.

Check the setup. The first four lines must print `OK`, and the sampler must reprint fingerprint `08cef024…`:

```bash
python3 scripts/check_assets.py configs/eval_tasks.args
python3 scripts/check_assets.py configs/dev_tasks.args
uv run python scripts/check_harbor_filter.py configs/eval_tasks.args
uv run python scripts/check_harbor_filter.py configs/dev_tasks.args
python3 scripts/sample_tasks.py --out-dir /tmp/subset-check | grep fingerprint
```

Smoke test, free and about 2 minutes (one small task with its reference solution):

```bash
bash scripts/harbor_run.sh --split dev --mode oracle --only 106-create-charles-ssh-user
```

Notes:

* `data/` is git-ignored. Everyone builds their own copy with the commands above, and nobody commits it.
* `setup-env` downloads about 0.9 GB (Hugging Face, NREL S3, Google Drive) into 14 task folders. It never changes tracked task or verifier files.
* No need to activate `.venv`. `uv run` picks the right environment. If it *is* active, `uv` prints a harmless `VIRTUAL_ENV … does not match` warning inside `data/TUA-Bench`.

---

## Running Locally

```bash
bash scripts/harbor_run.sh --split dev --mode oracle                          # free: reference solutions
bash scripts/harbor_run.sh --split dev --mode oracle --only 003-rebuild-energy-model
bash scripts/harbor_run.sh --split eval --mode oracle --prune-cache -- --job-name eval-oracle-gate
python3 scripts/summarize_run.py jobs/eval-oracle-gate                         # one table for the run
python3 scripts/export_run.py jobs/eval-oracle-gate results/oracle-gate/eval  # curated logs into git
```

* `--split eval` runs the sampled eval split with the oracle-gate swaps in [`configs/subset_amendments.json`](configs/subset_amendments.json) applied (`python3 scripts/task_list.py eval` prints it). `--split reserve` runs unused reserves, oracle or nop only, to check a replacement before it is swapped in.
* `--only ID[,ID…]` runs part of a split.
* `--dry-run` prints the commands after the checks.
* Anything after `--` goes to `harbor run` unchanged.
* `--job-name` names the run, and re-running with the same name **resumes** it, skipping finished tasks.
* Paid agents need `CONFIRM_PAID=1`, and on the eval split also `CONFIRM_EVAL=1`.

Same toolchain in a container, from the repo root:

```bash
docker compose run --rm harness scripts/harbor_run.sh --split dev --mode oracle
```

**Pre-flight checks.** `scripts/harbor_run.sh` refuses to start unless all of these hold:

* the TUA-Bench checkout is at the subset's commit, with no modified tasks or verifiers;
* Harbor resolves exactly the requested tasks;
* every task's downloaded assets exist;
* the Docker VM has enough memory for the largest task.

**Disk policy.** Measured on the dev split: 10 tasks added about 26 GB of Docker build cache, while deleting their images freed nothing on the host. So the run is bounded per task:

1. Each task runs as its own Harbor job under `jobs/<run>/<task>/`.
2. Harbor deletes each trial's image afterwards (`--delete`), and the build cache keeps rebuilds of the same task fast.
3. Before every task the script checks free disk, and stops cleanly below `MIN_FREE_GB` (default 10). A full disk can corrupt Docker's VM.
4. `--prune-cache` shrinks Docker's build cache to `CACHE_KEEP_GB` (default 15) after each task. Docker's cache is shared, so this also evicts other projects' oldest build cache. That cache is regenerable but slow to rebuild, so the flag is opt-in.

**Other defaults:**

* `--n-concurrent 1` instead of Harbor's 4. Four 8 GB trials would run out of memory on a 16 GB machine.
* Task images build for `linux/amd64` on every machine. Several images are amd64-only, and one architecture keeps arm64 Macs and x86 laptops on identical environments.
* Use `--split dev` for harness development and model pilots. The eval split is for recorded runs only.

---

## Disk Use and Cleanup

The runs need disk space, but it's bounded and all of it can be reclaimed. Measured on a Mac on 2026-10-10:

| What | Size | Notes |
|---|---|---|
| Docker build cache and task images | ~12 GB now, est. 15–25 GB peak during eval runs | Each task is a container that Docker builds. Everything Docker stores sits in one virtual disk capped by Docker Desktop (Settings → Resources → Disk usage limit, 60 GB by default), so it cannot grow past that. |
| `.venv` | ~0.7 GB | Repo Python environment |
| `data/TUA-Bench` | ~0.75 GB | Benchmark, downloaded inputs, its own `.venv` |
| `setup-env` download cache in `$TMPDIR` | ~1 GB | Only reused if `setup-env` runs again; safe to delete |
| `jobs/` | MBs | Raw run logs |

During runs, `scripts/harbor_run.sh` stops cleanly if free disk falls below `MIN_FREE_GB` (10 GB). Re-running the same command resumes. `--prune-cache` keeps the build cache under `CACHE_KEEP_GB` (15 GB).

**At the end of the project**, after `results/` is committed, run these from the repo folder to get the space back.

Clear all of Docker's build cache. This also clears other projects' cache: safe, but their next builds will be slower.

```bash
docker builder prune -af
```

Remove the helper images this project pulled or built:

```bash
docker image rm pe6203-harness:local docker:27.5.1-cli ghcr.io/astral-sh/uv:0.11.14 alpine:3.20
```

Delete the benchmark copy, Python environments and raw job logs:

```bash
rm -rf data .venv jobs
```

Delete the `setup-env` download cache:

```bash
rm -f "${TMPDIR:-/tmp}/PE-Video-test-000000.tar" "${TMPDIR:-/tmp}/Task05_Prostate.tar" "${TMPDIR:-/tmp}/comstock-100094-0.parquet"
```

```bash
rm -rf "${TMPDIR:-/tmp}/real-estate-openstudio-comstock-pngs" "${TMPDIR:-/tmp}/cell-profiler"
```

Docker's disk file shrinks on its own within a few minutes. Docker Desktop's "Troubleshoot → Clean / Purge data" removes everything Docker holds, for every project.
