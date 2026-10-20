**Harness, Runtime, and Multi-Agent Systems** Week 10 · Agentic AI 

Prof Bo AN https://personal.ntu.edu.sg/boan/ _Email_ : boan@ntu.edu.sg _Office_ : S3-B2C-83 



#### **Roadmap** 

_Six weekly sessions across Weeks 7-12_ 

**Introduction to Agentic AI 1** 

Agents, autonomy, reasoning & planning  (Wk 7) 

- **Tools, Skills, and Action Interfaces** 

- **2** Function calling, MCP, CodeAct, computer use  (Wk 8) 

- **Memory and Context Management** 

- **3** Memory types, context engineering, RAG  (Wk 9) 

- **Harness, Runtime, and Multi-Agent Systems** 

- **4** The loop, harnesses, orchestration  (Wk 10) 

- **Agent Training and Optimization** 

- **5** SFT, RLHF, PPO/GRPO, evaluation  (Wk 11) 

**Industry Applications 6** Deployment, safety, real-world systems  (Wk 12) 



2 

### **Today: Five Questions** 

Five parts · a discussion at the end of each 

|**1**|**From Prompts to a Harness**|What does a loop add to a good prompt?|
|---|---|---|
|**2**|**Agent Runtime**|Where does an action actually run, and<br>safely?|
|**3**|**Workflow and Orchestration**|Which decisions belong in code, not in the<br>model?|
|**4**|**Multi-Agent Systems**|When is a second agent worth its cost?|
|**5**|**Debugging and Evaluation**|Which layer should you repair?|
|**By**|**the end: build a loop, bound it,**|**and know which layer to repair.**|



**OVERVIEW** 3 



## **Part 1 From Prompts to a Harness** 

- Three levels of control: prompt · context · harness 

- You already have the loop — who owns it? 

- State, budgets and stopping 

You have built agents. This is the code around them. 



### **Three Levels of Control** 

Same model, three different things for you to engineer — and a widening scope 

###### **Prompt engineering** 

You control the words of one call e.g. “In 120 words: method, result, one limitation.” 

###### **Context engineering** 

You control what the model is → shown e.g. retrieve the 3 relevant pages, drop the other 200 

###### **Harness engineering** 

You control the loop the calls run in → e.g. run tests → read failure → edit → run again, max 8 turns 



Scope: one request, one reply 

Scope: a whole task, many calls 



**This week is the third level: the code that runs around the calls.** 

**PART 1** 

5 



### **Context Engineering: What the Model Sees** 

The prompt is no longer typed by hand — your program assembles it 

You now choose the retrieved documents, the tool specs, the history and the memory and, just as important, what to leave out 

`# "when is my next assignment due?" retrieve  -> the 3 most relevant course pages memory    -> "this student takes PE6203" assemble  -> instructions + pages + memory + question` **Better answers, still one call — and still no way to act.** 

**PART 1** 6 



### **One Call or a Loop?** 

The same request — “make the failing test pass” — handled two ways 

###### **Without a harness** 

```
user  : make test_login pass
model : "change auth.py line 42
to use token.get()"
# never ran the test
# never saw the error
```

Guessed from memory — often wrong, and nothing checks it 

###### **With a harness** 

`run_tests()  -> KeyError 'token' open_file()  -> lines 40-60 edit_file()  -> patch applied run_tests()  -> PASS # stops on a real signal` Grounded in what the tools returned, and verified before it stops 



**The loop is not a better prompt. It is the ability to look before deciding.** 

**PART 1** 

7 



### **You Already Have the Loop. Who Owns It?** 

You have written this loop already — five lines, and only one of them is the model 

```
while not done:
context = assemble(state)                 # you
action  = validate(model.decide(context))  # model, then you
state   = update(state, run(action))      # you
done    = should_stop(state)              # you
```

**Already known** Reason, call a tool, read the result (Weeks 7–9) **New this week** Everything that makes that loop bounded, safe and debuggable 



**Harness engineering is the discipline of owning the other four lines.** 

**PART 1** 8 



### **What the Harness Owns** 

