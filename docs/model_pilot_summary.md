# Model pilot results and handoff — 13 October 2026

Model configurations are frozen. The selected pair and rationale are recorded in
[model_selection.md](model_selection.md). These are dev-pilot results, not final
40-task evaluation results.

## Experimental setup
- Same 10 dev tasks for each main pilot; one trial per model.
- Harbor 0.6.3 and stock mini-swe-agent 2.4.6, with unchanged stock prompts.
- GPT-OSS models: low reasoning effort and max_tokens 8192; temperature and seed
  unspecified, matching the tested settings.
- Qwen: temperature 0 and max_tokens 8192; no reasoning parameter.
- Providers pinned; fallbacks disabled.
- Costs use the listed input/output rates in the price tables. All prompt tokens
  are charged at the normal input rate, including cached tokens. Provider-reported
  charges can therefore differ.
- Agent costs below exclude Gemini verifier calls.

## Main pilots
| Model / provider | Mean reward | Full rewards | Partial rewards | Submitted | RepeatedFormatError | Agent table cost (USD) |
|---|---:|---:|---:|---:|---:|---:|
| GPT-OSS-20b / Darkbloom | 0.200 | 2 | 0 | 2/10 | 8/10 | 0.006255306 |
| Qwen3-Coder-30B / SiliconFlow | 0.319 | 2 | 3 | 10/10 | 0/10 | 0.159162220 |
| GPT-OSS-120b / Venice | 0.366 | 3 | 1 | 0/10 | 10/10 | 0.011024880 |

120b improved task 056 from 0 to 1 and task 033 from 0 to 0.66 versus 20b;
the other eight main-pilot rewards were unchanged. It cost 1.76 times as much.
Qwen cost 25.44 times as much as 20b, although it submitted successfully on
every task. Submitted indicates protocol completion, not a correct task result.

Qwen task 033 used 1,180,753 cumulative prompt tokens and task 095 used 463,852.
Together they accounted for about 74% of its pilot cost. These totals sum all
calls, rather than representing one prompt's length.

## Format-error diagnosis and alternate-provider check
The inspected GPT-OSS termination failures included plain-text summaries or
commands printed in markdown instead of bash tool calls. Stock handling is
preserved for B0/E; planned C0/C2 improvements must be evaluated separately.

In the original 20b pilot, the diagnostic parser found 28 responses with
reasoning but no text or tool call, and zero completely empty responses.
This clarifies the earlier description of "empty replies".

Three dev tasks (003, 020, 086) were rerun with 20b on DeepInfra, retaining the
other model settings. The diagnostic uses its separate
[price table](../configs/pricing-provider-check.json).

| Metric across those three tasks | Darkbloom | DeepInfra |
|---|---:|---:|
| Model calls | 53 | 32 |
| Completely empty responses | 0 | 0 |
| Reasoning-only responses without tools | 14 | 5 |
| All responses without tools | 27 | 15 |
| Mean reward | 0.000 | 0.000 |
| Agent table cost (USD) | 0.003098772 | 0.003724280 |

DeepInfra reduced reasoning-only responses in this sample but did not improve
reward. One trial per task, different trajectories, and endpoint differences
prevent a causal conclusion about Darkbloom. Darkbloom remains the selected
base provider.

## Task 009 and Gemini verifier
The original GPT-OSS task 009 pilots lacked a Gemini key. After adding the key,
both models were rerun as separate trials, preserving the original evidence:
- 20b: missing PNG, reward 0, agent table cost USD 0.000513324.
- 120b: empty PNG, reward 0, agent table cost USD 0.001395000.

These runs failed the initial PNG check and do not demonstrate judge execution.
The Qwen run did execute all four Gemini judge checks:
- required boxes: fail;
- connector quality: fail;
- overlap: pass;
- overall match: fail.
Its PNG existence check passed; the resulting reward was 0.25.

Do not present the main pilots as having identical verifier availability.
Reruns are supplementary evidence, not silently substituted original trials.

## Frozen selection and revised harness budget
- Base: GPT-OSS-20b / Darkbloom, the cheapest tested base candidate with
  non-trivial success under architecture section 7.3.
- Expensive: GPT-OSS-120b / Venice, supported by higher pilot reward and cost.
- Configurations: [base.yaml](../configs/models/base.yaml) and
  [expensive.yaml](../configs/models/expensive.yaml).
- The main price table is marked frozen for evaluation; its original
  2026-10-12 snapshot and rates are preserved. Qwen remains as pilot evidence.
- Retain B_task = USD 0.01 and a 50-step allowance for C3 configurations.
  The lead's revised rationale is approximately
  50 * 11,000 input tokens * USD 0.018/M = USD 0.0099 in input cost.
  Output tokens also consume the cap, so 50 steps are not guaranteed affordable.
- The twice-median budget rationale is superseded. Rohit owns the corresponding
  architecture section 6 update. Budget enforcement belongs to the harness,
  not to this documentation update, and B0/E remain uncapped at runtime.

The expensive baseline's cost must still be checked against the best harness
configuration after evaluation.

## Spend and evidence
There are 35 recorded agent trials: 30 main-pilot trials, 3 provider diagnostics,
and 2 task 009 reruns. The first SSH pilot is already included in the 20b main
pilot and is not counted twice.

Combined agent table cost: USD 0.182075010. This is not the total provider bill
and excludes Gemini judge costs.

- [20b main pilot](../results/pilots/b0-20b-dev/)
- [120b main pilot](../results/pilots/e-120b-dev/)
- [Qwen main pilot](../results/pilots/b0-qwen3-coder-dev/)
- [DeepInfra diagnostic](../results/pilots/b0-20b-deepinfra-check/)
- [20b task 009 rerun](../results/pilots/b0-20b-009-gemini/)
- [120b task 009 rerun](../results/pilots/e-120b-009-gemini/)

## Remaining integration work
- Agree the append-only call/event log interface with Abin: he writes, Ulfa reads.
- Validate accounting for invalid responses, billed retries, and harness overhead.
- Update architecture section 6 through Rohit and implement the budget in C3.
- Decide repeat counts and eval scheduling with the team; additional repeats
  have not been started.
