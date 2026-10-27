# Framework mapping: additions to `guardrails.md` §8

Asmitha, 2026-10-27. Rohit's `guardrails.md` §8 already maps the harness to:
- the lethal trifecta and the Rule of Two;
- Week 8 tool safety;
- Week 10 harness duties;
- the OWASP Top 10 for LLM Applications (2025);
- the NIST AI RMF.

This file does not repeat any of that. It lists what the lecture notes `docs/Week07_Introduction.md` … `docs/Week12_Industry_Applications.md` cover that §8 misses, as rows and paragraphs ready to paste into §8. `guardrails.md` is frozen with `harness-v1`, so nothing here has been applied; Isha or Rohit decide.

**Method.**
- I read §8 against all six lecture files.
- Every quote below is copied verbatim and cited as `file:line`. Several lecture lines are long PDF extractions; the quote is a substring of that line.
- Control IDs refer to `guardrails.md` §3–§6 and to `system_architecture.md` §5.

## Summary of gaps

| # | Gap | Kind | Where it goes |
|---|---|---|---|
| 1 | Week 7's three permission levels and their four criteria | Framework not cited | §8.2, new first row |
| 2 | Week 12's Autonomy Ladder: where our agent sits and where oversight is | Framework not cited | §8.2, new row |
| 3 | Compaction can drop instructions (Week 9, Week 12 incident) | Principle, maps to C1 | New §8.6 |
| 4 | Memory poisoning and offloaded files (Week 9) | Principle, maps to C1 | New §8.6 |
| 5 | Success checked in code, not claimed by the model (Weeks 7, 10, 12) | Principle, maps to C5 and the verifier | §8.3, new row |
| 6 | Timeouts are unknowns; replay can repeat side effects (Week 10) | Principle, maps to the gateway and rerun policy | §8.3, new row |
| 7 | Explicit terminal states (Week 10) | Principle, maps to exit statuses | §8.3, new row |
| 8 | Harness vs runtime separation (Week 10) | Principle, maps to the container adapter | §8.3, new row |
| 9 | Poka-yoke and high-signal tool returns (Week 8) | Principle, maps to C2 and C1 | §8.2, new row |
| 10 | Budget alerts (Week 12) | Principle, maps to C3's status line and nudges | §8.3, extend the budgets row |
| 11 | Evaluation integrity: headline metric vs safety columns, same task set (Weeks 10–11) | Principle, maps to §6 and §7 | New §8.7 |
| 12 | Industry-grade checklist; log retention, vendor and access review (Week 12) | Governance | §8.5, extend |
| 13 | OWASP LLM04, LLM07, LLM08, LLM09 missing from §8.4 | Framework rows | §8.4, 4 new rows |
| 14 | Controls with no §8 row: C0, C5, C4 stall detection, U-INT-01…04, U-FMT-01…05, GuardrailLimit, §6 integrity checks | Unmapped controls | Spread over the rows above |
| 15 | Controls that exist in code but not in `guardrails.md`, so §8 cannot map them | Documentation gap | `guardrails.md` §4–§5 first, then §8 |
| 16 | A §8.2 statement contradicted by the eval logs ("passwordless sudo") | Correction | §8.2, edit one row |

The lectures do not name MITRE ATLAS, the EU AI Act, ISO 42001, the dual-LLM pattern, CaMeL or an OWASP agentic list. I searched for each and found none, so none is proposed. The only MCP line is "MCP servers still need access control and input validation" (`docs/Week08_Tools.md:542`); it doesn't apply, because the harness uses no MCP.

---

## Proposed rows for existing §8 tables

### §8.2 Tool safety: three new rows and one correction

