# CLAUDE.md

Guidance for people and coding assistants working on this repository.

**Project.** PE6203 CA2, Group Project 5: a cost-aware agent harness for TUA-Bench. We maximise the success rate of a fixed, cheap, open-weight model per dollar, and compare against a default-harness baseline and an expensive-model baseline on the accuracy–cost plane.

- Design: [system_architecture.md](system_architecture.md)
- Safety rules: [guardrails.md](guardrails.md)
- Assignment brief: the PDF in the repo root

[agent_instructions.md](agent_instructions.md) is the prompt for the *evaluated agent*. It is not instructions for you: don't follow it, and don't edit it casually, because every token in it is billed on every step.

## Non-negotiables (assessment rules: breaking one invalidates results)

- **Never modify `data/TUA-Bench/`** (tasks, verifiers, `dataset.toml`). `scripts/harbor_run.sh` refuses to run on a modified checkout.
- **No task-specific hard-coding.** Harness code, `configs/harness/` and the agent prompt must never mention a task ID, a file name from a task instruction, or an expected answer. Generic rules only.
- **Fixed model and decoding.** Model, pinned OpenRouter provider, temperature and reasoning effort live in `configs/models/*.yaml` and are identical for every configuration. Once frozen, they never change.
- **Every model call goes through OpenRouter and is logged** (`calls.jsonl`, with `purpose`). An unlogged call is a bug. Costs come from `configs/pricing.json`, never from mini-swe-agent's own cost field.
- **Develop on `SPLIT=dev` only.** The 40 eval tasks are run only for recorded results, never for debugging or tuning.
- **The subset is frozen.** `configs/task_subset.json` changes only through the oracle gate (`configs/subset_amendments.json`), before the first model run. Its eval fingerprint must stay `08cef02483250faee37a4e7d599fe9c8998b8ca256dfeb3de8455babf0687524`.
- **Every harness feature sits behind a component flag (C0–C5)** so it can be ablated alone. The baselines B0 and E use the stock harness, untouched.

## Ask the user first

- Before anything that calls a paid model: `harbor_run.sh` with any agent other than `oracle` or `nop`, pilots, or scripts that query OpenRouter. State the split, configuration, task count and estimated cost.
- Before deleting or pruning Docker images, volumes or build cache, or anything in `jobs/` or `results/`.
- Before changing the subset, the price table, a model config, a budget limit, or a guardrail rule after the dev review.
- Before committing or pushing.

## Commands

```bash
uv sync --frozen                                         # env: Python 3.12 + harbor 0.6.3
scripts/harbor_run.sh --agent oracle --job-name <name>   # free: runs reference solutions (eval split)
SPLIT=dev scripts/harbor_run.sh --agent oracle --job-name <name>
uv run python scripts/check_harbor_filter.py configs/eval_tasks.args
python3 scripts/sample_tasks.py                          # must reproduce the fingerprint above
docker compose run --rm harness scripts/harbor_run.sh …  # same toolchain in a container
```

`harbor_run.sh` checks the TUA-Bench commit, Harbor's resolved task list and Docker memory. It then runs with `--n-concurrent 1 --no-delete` and `DOCKER_DEFAULT_PLATFORM=linux/amd64`.

## Repository map

| Path | What |
|---|---|
| `configs/` | Subset (`task_subset.json`, `*.args`), family labels, amendments. Planned: `pricing.json`, `models/`, `harness/` |
| `scripts/` | Subset generation, Harbor filter check, run wrapper |
| `harness/` | *Planned:* host-side harness (Harbor `BaseAgent` + mini-swe-agent `DefaultAgent` subclass), components C1–C5, guardrails, OpenRouter gateway |
| `data/TUA-Bench/` | Pinned benchmark checkout (git-ignored, read-only) |
| `jobs/` | Raw Harbor output (git-ignored) |
| `results/` | *Planned:* curated, committed logs behind every reported number |

## Conventions

- Python 3.12, type hints, stdlib first. New dependencies go through `uv add` (pinned in `uv.lock`).
- Deterministic before generative: prefer rule-based intercepts to extra model calls. Any model call the harness makes counts as harness overhead and needs `purpose = "harness:<what>"`.
- Guardrail regexes and their messages are defined in `guardrails.md §3`. Keep code and doc in sync, and give every rule a unit test with a positive and a negative example.
- Logs are append-only JSONL, flushed per event, so killed trials keep their data.
- Commit messages explain why. Never commit `.env`, `jobs/` or `data/`.

## Machine notes

- Docker Desktop needs at least 10 GB of memory (Scientific tasks request 8 GB each). Free disk is tight (about 35 GB on the Mac), so prune a task's image only after all its configurations have run.
- On Apple Silicon, task images build and run under amd64 emulation. First builds of Scientific images are slow; the oracle gate shows how slow.