Three groups of duties, all of them ordinary deterministic code 

**1** Assemble the context, and keep it inside its budget what goes in, what is summarised, what is dropped 

- **2** Validate the proposed action before anything runs does the tool exist, is the schema right, is this allowed 

- **3** Write the result back, then decide whether to continue the observation must reach state, or the loop repeats itself 



**Model output is untrusted input. Validate it before you execute it.** 



**PART 1** 9 

### **State: What the Loop Remembers** 

If it is not in state, the next turn cannot see it 

**Goal** 

The request and its hard constraints  — “make test_login pass, do not touch other files” 



**Trajectory Results** 

Every action and every observation  — “run_tests() → KeyError 'token'” Structured findings, not raw text  — {"failing_test": "test_login"} 



**Counters Flags** 

Steps, tokens, time, cost  — “step 4 of 8, 12k tokens” Awaiting approval · terminated · reason for failure 



**PART 1** 

10 

### **Budgets and Stopping** 

A loop needs at least one condition that does not depend on the model 

**Success** 

The goal test passes — checked in code, not claimed by the model 



**Exhaustion** 

A step, token, time or cost budget is spent 



**No progress** 

The same action repeats, or state stops changing 



**When a budget runs out, return partial results and a reason — never report success.** 

**PART 1** 

11 



### **Example: Fixing a Failing Test** 

Four turns of one loop, and what each layer contributed 

```
turn 1  run_tests()   -> FAIL: KeyError 'token'
turn 2  open_file(...) -> returns lines 40-60
turn 3  edit_file(...) -> patch applied
turn 4  run_tests()   -> PASS
```

The model chose which file to open and what to change 

The harness fed each result back, counted the turns, and read PASS as the stop condition 



**PART 1** 12 

### **Why Does It Repeat?** 

This loop never finishes. Read the trace, then identify which harness duty is missing. 

**DISCUSSION  |  6 MIN** 

**<mark>Options   assemble · validate · write back · stop condition</mark>** 

```
step 1  model -> run_tests()   ; obs: FAIL test_login
step 2  model -> run_tests()   ; obs: FAIL test_login
step 3  model -> run_tests()   ; obs: FAIL test_login
...     identical prompt every turn, max_steps never reached
```

- What does the model see at the start of step 2? Which of the harness's three duties was skipped? 



<!-- Start of picture text -->
fo] NANYANG TECHNOLOGICAL UNIVERSITY SINGAPORE<br><!-- End of picture text -->

**PART 1** 13 

### **The Observation Never Reached State** 

Same state in, same context out, same action back — forever 

**DISCUSSION ANSWER** 

**The defect** 

run_tests() returned, but the result was never written into state 



**The consequence** 

assemble(state) builds an identical prompt, so the model repeats an identical action 



**The repair** 

state = update(state, obs) — and a max_steps guard that is actually enforced 



**Two lines: write the result back, and cap the loop.** 

**PART 1** 

14 



## **Part 2 Agent Runtime** 

- Where the harness ends 

- Errors, retries and checkpoints 

- Idempotency and permission 

Making the loop execute safely 



### **Harness or Runtime?** 

Both impose limits, for entirely different reasons 

###### **Harness** 

Decides what to do next, and when the task is done. Task logic lives here. e.g. stop after 8 steps, or when the tests pass 



###### **Runtime** 

Decides how an action executes and what it may touch. Safety lives here. e.g. kill the call after 60s; mount the repo read-only 

**The test** Would this limit still be needed if the task changed? If yes, it belongs to the runtime. e.g. a timeout survives any change of task 



**Task logic in the harness; execution safety in the runtime.** 

**PART 2** 



16 

### **What the Runtime Manages** 

The environment an action executes in — defined by its isolation, not by whose machine it is 

**Isolation** 

A container, or enforced OS-level isolation 



**Access** 

Filesystem scope, network egress, and credentials injected at execution — never inside a prompt **Limits** 

CPU, memory, disk, concurrency, and a per-call timeout 



