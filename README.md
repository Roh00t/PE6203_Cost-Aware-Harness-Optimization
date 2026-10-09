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

* **`claude.md` (or `agent_instructions.md`)**: The core operational playbook. This acts as the agent's procedural memory, containing the system prompt, the format for emitting Bash commands, rules for reading standard output (`stdout`), and the strict criteria for when the agent is allowed to declare a task "complete."

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
* **Eval fingerprint:** `08cef02483250faee37a4e7d599fe9c8998b8ca256dfeb3de8455babf0687524`
* **Substitution rule:** before any model run, the oracle agent runs on all 40 tasks. A task that fails for an infrastructure reason is replaced by the next reserve in its family and logged in [`configs/subset_amendments.json`](configs/subset_amendments.json). The subset is frozen once the first model run starts.
* **Reporting:** the headline success rate is the subset mean (equal weight per family). We also report a family-reweighted estimate (46/22/19/17/16 ÷ 120) as a projection to the full benchmark.

| Family | Eval tasks |
|---|---|
| Multimedia & Design | 008-find-bird-chase-frames, 076-make-src-gif-clip, 080-convert-novel-epub, 088-extract-presenter-photos, 101-rearrange-warm-tiles, 110-rotate-macintosh-video, 111-set-video-wallpaper, 112-capture-video-frame |
| Office & Productivity | 016-count-invoice-pivot, 068-strike-first-two-lines, 069-linux-ls-tutorial, 074-apa-references-review, 087-spreadsheet-to-doc-table, 102-daily-email-report, 116-bottom-left-page-numbers, 117-comma-text-to-table |
| Scientific & Engineering | 000-count-nuclei, 004-place-heater-for-sensors, 006-extract-gym-auditorium, 011-epw-parquet-check, 015-gym-auditorium-sim, 019-prostate-red-overlay, 075-nuclei-locations, 114-nuclei-csv-open |
| System & Software Operations | 046-restore-tripadvisor-tab, 047-set-bing-search, 052-vignette-filter-window, 057-set-undo-steps-100, 073-force-quit-frozen-doc, 085-webext-happy-scaffold, 089-install-recommended-exts, 115-remove-explorer-find-key |
| Web & Information | 032-compare-iphones, 036-license-eligibility, 037-electric-cars-under-50k, 040-seattle-ny-miles-flight, 041-baby-name-carl, 042-black-sale-coffee-makers, 099-professor-contact-info, 105-search-cell-b6 |

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

## Running Locally

**One-time setup**

1. Docker Desktop → Settings → Resources: **Memory ≥ 10 GB** (the Scientific & Engineering tasks request 8 GB each), CPUs ≥ 6, and enough disk for the task images.
2. `cp .env.example .env` and set `OPENROUTER_API_KEY`. Use a dedicated key with a credit limit.
3. `(cd data/TUA-Bench && uv run setup-env)` downloads the task assets.

**Run** (host, recommended):

```bash
scripts/harbor_run.sh --agent oracle --job-name oracle-gate
```

**Run** (same toolchain in a container, from the repo root):

```bash
docker compose run --rm harness scripts/harbor_run.sh --agent oracle --job-name oracle-gate
```

`scripts/harbor_run.sh` refuses to start unless all of these hold:

* the TUA-Bench checkout matches the subset's commit and has no modified tasks or verifiers;
* Harbor resolves exactly the subset's tasks;
* the Docker VM has enough memory for the largest task at the chosen concurrency.

It then overrides two Harbor defaults:

* `--n-concurrent 1` instead of 4. Four 8 GB trials would run out of memory on a 16 GB machine.
* `--no-delete` instead of `--delete`. Harbor's default deletes each task image after every trial, so every configuration would rebuild every image.

Task images are built for `linux/amd64` on every machine. Several images are amd64-only, and using one architecture keeps arm64 Macs and x86 teammates on identical environments. Set `SPLIT=dev` for harness development and model pilots. The eval split is for recorded runs only.
