# Eval pass 1: B0, E, H0, V, V-E on the 40 eval tasks

Run by Rohit on a Windows 11 laptop (WSL2, Docker 10 GB, x86), 25–26 October 2026. Harness code `harness-v1` (`6c87103`); runner at `72ecb6f` (adds the B0/E install pin below). One run per configuration and task, task-major order, `--n-concurrent 1`. Final eval fingerprint `973635ea…`.

```bash
CONFIRM_PAID=1 CONFIRM_EVAL=1 uv run --frozen python scripts/run_all_configs.py --split eval --configs B0,E,H0,V,V-E --run-name rohit-eval-pass1 --job-budget-usd 1.00 --keep-going
```

## Coverage

All 200 trials (5 configurations × 40 tasks) finished with a verifier reward. No trial is missing or unscored.

Infrastructure failures were rerun with the same command and are **kept** here as archived attempts (folders named `<task>.errored-<time>` or `<task>.interrupted-<time>`); they are not scored:

| Cause | Trials | Fix |
|---|---|---|
| B0/E crashed on their first model call: `ModuleNotFoundError: No module named 'mcp'`. Harbor installs stock mini-swe-agent 2.4.6 in the container with an unpinned `uv tool install`, and a litellm release after the 13 Oct pilot imports `mcp` without installing it | 19 (all B0/E trials of the first 9 tasks) | Runner passes `--ae UV_EXCLUDE_NEWER=2026-10-13` to B0/E only, so the container installs the dependency snapshot the dev pilot validated. Agent code and settings stay stock. See `CLAUDE.md`, third freeze exception |
| Docker could not reach Docker Hub (network drop) while building task images | 7 (075 in all configurations, 074 in V and V-E) | Rerun |
| OpenRouter rate limit exhausted the gateway's retries | 1 (077 in V-E) | Rerun |
| Run stopped by hand during the fix above | 1 (037 in B0) | Rerun |

## Preliminary results

From `scripts/analyze.py` and `scripts/plot_pareto.py` (Ulfa) at `72ecb6f`, run on the current trials only (archived attempts excluded; see the analysis note below). Paired bootstrap over the 40 tasks, 10,000 samples, seed 42. Costs are agent inference at the frozen table prices (`configs/pricing.json`); verifier costs excluded.

| Config | Model | Mean reward | Known cost per task | Cost complete? |
|---|---|---|---|---|
| B0 (stock harness) | gpt-oss-20b | 0.089 | $0.00071 | yes |
| H0 (our loop, no components) | gpt-oss-20b | 0.131 | ≥ $0.00084 | no: 3 calls with unknown usage |
| V (full harness) | gpt-oss-20b | 0.164 | ≥ $0.00119 | no: 2 calls with unknown usage |
| E (stock harness) | gpt-oss-120b | 0.169 | $0.00140 | yes |
| V-E (full harness) | gpt-oss-120b | 0.260 | ≥ $0.00230 | no: 7 calls with unknown usage |

| Comparison | Mean reward difference | 95 % CI | Wins / ties / losses |
|---|---|---|---|
| V − B0 | +0.075 | +0.008 to +0.158 | 6 / 33 / 1 |
| V − E | −0.004 | −0.113 to +0.107 | 5 / 31 / 4 |
| V-E − B0 | +0.170 | +0.045 to +0.304 | 10 / 29 / 1 |
| V-E − E | +0.091 | −0.013 to +0.203 | 6 / 33 / 1 |
| E − B0 | +0.079 | −0.012 to +0.183 | 5 / 34 / 1 |
| H0 − B0 | +0.042 | −0.008 to +0.108 | 3 / 36 / 1 |

Reading, with one run per configuration: the full harness on the cheap model (V) is clearly better than the default harness on the same model (B0), and statistically level with the expensive model on the default harness (E) at a lower known cost per task. The harness also helps the stronger model (V-E vs B0). Ties dominate because most tasks are failed by every configuration.

**Open before these become final:**
- **Unknown-cost calls** (2–7 per harness configuration, from provider rate limits) make those costs lower bounds, and `plot_pareto.py` excludes lower-bound points from the frontier, so the frontier currently shows only B0 and E. The team policy for reporting them is still open (`docs/STATUS.md`).
- **Analysis note:** `analyze.py` stops with "No model calls found" on the 19 archived B0/E attempts (they crashed before any call) because its cost step runs before it filters archived attempts. The numbers above come from a temporary copy without the archived folders; `analyze.py` should treat a zero-call log in an archived attempt like a missing log.
- **H0 vs B0 parity:** H0 is a little higher than B0 (+0.042, CI includes 0). Check per task before calling it parity (architecture §10.2).
- Passes 2–3 (the six single-component ablations H0+C0…C5) have not been run.

## Layout

`<config>/<task>/<task>__<trial-id>/`: `result.json`, `config.json`, `trial.log`, `agent/` (harness configs: `calls.jsonl`, `events.jsonl`, `mini-swe-agent.trajectory.json`; B0/E: the stock trajectory), `verifier/` (`reward.txt`, `test-stdout.txt`), small JSON/TXT `artifacts/`. Browser profiles, images and files over 2 MB were left out by `scripts/export_run.py`. Per-configuration `summary.json` is from `scripts/summarize_run.py`.
