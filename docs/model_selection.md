# Model selection — 13 October 2026

## Selected pair
- Base: openai/gpt-oss-20b, pinned to Darkbloom.
- Expensive: openai/gpt-oss-120b, pinned to Venice.
- Both retain the tested low reasoning effort and max_tokens 8192.
- Temperature and seed remain unspecified, as in the GPT-OSS pilots.
- Provider fallback remains disabled.

## Selection evidence
| Candidate | Dev mean reward | Table cost for 10 tasks (USD) | Submitted |
|---|---:|---:|---:|
| GPT-OSS-20b / Darkbloom | 0.200 | 0.006255306 | 2/10 |
| Qwen3-Coder-30B / SiliconFlow | 0.31866367137355584 | 0.159162220 | 10/10 |
| GPT-OSS-120b / Venice | 0.366 | 0.011024880 | 0/10 |

The base selection follows architecture section 7.3:
choose the cheapest tested base candidate with non-trivial success.
Qwen submitted reliably but cost 25.44 times as much as GPT-OSS-20b.
The DeepInfra diagnostic did not improve rewards on the three tested tasks.

## Baseline behaviour
Keep stock mini-swe-agent 2.4.6 prompts and behaviour for B0/E.
Do not repair their plain-text termination failures.
Harbor overrides stock mode and cost-limit settings at runtime.
No C3 budget or step cap is introduced into B0/E by this freeze.

## Harness budget decision
Retain B_task = USD 0.01 and a 50-step allowance for configurations
with C3, following the lead's revised instruction.
The rationale is approximately 50 * 11000 input tokens * USD 0.018/M
= USD 0.0099 in input cost. Output tokens also consume the dollar cap;
this estimate does not guarantee that all 50 steps are affordable.
The earlier twice-median rationale is superseded.
Architecture section 6 is to be updated by the project lead.

## Limitations
These are single-trial dev pilots, not final eval results.
GPT-OSS pilots had high RepeatedFormatError rates.
Original task 009 runs lacked the Gemini judge key.
Separate GPT-OSS reruns produced missing or empty PNGs.
The Qwen task 009 run successfully executed Gemini judge checks.
Verifier judge costs are separate from the agent table costs above.
The expensive baseline cost requirement must be checked against
the best harness configuration after evaluation.

## Integration
Each YAML retains the full tested stock configuration.
The shared model settings are under the model section.
Keep these settings identical across variants using the same model.