<!-- Start of picture text -->
{ i Isolation<br>' poten<br>or wee<br>: Runtime Container<br>DB nme 4] QB Ferrero<br>eon essen DF ictamncan<br>“halon |B reworcenee Limits<br>| P wemdertetie 3 DY) cr mame<br>| GQ) womeaments | fences<br>BP) ResultcomatedevonArtifact<br>om<br><!-- End of picture text -->



**The anti-pattern: an agent running shell commands with no enforced boundary.** 

**PART 2** 

17 



### **Not Every Error Deserves a Retry** 

Classify the failure first; the policy follows from the class **CLASS EXAMPLE POLICY Transient** 503, timeout, 429 Bounded retry + backoff **Permanent** 403 denied Do not retry; escalate **Malformed** Invalid JSON Repair input, then retry **Fatal** Revoked key Terminate and report **Ask whether repeating this identical call could plausibly succeed.** 



**PART 2** 18 

### **Checkpoints and Recovery** 

Persist state at a meaningful step, so work resumes instead of restarting 

```
checkpoint.save(task_id, step=3, state)
# ... crash, pre-emption, or a timeout ...
state = checkpoint.load(task_id)
# resumes at step 3, not step 0
```

Checkpoint at a boundary that means something, not every step e.g. after each paper is summarised — not after each token 

- A 40-minute run that dies at minute 38 should resume at minute 38 e.g. 12 of 14 papers already written to disk; only 2 remain 



**The hard question is not saving state; it is whether replay repeats a side effect.** 

**PART 2** 19 



### **Why Replay Is Dangerous** 

Retry safety is a property of the operation, not of the word “read” 

**No idempotency guarantee** `send_email(...)      -> TIMEOUT pay_invoice(...)     -> TIMEOUT create_ticket(...)   -> TIMEOUT # did it happen? unknown` A timeout says nothing; a blind retry may do it twice 

###### **Idempotent by construction** 

`search(...)          -> TIMEOUT get_order(...)       -> TIMEOUT pay(..., key=K)      -> TIMEOUT # repeating lands in the same state` Same request, same outcome — so retry freely 



**Make the operation idempotent, then a retry is safe by construction.** 

**PART 2** 



Idempotency-key practice per Stripe API docs; exactly-once discussion per Temporal docs. 

20 

### **Idempotency Keys** 

Make the same request twice; make it happen once 

```
key = hash(task_id + recipient + hash(body))
if log.has_receipt(key):
return log.get_receipt(key)   # done
r = service.call(..., idempotency_key=key)
log.save_receipt(key, r)
```

The key is derived from the request, so a retry produces the same key The receipt is written before the loop moves on 



**PART 2** 21 

### **Example: The Invoice Paid Twice** 

A $8,400 duplicate payment, and not one model mistake 

```
[1] agent   -> pay_invoice(INV-2231, 8400)
```

- `[2] bank    -> paid, then the network drops` 

- `[3] agent   -> sees TIMEOUT, assumes failure` 

- `[4] runtime -> resumes from the checkpoint` 

- `[5] agent   -> pay_invoice(...)  <- paid twice` 

The checkpoint was taken before the payment, so replay re-ran it 

The call carried no idempotency key, so the bank could not de-duplicate 



**PART 2** 22 

### **Choose a Retry Policy** 

For each failure, write the policy you would implement — and say what must be true before any retry is safe. 

**DISCUSSION  |  6 MIN** 

**<mark>Options   transient · malformed · permanent · fatal</mark> FAILURE RETRY?** 

**WHAT INSTEAD** 



**429 rate limited** 



**403 permission denied** 



**send_email timed out** 



**Invalid JSON from the model** 

**PART 2** 



<!-- Start of picture text -->
fo] NANYANG TECHNOLOGICAL UNIVERSITY SINGAPORE<br><!-- End of picture text -->

23 

### **One Policy per Class** 

Only the third one is about the world rather than the call 

**DISCUSSION ANSWER** 

**POLICY** 

**FAILURE POLICY 429 rate limited** Bounded retry, exponential backoff with jitter **403 permission denied** Never retry; escalate or reroute **send_email timed out** Retry only with an idempotency key, or check for a receipt first **Invalid JSON** Repair or re-ask once, then fail loudly **A timeout on a write is not a failure — it is an unknown.** 

