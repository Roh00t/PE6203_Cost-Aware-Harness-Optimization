# Eval results: all 11 configurations on the 40 eval tasks

Run by Rohit on a Windows 11 laptop (WSL2, Docker 10 GB, x86), 25–27 October 2026. Harness code `harness-v1` (`6c87103`); runner at `72ecb6f` or later (adds the B0/E install pin below). One run per configuration and task, task-major order, `--n-concurrent 1`, one shared per-run spend cap (`--job-budget-usd 1.00`). Final eval fingerprint `973635ea…`. The folder keeps its first name (`rohit-eval-pass1`) because all three passes share one run name.

| Pass | Configurations | When |
|---|---|---|
| 1 | B0, E, H0, V, V-E | 25–26 Oct |
| 2 | H0+C5, H0+C4, H0+C1 | 26 Oct |
| 3 | H0+C0, H0+C2, H0+C3 | 26–27 Oct |

```bash
CONFIRM_PAID=1 CONFIRM_EVAL=1 uv run --frozen python scripts/run_all_configs.py --split eval --configs <pass configs> --run-name rohit-eval-pass1 --job-budget-usd 1.00 --keep-going
```

## Coverage

**438 of 440 trials** (11 configurations × 40 tasks) finished with a verifier reward. The two exceptions are **H0+C0 on tasks 004 and 099**: the Docker image build failed with `error getting credentials` after WSL socket timeouts (infrastructure, not a task result). They have no reward and no call log; rerun them and re-export `h0-c0` to complete the table.

Infrastructure failures that were rerun are **kept** as archived attempts (folders `<task>.errored-<time>` or `<task>.interrupted-<time>`); they are never scored:

| Cause | Trials | Fix |
|---|---|---|
| B0/E crashed on their first model call: `ModuleNotFoundError: No module named 'mcp'`. Harbor installs stock mini-swe-agent 2.4.6 in the container with an unpinned `uv tool install`, and a litellm release after the 13 Oct pilot imports `mcp` without installing it | 19 (all B0/E trials of the first 9 tasks) | Runner passes `--ae UV_EXCLUDE_NEWER=2026-10-13` to B0/E only, so the container installs the dependency snapshot the dev pilot validated. Agent code and settings stay stock. See `CLAUDE.md`, third freeze exception |
| Docker could not reach Docker Hub (network drop) while building task images | 7 (075 in all pass-1 configurations, 074 in V and V-E) | Rerun |
| OpenRouter rate limit exhausted the gateway's retries | 1 (077 in V-E) | Rerun |
| Run stopped by hand during the fix above | 1 (037 in B0) | Rerun |

## Results

From `scripts/analyze.py` and `scripts/plot_pareto.py` on this whole folder. Full tables, `analysis.json` and both Pareto plots: [`results/analysis/eval/rohit-eval-pass1/`](../../analysis/eval/rohit-eval-pass1/). Paired bootstrap over tasks, 10,000 samples, seed 42; comparisons use only tasks scored in both configurations. Costs are agent inference at the frozen table prices (`configs/pricing.json`); verifier costs excluded. "≥" marks a lower bound (some calls with unknown usage).

### Headline configurations

| Config | Model | Mean reward | Family-reweighted | Known cost per task |
|---|---|---|---|---|
| B0 (stock harness) | gpt-oss-20b | 0.089 | 0.086 | $0.00071 |
| H0 (our loop, no components) | gpt-oss-20b | 0.131 | 0.145 | ≥ $0.00084 |
| **V (full harness)** | gpt-oss-20b | **0.164** | **0.143** | ≥ $0.00119 |
| E (stock harness) | gpt-oss-120b | 0.169 | 0.116 | $0.00140 |
| V-E (full harness) | gpt-oss-120b | 0.260 | 0.219 | ≥ $0.00230 |

| Comparison | Mean reward difference | 95 % CI | Wins / ties / losses |
|---|---|---|---|
| V − B0 | +0.075 | +0.008 to +0.158 | 6 / 33 / 1 |
| V − E | −0.004 | −0.113 to +0.107 | 5 / 31 / 4 |
| V-E − B0 | +0.170 | +0.045 to +0.304 | 10 / 29 / 1 |
| V-E − E | +0.091 | −0.013 to +0.203 | 6 / 33 / 1 |
| E − B0 | +0.079 | −0.012 to +0.183 | 5 / 34 / 1 |
| H0 − B0 | +0.042 | −0.008 to +0.108 | 3 / 36 / 1 |