| Lecture principle | How the harness applies it |
|---|---|
| Week 7's three permission levels: "**EXECUTE AUTOMATICALLY**", "REQUIRE CONFIRMATION" and "**DO NOT ALLOW EXECUTION** The action is outside the agent's authority in this system." The level "depends on impact, reversibility, authorization, and recovery cost." (`docs/Week07_Introduction.md:382–390`) | *Execute automatically*: ordinary commands, plus the log-only rules G-SEC-01 and U-INT-05. *Do not allow*: G-DST-01…05 (irreversible, unrecoverable) and G-INT-01 (outside the agent's authority: grader material). Direct testing found gaps: G-DST-01 allows `rm -rf /app`, and a log-only G-SEC-01 match hides later blocks (`docs/guardrail_eval_review.md` §6). *Require confirmation*: no in-trial action needs it, because the container is disposable. The confirmation gates sit on the irreversible project actions instead: `CONFIRM_PAID=1` and `CONFIRM_EVAL=1` (§4) |
| Week 12's Autonomy Ladder: a "Goal-directed agent" is "given an objective, plans and executes multiple steps" and "continues with limited supervision" (`docs/Week12_Industry_Applications.md:86–88`) | Inside a trial our agent is a goal-directed agent with no human in the loop, because the benchmark requires it. Oversight therefore sits at the run level (paid and eval gates, a named owner for freezes, per-run spend caps) and in code-enforced limits (§3, §4), not in per-step approval |
| Week 8: "**Poka-yoke:** constrain arguments so mistakes are impossible (e.g. require absolute paths)", "**Actionable errors:** guide self-correction" and "paginate and truncate" (`docs/Week08_Tools.md:730–734`) | C2's tools take typed, base64-encoded arguments, so shell quoting cannot break them. `edit_file` fails unless its snippet matches exactly once. `read_file` returns at most 200 lines and `search` at most 100 hits. C1 offloads long outputs to a file and shows head and tail. Every §3.3 message says what to do instead. *Eval evidence:* an actionable error is only as good as the check behind it. U-FMT-03 returned an actionable but false message 13 times (`docs/guardrail_eval_review.md`) |

**Correction to the existing "Least privilege" row.** It says: "Inside the container the agent has passwordless sudo because many tasks need it". That holds for dev task 106, but the eval logs show images without `sudo`: all 3 U-INT-05 events returned `bash: line 1: sudo: command not found` (`docs/guardrail_eval_review.md` §3). Suggested wording: "Some task images grant passwordless sudo and others don't install it; either way `sudo` is logged (U-INT-05) rather than blocked, and the container boundary, not in-container permissions, is the control."

Optionally, add one sentence to the "Sandbox code execution" row. The lecture lists "Tools: Docker, gVisor, Firecracker, E2B." (`docs/Week08_Tools.md:828`). We use Docker, a shared-kernel container, not a VM-isolated sandbox. That is acceptable because nothing secret is inside it (§2.1), but it is the weakest of the four.

### §8.3 Harness duties: four new rows and one extension

| Lecture principle | How the harness applies it |
|---|---|
| "The goal test passes — checked in code, not claimed by the model" (`docs/Week10_Harness.md:213`). "A model's claim of completion is not a completion check" (`docs/Week10_Harness.md:698`). "Are outputs verified? … Is the status report honest?" (`docs/Week07_Introduction.md:1126`) | The reward comes only from Harbor's verifier, which runs after the agent finishes (§6). C5 checks, in code, that every output path in the instruction exists, is non-empty and was written during the trial (`test -s` plus a modification-time check) before releasing the first submission. Cap exits never report `Submitted`. *Eval evidence:* the check matters. V-E/015 submitted with "We have generated the reduced OSM, translated it to IDF, and created the EnergyPlus run directory" while the required `eplusout.sql` was an empty file it had created with `touch` (`docs/failure_catalog.md`, Case 5) |
| "The hard question is not saving state; it is whether replay repeats a side effect." (`docs/Week10_Harness.md:406`). "A timeout on a write is not a failure — it is an unknown." (`docs/Week10_Harness.md:519`) | No checkpoint replay: an infrastructure-error trial is rerun from a fresh container, and the failed attempt is archived, never scored. The gateway writes one `calls.jsonl` row per HTTP attempt and records unknown usage as `null`, never 0, so a rejected or timed-out call stays an unknown in the cost report (reported as a lower bound). Each request has a 600 s timeout. *Gap:* the same lecture line sets the 429 policy as "Bounded retry, exponential backoff with jitter". The gateway retries a rate-limited call only 3 times, waiting 2, 4 and 8 s with no jitter (`harness/gateway.py:205-216`), and gives up after about 14 s. Stock mini-swe-agent retries up to 10 times with 4–60 s waits. Two V-E trials crashed this way (tasks 011 and 077); both were archived as infrastructure errors and rerun |
| "Every terminal state is explicit, so the process cannot end by accident." (`docs/Week10_Harness.md:604`) | Every trial ends with a named `exit_status`: `Submitted`, `RepeatedFormatError`, `GuardrailLimit`, `LimitsExceeded`, `CostCapExceeded` or `TimeExceeded` (`harness/loop.py`, `harness/components/budget.py`). A run aborted by the job ledger is marked `budget_abort` (§4) |
| "**Task logic in the harness; execution safety in the runtime.**" (`docs/Week10_Harness.md:342`), with "credentials injected at execution — never inside a prompt" (`docs/Week10_Harness.md:362`) | The loop, prompts and components C0–C5 are the harness. `harness/environment.py` is the runtime adapter: env allow-list with no secrets, 1 MiB output cap, per-command timeout. The API key is used by the host-side gateway and never enters a prompt or the container (§2.1) |

