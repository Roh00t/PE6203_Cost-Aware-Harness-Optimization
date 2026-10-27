# Draft: Report Appendix C, guardrail rules mapped to the course frameworks

Asmitha, 2026-10-27. This is the draft for the shared report.

**Sources.**
- Rule definitions: `guardrails.md` §3–§4.
- Framework mapping: `guardrails.md` §8, plus the proposed additions in `docs/framework_mapping_additions.md`.
- Eval-phase trigger counts: `docs/guardrail_eval_review.md` (all 11 configurations).
- Lecture references are to the course notes in `docs/Week07…Week12`.
- OWASP = OWASP Top 10 for LLM Applications (2025), as summarised in Week 12.

The separate AI Cybersecurity slides were not available to us, so no framework from them is mapped.

---

## Appendix C. Guardrail rules mapped to the course frameworks

The harness checks every proposed command before it runs.
- **Always-on rules** (G-*) apply to every harness configuration.
- **Usability rules** (U-*) belong to the tool-interface component C2.
- The stock baselines B0 and E run no rules, because the brief requires an unmodified default harness.

*Block* means not executed: the model receives a corrective message instead. *Log* means executed and recorded.

The permission tiers come from two lectures:
- **Week 7:** three levels, EXECUTE AUTOMATICALLY, REQUIRE CONFIRMATION and DO NOT ALLOW EXECUTION. The level "depends on impact, reversibility, authorization, and recovery cost" (`docs/Week07_Introduction.md:382–390`).
- **Week 8:** "auto-allow … require confirmation for writes; block the truly dangerous".

### C.1 Command rules

| Rule | Catches | Action | Permission tier (Weeks 7–8) | Harness duty (Week 10) | OWASP 2025 | Eval triggers (11 configs) |
|---|---|---|---|---|---|---|
| G-DST-01…05 | Recursive delete of `/`, `~` or `/app`; filesystem or device destruction; fork bombs and mass kills; shutdown or reboot; permission sweeps at `/` | Block | Do not allow: irreversible, high recovery cost | Validate model output before executing it | LLM05 Improper Output Handling; LLM06 Excessive Agency | 0 |
| G-INT-01 | Reading the grader's paths (`/tests`, `/solution`, verifier logs) | Block | Do not allow: outside the agent's authority | Success checked in code, not claimed; evaluation integrity (Week 11: "Hard gate plus an eval case — never a reward tweak") | LLM06 | 0 |
| G-SEC-01 | Secret probing (`env`, `printenv`, `/proc/*/environ`, `$…API_KEY`) | Log | Auto-allow and record | Observability: every step logged | LLM01 Prompt Injection (its visible half); LLM02 Sensitive Information Disclosure | 0 |
| U-INT-01 | Full-screen editors, pagers and monitors (`vim`, `less`, `top` …) | Block | — | Budgets and stopping: a hung command burns the time budget | LLM10 Unbounded Consumption | 0 |
| U-INT-02 | Follow mode (`tail -f`, `journalctl -f`) | Block | — | Budgets and stopping | LLM10 | 0 |
| U-INT-03 | A bare interpreter waiting on stdin (`python3`, `node` …) | Block | — | Budgets and stopping | LLM10 | 1 (false positive: piped input) |
| U-INT-04 | `ssh`/`scp` without `BatchMode` (password prompt) | Block | — | Budgets and stopping | LLM10 | 0 |
| U-INT-05 | `sudo` without `-n` | Log | Auto-allow and record; least privilege enforced at the container boundary | Observability | LLM06 | 3 logs (all harmless) |
| U-FMT-01 | Empty command | Block | — | Validate before executing; actionable errors | LLM05 | 0 |
| U-FMT-02 | Command over 8,000 characters | Block | — | Validate before executing | LLM05; LLM10 | 0 |
| U-FMT-03 | Unterminated heredoc | Block | — | Validate before executing | LLM05 | 13 (**all false positives**) |
| U-FMT-04 | Submit combined with other work | Block | — | Explicit terminal states; completion is a separate, checkable step | LLM05 | 2 (1 correct, 1 over-strict) |
| U-FMT-05 | More than one tool call per response | Run the first, note the rest | — | One action per turn, each validated | LLM06 | 0 |

The "Catches" column describes each rule's intent, as specified in `guardrails.md` §3. Testing the implementation directly found latent gaps that never fired in eval (`docs/guardrail_eval_review.md` §6):
- G-DST-01 allows `rm -rf /app`.
- G-DST-04 also blocks harmless code such as `logging.shutdown()`.
- A log-only G-SEC-01 match hides any later block.

### C.2 Other controls

| Control | Framework |
|---|---|
| API key never enters the task container; environment allow-list | Lethal trifecta / Rule of Two (Week 12): removes the *private data* leg. Untrusted content and internet access stay, because the tasks need them. OWASP LLM02 |
| Model commands run only inside a disposable Docker container, deleted after each trial | Week 8 sandboxing and least privilege; OWASP LLM05, LLM06 |
| Step cap (50), per-task dollar cap (B_task), per-run job ledger, wall-clock limit, 30 s / 180 s command timeout, 1 MB output cap | Week 10 budgets and stopping; Week 12 cost control; OWASP LLM10 |
| Gateway retries on HTTP 429 or 5xx errors: 3 retries at 2, 4 and 8 s | Week 10 failure policy ("Bounded retry, exponential backoff with jitter"). Bounded, but with no jitter and a short window: two V-E trials crashed on rate limits and were rerun |
| `CONFIRM_PAID=1` and `CONFIRM_EVAL=1` before paid or eval runs | Week 7 and Week 8 human-in-the-loop for irreversible actions (spending, recorded results) |
| C5 pre-submission gate; reward only from the independent verifier | Week 10 "checked in code, not claimed by the model"; OWASP LLM09 Misinformation (fabricated completion) |
| C4 repeat intercept and stall nudge | Week 10 stall detection and bounded retry |
| Pinned Harbor, mini-swe-agent and images; dependency snapshot pin for B0/E | OWASP LLM03 Supply Chain |
| Task-leak scan, unmodified-checkout check, frozen task subset | Weeks 10–11 evaluation integrity: same task set under each condition, no tuning on the evaluation set |
| `calls.jsonl`, `events.jsonl`, full trajectories, append-only and committed under `results/` | Week 12 observability; NIST AI RMF governance (accountability, traceability) |

**What the eval phase showed.**
- No always-on rule ever triggered, in 3,094 commands across all configurations, including an offline replay over B0 and E.
- The only blocks came from C2's format and usability rules.
- U-FMT-03 blocked 13 valid commands. Under the Week 8 principle of designing for failure, we report this as a harness-level failure in §9, not as a safety success.
