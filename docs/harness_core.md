# Harness core handoff

This implements Abin's host agent, loop hooks, configuration loader, prompt selection, container adapter, OpenRouter logging, C1 context management and C3 budget management. It is development code, not a frozen evaluation result. No paid API calls were made during implementation.

## Status

- Offline tests exercise the real pinned mini-swe-agent 2.4.6 and Harbor 0.6.3 Python classes with fake model/container responses.
- Scripted H0 comparisons cover successful submission and three consecutive format errors against stock DefaultAgent. This is not measured benchmark parity.
- Live Ubuntu/Docker execution and B0/H0 dev parity remain to be run.
- Integrated Isha's guardrails and leak scanner from branch isha/guardrails, commit 47ff409. The adapter invokes her actual check_command API; G rules apply in every configuration and U rules only when C2 is enabled. Fixed numeric/version false positives and sentence-final filename extraction in the leak scanner, with a regression test.
- C2/C4/C5 are implemented as independent plugins on Isha's `isha/c2-c4-c5` branch. Offline component tests use fake services; no Docker or API calls are needed. Paid dev smoke tests and false-positive review remain pending.
- The user-created configs/harness_core.py outline is retained and is not imported by this package.

## Files and dependencies

The Harbor import path is `harness.agent:CostAwareAgent`. The loop is `harness.loop.HarnessAgent`, a genuine subclass of `minisweagent.agents.default.DefaultAgent`. Runtime dependencies and uv.lock include mini-swe-agent==2.4.6; pytest==8.3.5 is a dev dependency.

From the repository root in Ubuntu:

```bash
uv sync --frozen
LITELLM_LOCAL_MODEL_COST_MAP=True MSWEA_SILENT_STARTUP=1 uv run --frozen python -m pytest tests/test_harness_core.py -q
uv run --frozen python scripts/check_harness.py
```

The final command reports whether a key exists without displaying it. The default guardrail factory now imports successfully. Missing or invalid plugin factories still fail explicitly. Offline tests need no key.

## Configuration

- configs/harness/h0.yaml: stock prompts, 30-second command timeout, no C3 step/cost cap.
- configs/harness/c1.yaml: only C1.
- configs/harness/c3.yaml: only C3; $0.01, at most 50 model-query steps, 180-second command timeout.
- configs/harness/c1_c3.yaml: combined development configuration, not the full V configuration.

The model is loaded from the existing frozen configs/models/base.yaml. No model/provider/decoding or pricing file was changed. Harbor's stock --yolo and --cost-limit 0 overrides are reflected in the custom default loop. H0 keeps the stock missing-tool-call and repeated-format-error behavior. C0 prompt rendering is supported, but prompt content is owned by Rohit.

## Integration contract for Isha

Factories have this signature:

```python
def build_guardrail(config: HarnessConfig, services: Services) -> Hook: ...
def build_hook(config: HarnessConfig, services: Services) -> Hook: ...
```

`Services` gives the container adapter (`execute`, `write_text`), event logger (`write`) and config. `RunState` contains task text, step, measured spending, elapsed seconds and enabled flags. Factories come only from developer-authored YAML; never load a path proposed by a model.

`harness/isha_adapter.py:build_guardrail` now adapts the GuardrailResult return type from Isha's check_command function. The adapter must apply G rules to every configuration, and U rules only with C2. G-SEC-01 logs and permits execution. Do not replace Isha's implementation with duplicated patterns or a Hook that permits everything.

| Hook | Inputs | Return | Timing |
|---|---|---|---|
| before_query | copied history, RunState | list of messages | After C1 builds its view, before API request |
| on_missing_tool_call | raw response dictionary, RunState | feedback string or None | Only when stock parsing reports no tool calls; None preserves stock |
| before_execute | action, RunState | Decision | Guardrail first, then enabled plugins; blocked commands never execute |
| after_execute | action, result, RunState | result dictionary | Plugins first, then C1 offload and C3 status line |
| before_submit | action, RunState | Decision | On a successful command whose first output line is the submission sentinel, before accepting submission |
| execute_tool | action, RunState | result dictionary | For a plugin's advertised non-bash function tool |

A `Decision` has `allowed`, `feedback`, optional `rule_id` and optional `event`. The guardrail decision's event is logged by the loop. Other plugins can log through services.events. An observation dictionary has `output`, `returncode`, `exception_info` and optional `extra`. Set extra.origin='harness' for entirely injected feedback, or extra.harness_chars for an injected suffix. Preserve any existing metadata.