**PART 2** 24 



##### **Part 3** 

**Workflow and Orchestration** 

- Loop or workflow? 

- State machines and contracts 

- Verifiers and terminal states 

Turning a vague request into a process 



### **Agent Loop or Workflow?** 

Flexibility and predictability pull in opposite directions 

**Agent loop** 

The next step is decided at run time; adapts, but is hard to reproduce 



**Workflow** 

Steps and transitions fixed in advance; auditable, but rigid when reality differs 

Real systems combine them: an outer workflow fixes the shape, and a constrained loop sits inside particular nodes. 



**For each step ask: do I need a guarantee here, or flexibility?** 

**PART 3** 



26 

### **Five Control Structures** 

Almost every agent workflow is built from these 

**Sequence Branch Loop Parallel Gate** fixed order explicit condition, bounded, with an disjoint writes only verifier or person → evaluated by code → exit → → **Never the model** Whether a required check has run, or whether the workflow is **alone** complete **The trap** A loop whose only exit condition is the model saying “I am done” 



**Code owns which structure runs; the model only fills in a node.** 

**PART 3** 



27 

### **Workflows as State Machines** 

The grading assistant, drawn as explicit states and conditional edges 

```
VERIFY GRADE  pass               -> FINAL REVIEW
VERIFY GRADE  fail & attempts <2 -> RE-GRADE
VERIFY GRADE  fail & attempts>=2 -> HUMAN ESCALATION
FINAL REVIEW  approve            -> RELEASED
FINAL REVIEW  cancel             -> CANCELLED
```

Every edge carries its condition, so the path is reviewable 

RELEASED and CANCELLED are terminal — no outgoing edges 



<!-- Start of picture text -->
Loap veriey | | FINAL<br>‘SUBMISSION GRADE REVIEW<br>= ' bj i<br>iH stamps?tna| 1| auampte>efoe  2 pals,H<br>(marten) H H H<br>=) Ga]<br>fe ead anew = nerstortion } i<br>| nase rasa ron ceo rycen| waz<br>1 reed<br>or tte i —-<br>fo<br><!-- End of picture text -->



**Every terminal state is explicit, so the process cannot end by accident.** 

Graph-of-nodes formulation per LangGraph docs (langchain-ai.github.io/langgraph). 



<!-- Start of picture text -->
G@ Nanvanc TECHNOLOGICAL UNIVERSITY SINGAPORE<br><!-- End of picture text -->

**PART 3** 28 

### **Contracts and Verifiers** 

Give every node a schema, then check it against criteria defined independently of the node 

```
{ "rubric_items": [ { "criterion_id": str, "score": num,
"max_score": num, "evidence": [str] } ],
"total_score": num, "flags": [str] }
```

Is the output structurally valid? 

**Contract Verifier** 

**Verifier** Checks an output against criteria set in advance, independent of it — tests, arithmetic checks, environment feedback, a rubric or human review **The real failure** “Looks fine” with no criteria — a second model may verify, but only against criteria it did not invent 



**A verifier is defined by its criteria, not by whether it happens to be code.** 

**PART 3** 29 



### **Example: A Grading Assistant** 

Draft feedback on 60 submissions; no mark reaches a student unchecked 

**DESIGN WHAT HAPPENED** 



**Free-form: grade, then publish** Three scripts cited a rubric item that does not exist **Explicit states, with a gate** LOAD SUBMISSION → GRADE → VERIFY GRADE → FINAL REVIEW → RELEASED. VERIFY GRADE is deterministic: every comment must cite a real rubric id, or the work returns to RE-GRADE 



**Bounded retry** At most two RE-GRADE attempts; after that the graph routes to HUMAN ESCALATION rather than looping 



**The gate that mattered was three lines of code, not a better prompt.** 

**PART 3** 

30 



### **Audit This Workflow** 

Six of these seven statements describe a real defect. Name the six, and say what each one breaks. 

**DISCUSSION  |  7 MIN** 