The full harness on the cheap model (V) is clearly better than the default harness on the same model (B0), and statistically level with the expensive model on the default harness (E) at a lower known cost per task. Weighted to the full benchmark's family mix (Office 46, Web 22, System 19, Scientific 17, Multimedia 16 out of 120), V is ahead of E: E's successes are concentrated in Scientific and Multimedia (0 in Office, Web and System), while V scores in all five families. The harness also helps the stronger model (V-E vs B0). Ties dominate because most tasks are failed by every configuration.

### Ablations: each component alone on top of H0

| Config | Component | Tasks paired with H0 | Mean reward | Δ vs H0 | 95 % CI | W / T / L | Known cost per task |
|---|---|---|---|---|---|---|---|
| H0+C0 | Task-appropriate prompt | 38 | 0.166 | +0.046 | 0.000 to +0.110 | 4 / 34 / 0 | ≈ $0.00033 (38 tasks; 2 trials without a call log) |
| H0+C1 | Context management | 40 | 0.079 | −0.052 | −0.143 to +0.029 | 2 / 34 / 4 | ≥ $0.00077 |
| H0+C2 | Tool interface and validation | 40 | 0.176 | +0.046 | −0.046 to +0.137 | 4 / 35 / 1 | ≥ $0.00191 |
| H0+C3 | Budget caps and awareness | 40 | 0.143 | +0.013 | −0.041 to +0.079 | 2 / 37 / 1 | $0.00077 |
| H0+C4 | Failure recovery | 40 | 0.118 | −0.012 | −0.092 to +0.063 | 2 / 36 / 2 | $0.00095 |
| H0+C5 | Pre-submission gate | 40 | 0.106 | −0.024 | −0.129 to +0.083 | 3 / 33 / 4 | $0.00111 |

Reading, with one run per configuration and wide intervals: **C0 (the prompt) is the clearest single gain**: +0.046 with no losses, and it roughly halves the number of model calls (247 against H0's 496), so it is also the cheapest configuration per task. **C2 (tools)** gives a similar reward gain at about twice H0's cost, because its longer format-error allowance keeps runs going. **C3** is neutral on reward and slightly cheaper. **C1, C4 and C5** are slightly negative alone; C1's drop (context condensing) is the one to inspect in the trajectories. The full harness V (+0.033 over H0) gains less than C0, C2 or C3 alone (+0.046, +0.046, +0.013), so the components overlap or interfere rather than add up; C1's negative effect may be part of the reason. No single ablation is significant at 95 %.

### Pareto frontier and cost policy

**Unknown-cost policy (decided 2026-10-26).** Calls with unknown usage (H0 3, V 2, V-E 7, H0+C0 1, H0+C1 3, H0+C2 2) are provider rate-limit rejections (HTTP 429) with no reported cost; affected costs are reported as lower bounds. Two plots are provided:
- `pareto` (strict: lower-bound points excluded): frontier B0, H0+C3, E.
- `pareto_include_lower_bounds` (lower-bound points admitted and labelled): frontier, by cost, B0, H0+C3, V, E, H0+C2, V-E. Use this one in the report, with its note.

H0+C0 is not on either frontier yet only because it has 38 of 40 tasks; after the two reruns it is likely to be (high reward, lowest cost).

**Harness overhead:** no harness-made model calls ($0). Harness-injected prompt text (status lines, nudges, recovery and gate messages) is estimated at about 17 % of V's and 16 % of V-E's known cost.

### Still open

- **Rerun H0+C0 on 004 and 099**, re-export `h0-c0`, rerun `analyze.py` and both plots.
- **H0 vs B0 parity:** H0 is a little higher than B0 (+0.042, CI includes 0). Check per task before calling it parity (architecture §10.2).
- Single run per configuration: repeats would narrow the intervals if time allows (architecture §10.3).

## Layout

`<config>/<task>/<task>__<trial-id>/`: `result.json`, `config.json`, `trial.log`, `agent/` (harness configs: `calls.jsonl`, `events.jsonl`, `mini-swe-agent.trajectory.json`; B0/E: the stock trajectory), `verifier/` (`reward.txt`, `test-stdout.txt`), small JSON/TXT `artifacts/`. Config folders: `b0`, `e`, `h0`, `v`, `v-e`, `h0-c0` … `h0-c5`. Browser profiles, images and files over 2 MB were left out by `scripts/export_run.py`. Per-configuration `summary.json` is from `scripts/summarize_run.py`.
