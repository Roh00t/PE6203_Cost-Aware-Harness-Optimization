# Model pilot results — 12 October 2026

Status: preliminary; model selection and budgets are not frozen.

## Setup
- Same 10 dev tasks, one trial per model.
- Harbor 0.6.3 and stock mini-swe-agent 2.4.6.
- Same stock prompts, low reasoning effort, max_tokens 8192.
- Providers pinned, with fallback disabled.
- Costs use configs/pricing.json; all prompt tokens are charged
  at the listed input rate. Provider-reported charges may differ
  because of caching.

## Results
| Metric | gpt-oss-20b / Darkbloom | gpt-oss-120b / Venice |
|---|---:|---:|
| Mean verifier reward | 0.200 | 0.366 |
| Full-reward tasks | 2 | 3 |
| Partial-reward tasks | 0 | 1 |
| Total table cost (USD) | 0.006255306 | 0.011024880 |
| RepeatedFormatError exits | 8/10 | 10/10 |

120b improved task 056 from 0 to 1 and task 033 from 0 to 0.66.
The other eight task rewards were unchanged.
120b cost 1.76 times as much as 20b in this pilot.

## Preliminary budget
20b median task cost: USD 0.000430974.
Twice the median: USD 0.000861948.
Rounded upward to the nearest cent, as specified in the design:
candidate B_task = USD 0.01.

## Findings and limitations
- High format-error rates need investigation before model freeze.
- Inspected task 020 responses from 20b refused to continue.
- Inspected task 106 responses from 20b described completion or
  printed commands as text instead of calling the bash tool.
- Verifier reward can be positive despite a format-error exit.
- Task 009 has a Gemini-dependent verifier check; confirm its
  availability from verifier logs before final interpretation.
- These are single-run dev results, not 40-task eval results.
- Only one base candidate has been tested so far.

## Decisions for kickoff
1. Select another base candidate to follow the planned 2–3-model pilot,
   or document an agreed change to that selection protocol.
2. Review format errors and confirm final decoding settings.
3. Decide whether to retain the cent-rounded B_task rule.
4. Freeze final models/configs after these decisions.
5. Confirm log fields with the harness team.

## Evidence
- results/pilots/b0-20b-dev/
- results/pilots/e-120b-dev/
- configs/pilots/b0-gpt-oss-20b.yaml
- configs/pilots/e-gpt-oss-120b.yaml