**<mark>Options   lost update · no criteria · wrong retry · unvalidated · unenforced · unverified completion</mark>** 

- a  Two parallel nodes both write to state.summary 

- b  The loop's exit condition is “the model says it is done” 

- c  The verifier is another model asked whether the draft looks fine 

- d  Retry on a 403 with the same credentials 

- e  Nodes exchange a single free-text blob 

- f  A step limit is declared but never checked 

- g  A person approves before anything is sent 



<!-- Start of picture text -->
fo] NANYANG TECHNOLOGICAL UNIVERSITY SINGAPORE<br><!-- End of picture text -->

**PART 3** 31 

### **Six Defects, One Sound Choice** 

g is the only one of the seven that is not a defect 

**DISCUSSION ANSWER** 

**a** Two writers, one field — a lost update **b** A model's claim of completion is not a completion check **c** No criteria, so nothing is actually verified **d** A permission error cannot be fixed by repetition **e** Unstructured handoff with no agreed contract or validation **f** A limit that is never enforced is not a limit 



**g** 

Exactly right — a person approves before anything is sent 

**PART 3** 

32 



## **Part 4 Multi-Agent Systems** 

- Three things that look alike 

- When splitting helps 

- Four coordination patterns 

When is more than one agent worth it? 



### **Three Things That Look Alike** 

Cost and complexity rise at every step 

###### **Calling a model many times does not make a multi-agent system.** 

###### **Single agent** 

One loop, one state, advancing in sequence. e.g. cost $ · coordination none 

###### **Parallel calls** 

One agent issuing independent calls and aggregating them. e.g. cost $$ · coordination inside one loop 

###### **Multi-agent** 

Distinct goals, separate context and tools, explicit coordination — an architectural choice, not 

more autonomy. e.g. cost $$$ · coordination is now your problem 



**Always ask whether the simpler option already solves the problem.** 



**PART 4** 

34 

### **When Splitting the Work Helps** 

And when the coordination costs more than it saves 

###### **It helps** 

Sub-tasks are genuinely independent, share almost no writes, and can be verified separately. e.g. summarise 40 unrelated papers, one worker each 

###### **It hurts** 

Strong shared state, frequent write conflicts, or each step needs the previous one's full context. e.g. refactor one file until its tests pass 



**With strong shared state, a single agent is usually faster and steadier.** 

**PART 4** 



35 

### **Pattern 1: Orchestrator and Workers** 

One lead agent assigns; each worker writes its own artifact 

The lead decomposes the task and hands each worker a contract 

Each worker returns an artifact, not an edit to shared state 



- A reducer combines the artifacts into the final answer 

Every contract names its own write scope, so two workers can never target one file 

The orchestrator-workers workflow from: _https://www.anthropic.com/engineering/building-effective-agents_ 

The lead reads artifacts; it never edits them 



**Write scope prevents overwrites, not lies — a corrupted artefact crosses it intact.** 

Anthropic, Building Effective Agents (2024), “Orchestrator-workers”. 

**PART 4** 



36 

### **Pattern 2: Pipeline with Handoff** 

A task moves through stages, one owner each — an orchestration pattern, not inherently multi-agent 

- Extract → summarise → proofread → format, one owner per stage 

- Each stage produces its own artifact, so a failure is localised 

- The cost: a mistake early on is carried all the way down 

The prompt-chaining workflow from: _https://www.anthropic.com/engineering/building-effective-agents_ 



**Every handoff is a natural place to verify.** 

Anthropic, Building Effective Agents (2024), “Prompt chaining”. 

**PART 4** 



37 

### **Patterns 3 and 4** 

Generator with a critic, and the shared blackboard 

###### **Generator and critic** 

One produces, one judges against explicit rules. Often one agent in two roles — not inherently multi-agent. e.g. draft a clause, then check it against a rubric 

###### **Blackboard** 

Agents share one workspace. Most flexible, most failure-prone. e.g. four agents editing one plan.md — who wins? 

**The rule** Choose the least coordination that still solves the task. e.g. if one loop can do it, use one loop 



**A critic needs criteria fixed in advance, or it only adds cost.** 