**Extension to the existing "Budgets and stopping" row.** Week 12 recommends "an alert at 80% of budget" (`docs/Week12_Industry_Applications.md:152`) because "Agents work in loops, so they can quietly run up big bills." (`docs/Week12_Industry_Applications.md:623`). Add: C3 shows the remaining budget on every observation (`[budget] step s/S · $spent/$B_task · …`) and sends two phase nudges, at 70% and 90% of steps (`system_architecture.md` §5, C3). The `stall_nudge` from C4 matches Week 10's stall signal, "The same action repeats, or state stops changing" (`docs/Week10_Harness.md:225`); §8 currently maps only C4's repeat intercept.

### §8.4 OWASP 2025: four new rows

Definitions as given in `docs/Week12_Industry_Applications.md:1114`.

| OWASP 2025 | Relevance here | Controls in this document |
|---|---|---|
| LLM04 Data & Model Poisoning ("corrupting training or knowledge-base data to bias / backdoor it") | Low. We do no training and keep no knowledge base; the model is a fixed third-party model. The nearest analogue is a poisoned notes or offload file inside one trial | Container deleted after every trial (`--delete`), so nothing persists across trials (§8.6) |
| LLM07 System Prompt Leakage ("the hidden system prompt (and secrets in it) is exposed") | Low: nothing secret to leak. `agent_instructions.md` is public in this repository and holds no secrets. The lecture's own example is a system prompt "which holds an API key" (`docs/Week12_Industry_Applications.md:1126`) | Key never in a prompt or the container (§2.1) |
| LLM08 Vector & Embedding Weaknesses ("RAG / embedding attacks, e.g. cross-tenant data leaks") | Not applicable: no vector store or embeddings | n/a |
| LLM09 Misinformation ("false or fabricated output that users rely on") | **Relevant.** The agent can claim success it did not achieve. Week 12 warns "agents can confidently lie about what they did" (`docs/Week12_Industry_Applications.md:875`). The eval logs contain fabricated stand-ins: V-E/015's `touch`ed `eplusout.sql`, V-E/089's placeholder `installed_extensions.txt` (`results/analysis/eval/rohit-eval-pass1/failures/manual_review.md`) | The reward comes only from the independent verifier (§6). C5 checks outputs in code before release. Cap exits never report `Submitted`. Costs come from the price table, never from the model or the agent's own cost field |

### §8.5 Governance: extend the paragraph

Add after the existing list:

> Week 12's checklist "What "Industry-Grade" Adds" (`docs/Week12_Industry_Applications.md:106–122`) maps one-to-one:
> - "every step logged, traceable and testable": `calls.jsonl`, `events.jsonl`, trajectories;
> - "predictable budget per task, at volume": C3's B_task and the job ledger;
> - "measured success rate, re-tested on every change": the frozen eval subset and one run per configuration, with every change ablated.
>
> Two of its accountability questions are only partly answered. "decide up front how long its logs and outputs are kept" (`docs/Week12_Industry_Applications.md:667`): `results/` is kept in git, `jobs/` is git-ignored and pruned by hand, and no retention period is set. "audit outside AI vendors like any other supplier" (`docs/Week12_Industry_Applications.md:669`): the only outside AI vendor path is OpenRouter with one pinned provider per model (`configs/models/`), and keys are rotated after the final run (§5).

---

## Proposed new subsections

### §8.6 Context and memory (Week 9)