A plugin declares `components = frozenset({'C2'})` (or C4/C5 as appropriate) and optionally function schemas in `tools`. Configure its factory in the YAML `plugins` list. All enabled C2/C4/C5 flags must be backed by plugins; plugins implementing disabled components are rejected. Separate factories are easiest for clean ablations. Plugin schemas must validate arguments before executing tools. C2 should return blocked observations for additional calls after the first so every tool_call_id still receives a result. C2 supplies the missing-tool-call recovery wording; the loop raises its consecutive-format-error allowance to five only with C2 enabled.

Submission gating occurs after a command produces the actual stock completion sentinel, rather than guessing from command text. Deferring it returns feedback to the model and leaves the run open. C5 must bound its gate count as specified in the architecture. U-FMT-04 belongs to C2 and prevents combining submission with other work.

## Container boundary and parity caveats

All model commands execute using Harbor environment.exec; no model command is run on the host. Only the fixed non-secret environment allow-list is passed. Template platform values are read from the container, not the Windows host. C1 observations are written through Harbor upload_file.

Commands use GNU timeout and a streaming Python output drain inside the container. This caps host-visible output at 1 MiB while preserving the shell command's exit status, merged stdout/stderr, heredocs, and container workdir/user. The exact timeout error text and wrapper behavior differ from stock subprocess execution; test these on dev, and report H0 as the port/control rather than claiming byte-for-byte environment parity. Commands returning 124/137 are logged as timed out or killed; an explicit command exit with those codes cannot be distinguished by this wrapper.

Cancellation signals the worker and cancels pending Harbor calls. Python cannot forcibly stop an in-flight blocking HTTP call; an already-started call can finish and be charged after cancellation. No subsequent call is allowed. This is a known limitation to test under Docker.

## Logs and Ulfa's collector

Per attempt, calls.jsonl contains config_id, task_id, trial_id, call_idx, step, ts, purpose, model, provider, provider_expected, prompt_tokens, completion_tokens, reasoning_tokens, cached_tokens, cost_table_usd, cost_reported_usd, finish_reason, error, retries, latency_ms and prompt_chars_by_origin. Requests and credentials are not stored in this log. Full model responses and full retained observations remain in the mini trajectory.

Costs use the frozen full input and completion rates. Reasoning tokens are already part of completion_tokens; cached tokens are already part of prompt_tokens. Neither is added twice. An absent observed provider remains null, with the configured pin in provider_expected; it is not invented as an observed value.

Every HTTP retry is a separate attempt row. Unknown usage is null, never zero. Harbor context.cost_usd is null when any attempt has unknown usage, and metadata contains known_cost_table_usd plus usage_complete=false. Ulfa's current collect_costs.py deliberately rejects null usage. Such logs need reconciliation against provider records or a clearly reported incomplete-cost status; do not silently drop failed attempts. No collector changes were made here.

Prompt origin attribution is character-based, as specified in the architecture, and is an estimate rather than exact token-level attribution. Component suffixes, budget nudges, offload notices, recovery feedback and compaction digests are marked. Additional plugins must preserve/provide attribution metadata.

## Budget semantics

C3 uses the frozen $0.01 task budget. Before sending a request it reserves a conservative input allowance (serialized request UTF-8 bytes plus 4096) and the full frozen max_tokens completion allowance. If that reserve does not fit, the run stops without altering max_tokens. This can stop earlier than a policy based only on spend so far. It is a local token estimate, not a provider-certified maximum: actual excess is logged as reservation_underestimate and must be reviewed; do not claim a mathematically guaranteed billing ceiling. The API key credit limit remains the external spending boundary.

Failed requests retain their conservative reservation, since their cost is unknown. Successful replies settle to measured table cost. A SQLite JobLedger can share a cap across simultaneous host agents: pass both job_budget_usd and job_ledger_path as Harbor agent kwargs. Use the same path for every agent in the job, on a local filesystem. A reserved entry survives a crash and is not automatically refunded. Reuse it only when intentionally resuming that same run. Rohit's multi-config runner should supply the agreed job estimate plus 20%.

## Live validation after integration

1. Run Isha's guardrail/leak-scanner tests plus the core and adapter tests. Run the real-corpus leak scan using Isha's documented CLI.
2. Have the lead agree the dev tasks, configuration and cost estimate before a paid run, as CLAUDE.md requires.
3. Export PYTHONPATH to the repository root so Harbor can import this uninstalled package.
4. Use the existing harbor_run.sh, --split dev, --agent-import-path harness.agent:CostAwareAgent, and --ak config_path=configs/harness/h0.yaml. Supply the agreed job ledger and cap via --ak. Do not change the stock baseline.
5. Preserve logs under a new job name. Compare the same dev tasks against B0, including rewards, exit reasons, command behavior and cost. Compare C1 and C3 independently after H0 works.
6. Mark live parity complete only with actual recorded evidence. Do not tune on eval tasks.

No live-run approval, spend, final eval freeze, commit or push is implied by the offline checks above.