Generator-critic per Anthropic (2024) “Evaluator-optimizer”; blackboard per Hayes-Roth (1985). 

**PART 4** 



38 

### **Task Contracts and Failure Modes** 

What an assignment must state, and how coordination goes wrong 

```
{ "goal": str, "inputs": [...], "output_schema": {...},
"budget": {"steps": 8}, "write_scope": ["artifacts/a.md"] }
```

Lost update: two agents write the same field e.g. worker-B and worker-C both save to state.summary Duplicated work: two agents solve the same sub-task e.g. both search “paper A” because neither claimed it 

Deadlock: each waits for the other's artifact e.g. the writer waits for the reviewer, who waits for the writer 



**Give every field exactly one owner, or you will debug a lost update.** 

**PART 4** 39 



### **Example: A Literature Review** 

Same task, twelve papers — one agent, or four workers? 

|**DESIGN**|**TOKENS**|**COVERAGE**|**VERDICT**|
|---|---|---|---|
|**One agent, papers in**|41k|11 / 20|Cheapest, and it|
|**sequence**|||misses things|
|**Four workers + a**|88k|16 / 20|Twice the cost, five|
|**reducer**|||points better|



It paid off here because each paper was independent and each worker wrote its own file 

e.g. change the task to “write one coherent survey” and the same split gets worse, not better 



**Split the work only when the sub-tasks really are independent.** 

Coverage is out of 20 key claims. Figures are illustrative teaching numbers, not results from a published experiment. 

**PART 4** 

40 



### **Choose an Architecture** 

For each task, choose the simplest architecture that works, and name the one risk your choice carries. 

**DISCUSSION  |  7 MIN** 

**<mark>Options   single loop · parallel workers · generator-critic · workflow</mark>** 

**TASK YOUR CHOICE** 

**THE RISK** 



**Summarise 40 unrelated papers** 



**Refactor one file until its tests pass** 



**Draft, then check, a legal clause** 



**Plan a trip: flights, hotel, budget** 



<!-- Start of picture text -->
fo] NANYANG TECHNOLOGICAL UNIVERSITY SINGAPORE<br><!-- End of picture text -->

**PART 4** 41 

### **The Simplest Thing That Works** 

Only one of the four needs more than one agent 

**DISCUSSION ANSWER TASK ARCHITECTURE WHY 40 unrelated papers** Parallel workers + reducer Independent, no shared writes **Refactor one file** Single agent loop Every step needs the previous one's full context **Draft, then check** Generator and critic The criteria are explicit and checkable **Plan a trip** Workflow with a shared plan Coupled constraints, so coordination beats splitting 



**PART 4** 

42 

##### **Part 5** 

## **Debugging and Evaluation** 

- Reading a trace 

- Symptom, cause, repair layer 

- What to measure 

Judging whether a design is any good 



### **How to Read an Execution Trace** 

Four passes over the same trace, in this order 

- **1** Read the state at step 0, then watch what changes 

- **2** Mark the first departure from expectation 

- **3** Mark swallowed errors, and actions that repeat **4** Check the budget: how many steps, spent on what 





**The final error message is usually far from the actual cause.** 



<!-- Start of picture text -->
g NANYANG TECHNOLOGICAL UNIVERSITY SINGAPORE<br><!-- End of picture text -->

**PART 5** 

44 

### **Symptom, Cause, Repair Layer** 

Three different questions that are easy to conflate 

**SYMPTOM ROOT CAUSE Two identical emails** A replayed side effect **A topic is missing** No completeness check **A call repeats forever** Observation not stored 

**REPAIR** Harness: an idempotency key 

Workflow: add a verifier 

Harness: write results back 



**Keep them separate, or you fix the symptom and leave the mechanism.** 

Broadly, “harness” covers all of this — workflow, coordination, runtime. Split here only to locate a repair. 

**PART 5** 45 



### **Why Many “Model Problems” Are Not** 

Four familiar complaints, and what they usually turn out to be 

**THE COMPLAINT WHAT IT USUALLY IS “It forgets what it was doing”** State was never written back 



