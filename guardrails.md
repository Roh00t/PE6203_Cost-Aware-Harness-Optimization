# Guardrails

**PE6203 CA2 · Group Project 5** · Safety and execution boundaries for the cost-aware harness.
Status: frozen with `harness-v1` (`6c87103`, 2026-10-21) after the dev false-positive review (§7). §8 maps the controls to the course frameworks.

This document defines what the harness blocks, limits and logs, and the exact text the model sees when that happens. Architecture context: [`system_architecture.md`](system_architecture.md). Config IDs (B0, E, H0, Ck, V) are defined in [§2 of that document](system_architecture.md#2-configurations).

> **Scope.** Rules in this document are enforced by our host-side harness (H0, H0+Ck, V). The stock baselines B0 and E run Harbor's unmodified `mini-swe-agent` and get **none** of them: that is what "default harness" means. Their residual risks are covered in §5.

---

## 1. Threat Model

| Asset | Threat | Source | Primary control |
|---|---|---|---|
| OpenRouter credit ($8 shared) | Runaway loops, oversized prompts, re-runs after a crash | Model behaviour, harness bugs, `restart:` policies | Step, cost and job caps; key credit limit; no auto-restart (§4) |
| API key | Exfiltration by a command the model runs | Model output, **prompt injection** from live websites or task files | Key never enters the task container (§2) |
| Host machine | Destructive commands, resource exhaustion | Model output | Commands only ever run in the task container; Docker CPU/memory limits; 1 MB output cap |
| Benchmark integrity | Reading verifiers or solutions, tampering with tasks, task-specific hard-coding | Model (reward hacking), developers | Harbor isolates tests; checkout check; leak scan (§6) |
| Experimental validity | Guardrails silently changing what is measured | Over-broad rules | Every trigger logged; false-positive review on dev; rules frozen before eval (§7) |

**Untrusted inputs:** everything the model emits, and everything it reads, including:
- command output;
- task files;
- live web pages: the 22 Web tasks browse real sites through Chrome's debugging port, and System tasks change browser and app settings.

**Trusted:** this repository, the pinned TUA-Bench checkout, and Harbor 0.6.3.

---

## 2. Trust Boundaries

```mermaid
flowchart LR
  subgraph T1["Trusted: host"]
    H["Harness + Harbor<br/>holds OPENROUTER_API_KEY"]
  end
  subgraph T2["Untrusted execution: task container"]
    C["bash as 'agent'<br/>runs model-written commands"]
  end
  subgraph T3["Untrusted content"]
    W["Live websites, task files,<br/>command output"]
  end
  H -- "commands only; env allow-list, no secrets" --> C
  C -- "stdout/stderr (data, never instructions)" --> H
  C <--> W
  H -- "HTTPS + key" --> OR["OpenRouter"]
```

1. **Secrets stay on the host.** The harness calls `environment.exec()` with an explicit allow-list of variables ([system_architecture.md §3.1](system_architecture.md#31-hostcontainer-adapter-harnessenvironmentpy)). A unit test asserts no variable whose name contains `KEY`, `TOKEN` or `SECRET` is ever passed.
2. **Model output is only ever executed inside the task container.** The harness never `eval`s, `subprocess`es or templates model text on the host.
3. **Observations are data.** The prompt tells the model that instructions found in output, files or web pages are to be ignored ([`agent_instructions.md`](agent_instructions.md)). No guardrail depends on the model obeying this: every rule below is enforced by code.
4. **The container keeps internet access**, because tasks require it (`allow_internet = true`). Egress is therefore not a control we can use. The controls are "nothing worth stealing inside" (1) and "spending is capped" (§4).

---

## 3. Command Rules

The harness checks each proposed command *before* execution. **Always-on** rules (`G-*`) apply to every host configuration, H0 included: they almost never trigger in normal work, so they don't distort the H0 ≈ B0 parity check. **C2** rules (`U-*`) are part of the tool-interface component and are on only when C2 is.

**Matching.**
- `G-*` rules match the full command text, heredoc bodies included (safety first; false positives are logged).
- `U-*` rules match the command with heredoc bodies removed. A Python file that merely *contains* the word `vim` is not an editor launch.
- First match wins, `G-*` before `U-*`.
- Patterns are Python `re` with `re.MULTILINE`. The tables are abridged; the authoritative patterns and their unit tests live in `harness/guardrails.py` (planned). "Segment start" below means `(^|[;&|]\s*|\$\(\s*)`.

**Actions.**
- **block:** not executed; the message below is returned as the observation; counts as a step.
- **log:** executed normally; an event is recorded.

> These regexes stop *accidents and obvious misuse*. They are a seatbelt, not a sandbox: a determined model can obfuscate around them (variables, base64). The real boundary is the container, the absence of secrets, and the spend caps.

### 3.1 Always-on safety and integrity rules

| ID | Catches | Pattern (abridged) | Action |
|---|---|---|---|
| G-DST-01 | Recursive delete of `/`, `~`, `$HOME` or `/app` (the task's input root) | `\brm\s+(-\w*[rR]\w*\s+)+(--no-preserve-root\s+)?(/\*?\|~/?\|\$HOME/?\|/app/?\*?)(?=\s\|;\|&\|\\|\|$)` | block |
| G-DST-02 | Filesystem or device destruction | `\bmkfs(\.\w+)?\b`, `\bdd\b[^;&\|]*\bof=/dev/`, `\bwipefs\b`, `>\s*/dev/[sh]d[a-z]` | block |
| G-DST-03 | Fork bombs and process-wide kills | `:\(\)\s*\{\s*:\s*\\|\s*:\s*&\s*\}`, `\bkill\s+-9\s+-1\b`, `\bpkill\s+-9\s+-u\b` | block |
| G-DST-04 | Power or init state | `\b(shutdown\|reboot\|halt\|poweroff)\b`, `\bsystemctl\s+(poweroff\|reboot\|halt)\b`, `\binit\s+[06]\b` | block |
| G-DST-05 | Permission or ownership sweeps at `/` | `\bch(mod\|own)\s+-R\s+\S+\s+/(?=\s\|$)` | block |
| G-INT-01 | Grader paths (reward hacking) | `(?<![\w.])/(tests\|solution\|oracle)(?=/\|\s\|$\|['"])`, `/logs/verifier\b`, `\btest_outputs\.py\b`, `\bsolve\.sh\b` | block |
| G-SEC-01 | Secret probing, often the visible half of a prompt injection | segment start + `(printenv\|env)\s*($\|[;&\|])`, `/proc/\d+/environ`, `\$\{?\w*(API_KEY\|TOKEN\|SECRET)` | log |

### 3.2 C2 usability rules

| ID | Catches | Pattern (abridged) | Action |
|---|---|---|---|
| U-INT-01 | Full-screen editors, pagers, monitors | segment start + `(sudo\s+)?(vi\|vim\|nvim\|nano\|emacs\|pico\|less\|more\|top\|htop\|man\|watch)\b` | block |
| U-INT-02 | Follow mode, which never exits | `\btail\s+(-\w*f\w*\|--follow)\b`, `\bjournalctl\b[^;&\|]*\s-f\b` | block |
| U-INT-03 | Bare REPLs waiting on stdin | segment start + `(python3?\|ipython\|node\|irb\|sqlite3\|psql\|mysql)\s*(?=$\|[;&\|])` | block |
| U-INT-04 | Password prompts that hang | `\b(ssh\|scp)\b(?![^;&\|]*BatchMode=yes)` | block |
| U-INT-05 | `sudo` without `-n` (narrowed from U-INT-04 after the dev review, 2026-10-21: task containers grant passwordless sudo, so blocking it rejected a correct `sudo useradd …`) | `\bsudo\b(?!\s+-n\b)`, checked after every other rule | log |
| U-FMT-01 | Empty command | `^\s*$` | block |
| U-FMT-02 | Over-long command | length > 8,000 characters | block |
| U-FMT-03 | Unterminated heredoc | `<<-?\s*['"]?(\w+)['"]?` with no later line equal to the delimiter | block |
| U-FMT-04 | Submit combined with other work | contains `COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT` but is not exactly `echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT` | block |
| U-FMT-05 | More than one tool call in a response | count > 1 | run first, note the rest |

### 3.3 Exact messages returned to the model

Messages are short on purpose (they are billed tokens) and always say what to do instead. `{…}` are filled in by the harness.

| Rule | Message |
|---|---|
| G-DST-01…05 | `BLOCKED [{rule_id}]: this command could destroy the environment and was not run. Delete or modify only the specific files the task requires.` |
| G-INT-01 | `BLOCKED [G-INT-01]: paths reserved for the benchmark's grader are not part of the task. Work only from the task's inputs.` |
| U-INT-01 | `BLOCKED [U-INT-01]: '{program}' is interactive and would hang. Read with cat/head/sed -n, edit with sed, python, or cat <<'EOF' > file.` |
| U-INT-02 | `BLOCKED [U-INT-02]: follow mode never exits. Use 'tail -n 50 FILE' and run it again to poll.` |
| U-INT-03 | `BLOCKED [U-INT-03]: a bare '{program}' waits for input. Use '{program} -c "..."', '{program} script', or pipe input in.` |
| U-INT-04 | `BLOCKED [U-INT-04]: this would wait for a password. Use '-o BatchMode=yes' so it fails fast instead.` |
| U-INT-05 | None: logged only (`guardrail_log` event), the command runs |
| U-FMT-01 | `REJECTED [U-FMT-01]: empty command. Send one bash command.` |
| U-FMT-02 | `REJECTED [U-FMT-02]: command is {n} characters (limit 8000). Write long content to a file with a heredoc across several steps.` |
| U-FMT-03 | `REJECTED [U-FMT-03]: heredoc '{delim}' is never closed. End it with a line containing only {delim}.` |
| U-FMT-04 | `REJECTED [U-FMT-04]: submit on its own: echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT` |
| U-FMT-05 | Appended to the observation: `NOTE: {k} extra tool call(s) were ignored; send one command per response.` |
| Format error (C2) | `REJECTED: no valid bash tool call found ({reason}). Reply with brief reasoning and exactly one bash tool call.` |
| Format error (H0, stock) | mini-swe-agent v2.4.6 `format_error_template`, unchanged |

---

## 4. Limits and Kill Switches

| Limit | H0 (stock behaviour) | With component | When hit |
|---|---|---|---|
| Consecutive format errors | 3 | 5 (C2) | Trial ends, `exit_status = RepeatedFormatError` |
| Guardrail blocks per trial | 10 | 10 | Trial ends, `exit_status = GuardrailLimit` |
| Repeat-failure intercepts | n/a | Unlimited, each logged (C4) | The command is not executed (see C4) |
| Model calls per trial | None (stock default) | 50 (C3) | `exit_status = LimitsExceeded` |
| Agent wall-clock | 2,400 s (task default) | same | Harbor stops the trial; logs already flushed |
| Per-command timeout | 30 s | 180 s (C3) | Command killed; message with background-job recipe (C4) |
| Output read per command | 1 MB | 1 MB | Rest dropped, `[output truncated at 1 MB]` |
| Per-task spend | None (stock default); key credit limit, plus a pilot-based safety ceiling if needed ([architecture §6](system_architecture.md#6-budgets-and-limits)) | B_task (C3) | `exit_status = CostCapExceeded` |
| Per-job spend | Job budget + 20% | same | Gateway refuses further calls; remaining trials marked `budget_abort` (rerun later, never scored as failures) |
| API errors (429, 5xx, timeout) | 3 retries, backoff 2/4/8 s | same | Then infra error → trial rerun policy |
| OpenRouter key | Credit limit set in the dashboard | n/a | Provider-side hard stop: the last line of defence |
| Process supervision | No `restart:` policy anywhere | n/a | A crashed run stays crashed (`docker-compose.yml`) |

**Human-in-the-loop** (enforced by `scripts/harbor_run.sh`):
- Any agent other than `oracle` or `nop` requires `CONFIRM_PAID=1`.
- `SPLIT=eval` with a model agent additionally requires `CONFIRM_EVAL=1`.
- Coding assistants working on this repo must ask a human before setting either ([`CLAUDE.md`](CLAUDE.md)).

---

## 5. Secrets and Residual Risks

- **Storage.**
  - `.env` is git-ignored and listed in `.dockerignore`.
  - The runner image copies no source. A search of the built image for `.env` returned nothing (verified 2026-10-09).
  - `.env.example` documents the variables.
- **One key per teammate**, created for this project with a hard credit limit, and rotated after the final run. Keys are never pasted into chat, issues, commits or logs. `calls.jsonl` stores no request headers.
- **B0 and E (accepted residual risk).** Harbor's stock `mini-swe-agent` passes the API key *into* the task container, where model-written commands and live web content coexist. We cannot change this without changing the default harness. Mitigations:
  - the credit-capped key bounds the loss;
  - post-experiment rotation;
  - G-SEC-01-style log review of B0/E trajectories (an offline grep, since no live rules apply to B0/E).
- **Docker socket.** The optional compose runner mounts `/var/run/docker.sock`, which is root-equivalent on the Docker VM. Only Harbor uses it. Model commands never run in that container.
- **Supply chain.** Harbor, mini-swe-agent (2.4.6), uv and base images are pinned. B0 still runs Harbor's installer, which `curl | sh`-installs uv 0.7.13 into the task container: part of the stock harness, noted rather than changed.

---

## 6. Benchmark Integrity

| Rule | Enforcement |
|---|---|
| Tasks and verifiers unmodified | `harbor_run.sh` refuses to start unless the TUA-Bench checkout is at the subset's commit with no tracked changes under `tasks/` or in `dataset.toml` |
| The agent never sees grader material | Harbor uploads `tests/` only after the agent has finished. `solution/` is used only by the oracle agent. G-INT-01 blocks and logs any attempt anyway. |
| No task-specific hard-coding | `scripts/check_no_task_leak.py` (planned, runs in `harbor_run.sh`) fails if `harness/`, `configs/harness/` or `agent_instructions.md` contains any task ID, or any file name that appears in a task instruction |
| No tuning on the evaluation set | Development and pilots on the dev split (`--split dev`) only. `CONFIRM_EVAL=1` gate (§4). |
| Subset fixed | `configs/task_subset.json` changes only through the oracle gate, before the first model run ([architecture §10.1](system_architecture.md#101-before-any-model-run)) |
| Budgets stated and versioned | Baselines keep stock defaults. Variant budgets (S, B_task, timeouts) live in versioned config files, not `.env`. The report lists every limit per configuration. |

---

## 7. Measuring the Guardrails

Guardrails can lower success as well as protect it, so they are measured like any other component:

- Every trigger is an `events.jsonl` record with `rule_id`, the command (truncated to 500 characters) and the action taken.
- **Dev review before freeze.** All `block` events from dev runs are reviewed by hand. A rule with any false positive on a legitimate command is narrowed. The rule table is then frozen together with the harness version used for eval.
- **Report.** Trigger counts per rule per configuration. Blocks that preceded a failed trial are checked during failure classification ([architecture §10.4](system_architecture.md#104-analysis)), so a guardrail-caused failure is labelled as a harness-level failure, not hidden.

### 7.1 Dev review result (2026-10-21)

Reviewed: every `guardrail_block` event in the dev logs, i.e. Abin's C1/C3 runs (`results/dev/c1-c3-dev`, 19 trials, G-rules only) and Rohit's live smoke runs of C2, C4, C5, V and V-E on dev tasks 020 and 106 (11 trials).

| Rule | Blocks | Legitimate? | Outcome |
|---|---|---|---|
| U-INT-04 (`sudo` part) | 3: H0+C2, V and V-E on task 106, each on `sudo useradd -m -d /home/test1 … && … \| sudo chpasswd` | **Yes: false positive.** Task containers grant the agent passwordless sudo, so the command could never wait for a password. After the block, H0+C2 and V scored 0 on a task that H0+C4 and H0+C5 (no U-rules) solved; V-E recovered and solved it | **Narrowed.** `sudo` without `-n` moved to the log-only rule U-INT-05 (checked last, so it never hides a block). U-INT-04 keeps blocking `ssh`/`scp` without `BatchMode`. Code, §3.2–3.3 and unit tests changed together (104 tests pass) |
| All other rules | 0 | n/a | Unchanged |

The rule table above is frozen with `harness-v1`. **Eval-phase review:** after the eval runs, count `guardrail_block` and `guardrail_log` events per rule per configuration (`grep -h '"guardrail_' jobs/<run>/*/*/*/agent/events.jsonl`), and check every block in a failed trial during failure classification. Report "0 blocks" explicitly where none occur. Because U-INT-05 now lets `sudo` through, a trial that hangs on a sudo password would surface as a `command_timeout` event (30 s, or 180 s with C3), not a hang.

---

## 8. Mapping to Course Frameworks

Sources: the Agentic AI lectures in `docs/` (Week 8 Tools, Week 10 Harness, Week 12 Industry Applications), which cite the OWASP Top 10 for LLM Applications (2025), Simon Willison's lethal trifecta (2025), Meta's Agents Rule of Two (2025) and the NIST AI RMF. The separate AI Cybersecurity slides are not in the repository; add any framework they introduce to the tables below.

### 8.1 Lethal trifecta and the Rule of Two (Week 12)

The lethal trifecta is **untrusted content + private data + a way to send data out**; together they make a data-theft path. The Rule of Two says an agent should not autonomously hold all three in one session.

| Leg | Our harness (H0 … V, V-E) | Stock baselines (B0, E) |
|---|---|---|
| Untrusted content | **Present:** live websites, task files, command output (§1) | Present |
| Private data | **Removed from the execution context:** the API key stays on the host; the container gets an env allow-list with no secrets (§2.1), checked by a unit test | **Present:** stock mini-swe-agent passes the key into the container |
| External communication | **Present:** tasks need internet (`allow_internet = true`), so egress can't be closed (§2.4) | Present |

So our harness satisfies the Rule of Two by removing the private-data leg, the leg it controls. B0/E hold all three; as the brief requires an unmodified default harness, this is an accepted residual risk bounded by credit-capped keys and rotation (§5). As the lecture stresses, prompt instructions alone are insufficient: our "observations are data" prompt line (§2.3) is a backstop, and every control here is enforced in code.

### 8.2 Tool safety: blast radius, permissions, sandboxing (Week 8)

| Lecture principle | How the harness applies it |
|---|---|
| Tier actions by blast radius: auto-allow reads, confirm writes, block the truly dangerous | Ordinary commands run; environment-destroying commands are blocked (G-DST-01…05); grader access is blocked (G-INT-01); risky-but-legitimate patterns are logged, not blocked (G-SEC-01, U-INT-05) |
| Human-in-the-loop before irreversible actions; "the runtime asks permission, the model never skips the gate" | The irreversible actions in this project are spending money and producing recorded results, so the gates sit there: `CONFIRM_PAID=1` for any paid run and `CONFIRM_EVAL=1` for the eval split, enforced by `harbor_run.sh`, not by the model (§4). Inside a trial, everything is undone by deleting the container |
| Sandbox code execution with CPU, memory, network, filesystem limits | Every trial runs in its own Docker container, built from the task image and deleted afterwards (`--delete`); task-defined CPU/memory limits; per-command timeouts (30 s, 180 s with C3); 1 MB output cap (§4) |
| Least privilege, no standing admin rights | Applied at the container boundary: no secrets, no host access, no Docker socket for model commands (§5). Inside the container the agent has passwordless sudo because many tasks need it; that is why `sudo` is logged (U-INT-05) rather than blocked, and why the boundary, not in-container permissions, is the control |
| Assume calls may be wrong or adversarial; design for failure | §3 rules check every command before it runs; C2 validates tool arguments against schemas; C4 stops identical failing commands from repeating |

### 8.3 Harness duties (Week 10)

| Lecture principle | How the harness applies it |
|---|---|
| "Model output is untrusted input. Validate it before you execute it." | The guardrail check runs before every execution (§3); C2 validates tool calls and returns a precise error with a valid example |
| Budgets and stopping: when a budget runs out, return a reason, never report success | C3's step and dollar caps end the trial with `LimitsExceeded` / `CostCapExceeded`, never `Submitted`; per-job ledger cap; wall-clock limit (§4) |
| Classify errors before retrying: transient → bounded retry with backoff; malformed → repair, then retry; permanent/fatal → stop and report | API 429/5xx/timeout: 3 retries with 2/4/8 s backoff, then an infrastructure error that is rerun, never scored (§4). Malformed responses: format-error feedback (C2 wording), at most 3 (5 with C2) in a row. Repeated identical failures: C4 refuses the third identical failing command and asks for a different approach |
| Observability: every step logged and traceable | `calls.jsonl` (every HTTP attempt, tokens, cost, provider, purpose), `events.jsonl` (every guardrail, budget and recovery event), and the full trajectory; append-only and flushed per event so killed trials keep their data |

### 8.4 OWASP Top 10 for LLM Applications (2025)

| OWASP 2025 | Relevance here | Controls in this document |
|---|---|---|
| LLM01 Prompt Injection | Live websites and task files flow into the model's context | No secrets in the container (§2.1, §8.1), container-only execution (§2.2), data framing (§2.3), G-SEC-01 logs secret probing |
| LLM02 Sensitive Information Disclosure | API key exposure | §2.1, §5 |
| LLM03 Supply Chain | Pinned Harbor, mini-swe-agent and images; B0's `curl \| sh` installer | §5 |
| LLM05 Improper Output Handling | Model output executed as shell | §2.2, §3 rules, C2 argument validation |
| LLM06 Excessive Agency | Root-level destructive commands, grader access, too much autonomy | G-DST-*, G-INT-01, container boundary (§8.2), paid/eval gates |
| LLM10 Unbounded Consumption | Loops, context growth, crash-restart spending | §4 caps, C1 context limits, C3 budget, C4 repeat intercept, no `restart:` policy |

### 8.5 Governance (Week 12, NIST AI RMF)

"Guardrails stop a bad action in the moment; governance keeps the deployment accountable." Our governance controls: a named owner for freezes and paid runs (Rohit, `CLAUDE.md`); rules, configs and models frozen and versioned with the `harness-v1` tag; a recorded review that narrowed one rule on evidence (§7.1); append-only logs committed under `results/` behind every reported number; per-person keys with credit limits, rotated after the final run; and a kill switch at three levels (job ledger, key credit limit, no auto-restart).