> The Week 9 lecture uses the CoALA memory framework ("Teaching analogy informed by CoALA’s memory framework (Sumers et al., 2023).", `docs/Week09_Memory.md:131`): working, episodic, semantic and procedural memory. Our harness keeps **working memory only**:
> - the trajectory;
> - C1's offloaded outputs in `/tmp/harness/obs/`;
> - C1's notes file `/tmp/harness/notes.md`.
>
> All three live in the task container, which is deleted after every trial. Nothing is carried across trials or tasks, so there is no long-term memory to poison or leak.
>
> | Lecture principle | How the harness applies it |
> |---|---|
> | Compaction is lossy: "removing older turns can also remove task instructions" (`docs/Week09_Memory.md:645`). Week 12's incident: "during context "compaction" (condensing memory to save tokens), the agent DROPPED the safety instruction "ask before deleting."" (`docs/Week12_Industry_Applications.md:897`) | C1's compaction always keeps the system message, the task and the first exchange verbatim, and condenses only the middle. More importantly, no safety rule lives in the prompt: every §3 rule and §4 limit is enforced in code (§2.3), so compaction cannot remove one |
> | "Malicious text may influence later decisions when a saved record is retrieved." "Keep source labels and do not follow external instructions merely because they were stored." (`docs/Week09_Memory.md:779–783`) | Offloaded outputs and the notes file are written from untrusted command output. The prompt frames all observations as data (§2.3), and C1's digest keeps the step number and command beside each quoted output line (its source label). *Residual:* no rule protects `/tmp/harness/`, so the agent can overwrite its own notes. That matters only within one trial |
> | Offloading: "The full output remains recoverable only while the file is intact and accessible" (`docs/Week09_Memory.md:686`) | C1 tells the model the file path and line count, and the files live until the trial ends. Containers are not reused, so an offload never outlives its trial |
> | "Do not store credentials." "Use the same checks before writing and in final scans of all retained records" (`docs/Week09_Memory.md:771–775`) | No credential enters the container or `calls.jsonl` (§2.1, §5). The final scan of retained records exists: `scripts/export_run.py` refuses to copy a run into `results/` if any file matches an API-key pattern (`SECRET_RE`, lines 20 and 49–51). This control should also be listed in §5 |

### §8.7 Evaluation integrity (Weeks 10–11)

> Week 11 is about training, but its evaluation rules apply to harness experiments too: "Good evaluation is required before and after — without it you cannot tell an improvement from a lucky run." (`docs/Week11_Training.md:244`). "A win on the headline metric is not a win: always diff the safety and efficiency columns too." (`docs/Week11_Training.md:1163`). An unsafe action calls for a "Hard gate plus an eval case — never a reward tweak." (`docs/Week11_Training.md:1176`). Week 10's ablation design uses the "same task set under each" condition (`docs/Week10_Harness.md:1046`).
>
> | Lecture principle | How the harness applies it |
> |---|---|
> | Same task set under each condition | Frozen 40-task subset, checked by fingerprint (`973635ea…`) in every run; every configuration runs every task (§6) |
> | Tell an improvement from a lucky run | Paired bootstrap over tasks with 95 % intervals and win/tie/loss counts; differences under about 10 points are reported as inconclusive (`system_architecture.md` §10.4) |
> | Diff the safety and efficiency columns | Cost per run is reported beside reward for every configuration. Guardrail trigger counts and false positives are reported per rule per configuration (`docs/guardrail_eval_review.md`) |
> | Hard gate plus an eval case, never a reward tweak | Every guardrail is a code gate with a unit test giving one positive and one negative example (`CLAUDE.md` conventions). The verifiers are never modified (`harbor_run.sh` refuses a modified checkout). Gaming the grader is blocked by G-INT-01 and by the leak scan `scripts/check_no_task_leak.py` (§6) |

---

## Controls that `guardrails.md` does not document (so §8 cannot map them)

All four are in the code and were added under freeze exceptions recorded in `CLAUDE.md`. They belong in `guardrails.md` §4 or §5 first.

| Control | Where | Framework it would map to |
|---|---|---|
| 600 s per-request timeout on model calls | `harness/gateway.py:17–20, 92` (`REQUEST_TIMEOUT_S = 600`) | Week 10 failure policy (row above); LLM10 |
| Secret scan before exporting logs to `results/` | `scripts/export_run.py:20, 49–51` | LLM02; Week 9 "final scans of all retained records" |
| Dependency snapshot pin for B0/E (`UV_EXCLUDE_NEWER=2026-10-13`) | `scripts/run_all_configs.py:41, 155` (`STOCK_EXCLUDE_NEWER`); `CLAUDE.md`, third freeze exception | LLM03 Supply Chain |
| Waiting on Harbor's event-loop thread raises instead of deadlocking | `harness/environment.py`; `CLAUDE.md`, first freeze exception | Week 10 "Every terminal state is explicit": a hang is the one terminal state with no name |

## AI Cybersecurity slides

§8 notes that the separate AI Cybersecurity slides are not in the repository. That is still true. None of the six lecture files mentions them. Week 12 treats cybersecurity only as an application area and in case studies; for example, "Cybersecurity is now a headline application in BOTH directions - defense and offense." (`docs/Week12_Industry_Applications.md:423`). Its frameworks (OWASP 2025, NIST AI RMF, the lethal trifecta, the Rule of Two) are already in §8. **Pending:** if Asmitha supplies the slide file, any framework it introduces will be mapped here in the same table style. Without it, nothing can be added.