**“It loops forever”** No enforced stop condition **“It delivers nonexistent** No citation check between drafting and delivery **sources” “It is too slow”** Serial tool calls, or no caching 



46 

**PART 5** 

### **What to Measure** 

Accuracy alone hides both cost and side effects 

###### **Outcome** 

Success rate, correctness, and coverage of what was actually asked for. e.g. did every requested topic appear in the report? 

###### **Efficiency & cost** 

Steps, tool calls, latency, tokens, and cost per completed task. e.g. 88k tokens for a 5-point gain — worth it here? 

###### **Reliability** 

Failure rate, recovery rate, and repeated side effects. e.g. how many runs sent the same email twice? 

A minimal ablation, four conditions: baseline · full system · full minus reviewer · full minus memory — same task set under each 

No difference is evidence to weigh, not proof it was decoration 



Metric set after Yehudai et al., Survey on Evaluation of LLM-based Agents (2503.16416). 

**PART 5** 

47 

|**Example:**|**Error Analysis**|||
|---|---|---|---|
|14 of 40 runs failed|— the team read every failing trace befo|re changing anything||
|**LAYER**|**WHAT FAILED**|**FAILING RUNS**|**THE FIX**|
|**Harness**|The observation was<br>never written back|7|one line: state =<br>update(state, obs)|
|**Harness**|A step limit was never<br>checked|3|enforce it in the loop|
|**Workflow**|No completeness<br>check before delivery|2|add a verifier before<br>send|
|**Model**|Genuinely wrong<br>answer|2|still unresolved|
|**Changing the m**|**odel first would have fixed 2 of**|**the 14. The harness**|**fixed 10.**|



Figures are illustrative teaching numbers, not results from a published experiment. 

**PART 5** 

48 



### **Attribute Each Symptom** 

For each symptom, name the layer where the repair belongs. A layer may be used more than once. 

**DISCUSSION  |  7 MIN** 

**<mark>Options   model · harness · runtime · workflow · coordination</mark>** 

```
[01] planner  -> tasks = [A, B, C]   max_steps = 6
[02] worker-A -> search("A") -> TIMEOUT
[03] harness  -> retry immediately -> TIMEOUT
[05] worker-B, worker-C -> both saved to state.summary
[07] writer   -> send_email(...) -> SUCCESS
[08] harness  -> restart from step 01, writer sends again
[10] final    -> "All three topics were delivered."
```

- a instant retry · b overwritten field · c sent although A failed · d email twice · e past max_steps · f untrue claim 



<!-- Start of picture text -->
fo] NANYANG TECHNOLOGICAL UNIVERSITY SINGAPORE<br><!-- End of picture text -->

49 

**PART 5** 

### **Where Each Repair Belongs** 

|Six symptoms, four different places to fix them — and none of them the model|
|---|
|**DISCUSSION ANSWER**|
|**SYMPTOM**<br>**LAYER**<br>**REASONING**|
|**a  Instant retry**<br>Harness<br>Retry scheduling is loop control|
|**b  Overwritten field**<br>Coordination<br>Two agents, one write target|
|**c  Sent although A failed**<br>Workflow<br>No gate before delivery|
|**d  Email twice**<br>Harness<br>A replayed side effect|
|**e  Past max_steps**<br>Harness<br>Declared, never enforced|
|**f  Untrue claim**<br>Workflow<br>Completion was never checked|
|**Three sit in the harness loop, two in the workflow, one in coordination.**|



Broadly, “harness” covers all of this — workflow, coordination, runtime. Split here only to locate a repair. 

**PART 5** 

50 



**What Each Layer Is Responsible For** tay) 2 Se Five layers, and the one thing each of them has to get right Sh **Harness** Closes the loop, and stops it **Runtime** Executes safely, survives failure **Workflow** Makes the process inspectable **Coordination** Only where the work decomposes **Evaluation** Finds the cheap fix **The model supplies intelligence. The system supplies reliability. WRAP-UP** 51 





<!-- Start of picture text -->
aoe<br>Wee7<br>sos<br><!-- End of picture text -->

# Thanks 

#### Q&A 



52 

