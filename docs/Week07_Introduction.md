**Agentic AI** Designing, Building, and Optimizing Autonomous AI Systems 

Prof Bo AN https://personal.ntu.edu.sg/boan/ _Email_ : boan@ntu.edu.sg _Office_ : S3-B2C-83 

## **Roadmap** 

- **Introduction to Agentic AI   (with hands-on session)** 

- **1** Agents, autonomy, reasoning & planning 

- **Tools, Skills, and Action Interfaces (with hands-on session)** 

- **2** Function calling, MCP, CodeAct, computer use 

- **Memory and Context Management (with hands-on session)** 

- **3** Memory types, context engineering, RAG 

- **Harness, Runtime, and Multi-Agent Systems (with hands-on session)** 

- **4** The loop, harnesses, orchestration 

- **Agent Training and Optimization** 

- **5** SFT, RLHF, PPO/GRPO, evaluation 

**Industry Applications 6** Deployment, safety, real-world systems 



2 

## **Today: Five Questions** 

- **1 From AI to Agentic AI** What changed from answering to acting? 



- **2 What Makes a System Agentic?** Who decides the next step? 



- **3 Anatomy of an AI Agent** Which components make action possible? 



- **4 Reasoning and Planning in Agents** How are complex tasks broken down? 



- **5 How Agents Work** How does the loop run and recover? 



**By the end: classify agentic systems, explain the core components, and trace an agent loop.** 



**OVERVIEW** 

3 

###### **Part 1** 

### **From AI to Agentic AI** 

- Traditional AI, Generative AI, Agentic AI 

- Prompt → response vs. goal → outcome 

- A practical definition of agency 

From prediction to goal-directed action 



#### **Three AI System Patterns — Real Tasks** 

The difference is the kind of result the system is designed to produce. 

###### **TRADITIONAL AI** 

**Classify an image** 



Image → labels Street · Town · Snapshot 

**GENERATIVE AI** 

**Write a summary** 



Prompt: Summarize the notice. Response: The library closes at 17:00 today. 

**Prompt → response** 

**AGENTIC AI** 

**Fix a software bug** 



Inspect files → edit code → run tests → revise 

**Goal → actions → verified outcome** 

<u>Source: Google Cloud Vision label detection</u> 

<u>model image: DeepSeek official site</u> 

<u>Source: OpenAI Codex official repository</u> 



5 

**PART 1** 

#### **Running Example: Fix a Failing Online Checkout Test** 

Background: after a coupon is applied, the checkout test expects a total of $80 but receives $100. 

**TRADITIONAL AI** 

###### **GENERATIVE AI** 

###### **AGENTIC AI** 

**Input** 

###### **Prompt** 

###### **Goal** 

Online checkout bug report Test log: expected $80, received $100 

Explain why the coupon total is $100 and suggest a patch 

Make the coupon total $80 without breaking related tests 





**Output Response** Category: payment / severity: high A written diagnosis or suggested code change 



###### **Outcome** 

Relevant files changed; target and related tests pass 

**One prediction** 

**User applies and tests it** 

**System chooses the next step** 

**Agentic AI moves beyond labels and responses to deliver tested, verified outcomes through iterative action.** 



**PART 1** 6 

#### **Prompt–Response vs Goal–Outcome** 

Use these exact terms to distinguish a generative interaction from an agentic task. 



<!-- Start of picture text -->
DIMENSION GENERATIVE AI AGENTIC AI<br>Starting input Prompt Goal<br>Main result Response Outcome<br>Who chooses the next<br>User Model policy<br>step?<br>Interaction pattern One turn Multiple action–observation steps<br>External action – Action<br>These are course-level distinctions: real systems may combine both patterns.<br><!-- End of picture text -->



**PART 1** 7 

#### **Working Definition: One Agent Decision Cycle** 

An AI agent uses current state and observations to choose actions toward a goal. 



<!-- Start of picture text -->
STATE +<br>GOAL — — ACTION — ENVIRONMENT — OBSERVATION<br>MODEL POLICY<br>update state and decide again<br>Observation Feedback<br>Information returned by the environment after an action. The role an observation plays when it changes evaluation<br>or the next decision.<br><!-- End of picture text -->

**Observation is the returned information; it becomes feedback when the agent uses it to adjust.** 



8 

**PART 1** 

#### **Agentic AI in Practice** 

Across domains, the recurring pattern is Goal → Action → Observation → next decision. 

|**SCENARIO**|**GOAL**|**ACTION → OBSERVATION → NEXT DECISION**|
|---|---|---|
|**Software repair**|Make tests pass|Run test → one edge case fails → inspect that case|
|**Research assistant**|Compare evidence|Search sources → results are too broad → narrow the query|
|**Customer service**|Resolve an order issue|Check order → shipment is delayed → offer allowed options|
|**Calendar assistant**|Find a meeting time|Read calendars → no common slot → ask which constraint can change|



**The next decision depends on the latest observation, not on a fully fixed answer path.** 



9 

**PART 1** 

#### **Discussion: Complete the Comparison** 

For each dimension, choose the Agentic AI term that corresponds to the Generative AI term in the same row. Use each term once. **CLASS EXERCISE  |  4 MIN** 

**Word bank: Model policy · Action · Goal ·  Multiple action–observation steps  · Outcome** 

|**DIMENSION**|**GENERATIVE AI**|**AGENTIC AI**|
|---|---|---|
|**Starting input**|Prompt|________________________|
|**Main result**|Response|________________________|
|**Who chooses next step?**|User|________________________|
|**Interaction pattern**|One turn|________________________|
|**External action**|–|________________________|





<!-- Start of picture text -->
fo] NANYANG TECHNOLOGICAL UNIVERSITY SINGAPORE<br><!-- End of picture text -->

10 

**PART 1** 

#### **Discussion: Answer** 

For each dimension, choose the Agentic AI term that corresponds to the Generative AI term in the same row. Use each term once. **ANSWER** 

###### **Word bank: Model policy · Action · Goal ·  Multiple action–observation steps  · Outcome** 

|**DIMENSION**|**GENERATIVE AI**|**AGENTIC AI**|
|---|---|---|
|**Starting input**|Prompt|**Goal**|
|**Main result**|Response|**Outcome**|
|**Who chooses next step?**|User|**Model policy**|
|**Interaction pattern**|One turn|**Multiple action–observation steps**|
|**External action**|–|**Action**|





<!-- Start of picture text -->
fo] NANYANG TECHNOLOGICAL UNIVERSITY SINGAPORE<br><!-- End of picture text -->

**PART 1** 11 

#### **Discussion: Label an Agent Trajectory** 

A coding agent is trying to fix a failing checkout test. Label what it wants, knows, does, receives, and decides. **CLASS EXERCISE  |  5 MIN** 

**Labels: Action ·  State  · Goal · Policy decision · Observation** 

|**#**|**TRACE STATEMENT**|**YOUR LABEL**|
|---|---|---|
|**1**|Make the failing checkout test pass without breaking other tests.|____________|
|**2**|The repository is open; checkout_test.py is currently failing.|____________|
|**3**|The agent runs the checkout test.|____________|
|**4**|The test reports: coupon_total expected 80, received 100.|____________|
|**5**|The agent decides to inspect the coupon calculation next.|____________|





<!-- Start of picture text -->
fo] NANYANG TECHNOLOGICAL UNIVERSITY SINGAPORE<br><!-- End of picture text -->

12 

**PART 1** 

#### **Discussion: Answer** 

A coding agent is trying to fix a failing checkout test. Label what it wants, knows, does, receives, and decides. 

###### **ANSWER** 

###### **Labels: Action ·  State  · Goal · Policy decision · Observation** 

|**#**|**TRACE STATEMENT**|**YOUR LABEL**|
|---|---|---|
|**1**|Make the failing checkout test pass without breaking other tests.|**Goal**|
|**2**|The repository is open; checkout_test.py is currently failing.|**State**|
|**3**|The agent runs the checkout test.|**Action**|
|**4**|The test reports: coupon_total expected 80, received 100.|**Observation**|
|**5**|The agent decides to inspect the coupon calculation next.|**Policy decision**|





<!-- Start of picture text -->
fo] NANYANG TECHNOLOGICAL UNIVERSITY SINGAPORE<br><!-- End of picture text -->

13 

**PART 1** 

###### **Part 2** 

**What Makes a System Agentic?** 

- Chatbot vs. workflow vs. agent 

- Who decides the next step? 

- Autonomy, capability, cost, and risk 

Agency is a spectrum, not a binary label 



#### **Chatbot, Workflow, and Agent — Concrete Examples** 

The visible interface may look similar; the control flow is what differs. 

**CHATBOT WORKFLOW DeepSeek chat Fixed document pipeline Extract Validate Store** User sends message Developer fixes the sequence. → model returns response The same step order runs each time. → user decides whether to continue 

**AGENT Codex / Claude Code** 



Model chooses among read, edit, test, or ask after each observation. 

<u>Workflow concept: Anthropic, Building Effective Agents</u> 



<u>OpenAI Codex official repository</u> 

<u>DeepSeek official site</u> 

15 

**PART 2** 

#### **Who Decides the Next Step?** 

A workflow follows developer-defined edges; an agent selects an action from the current state. 



<!-- Start of picture text -->
A. PREDEFINED WORKFLOW B. DYNAMIC AGENT<br>STATE +<br>Input Extract Validate Store Output ACTION ENV.<br>MODEL POLICY<br>Decision maker: developer-defined sequence<br>If validation fails, any alternate edge must also be designed in  OBSERVATION<br>advance.<br><!-- End of picture text -->

**Decision maker: model policy, bounded by available actions and permissions** 

**Observation must return to State; otherwise the next choice cannot respond to what happened.** 



16 

**PART 2** 

#### **Three Permission Levels for Agent Actions** 

Autonomy is assigned per action, not as one vague label for the whole system. 



<!-- Start of picture text -->
REQUIRE CONFIRMATION<br><!-- End of picture text -->

**EXECUTE AUTOMATICALLY** 

**DO NOT ALLOW EXECUTION** The action is outside the agent's authority in this system. 

The agent may perform the action The agent prepares the action, The action is outside the agent's when its conditions are met. then waits for a person to approve authority in this system. it. Example: search a public help article Example: submit a support ticket Example: reset another user's password 

**Permission level depends on impact, reversibility, authorization, and recovery cost.** 



<!-- Start of picture text -->
g NANYANG TECHNOLOGICAL UNIVERSITY SINGAPORE<br><!-- End of picture text -->

17 

**PART 2** 

#### **Choosing an Action Permission** 

Use four questions before assigning one of the three levels. 

**1** 

###### **IMPACT** 

Could this affect money, many people, or official records? 

**2** 

###### **REVERSIBILITY** 

Can the action be undone quickly and completely? 

###### **AUTHORIZATION** 

**3** Does the user clearly have the right to approve it? 

**4** 

###### **RECOVERY** 

If it fails, can the system detect and safely recover? 

**Search public help → Automatic** 

**Submit support ticket → Confirm** 

**Reset another user's password → Do not allow** 



18 

**PART 2** 

#### **Discussion: Reconstruct Control Flows** 

For a fixed document-processing workflow and a dynamic agent cycle, reconstruct the order and identify who chooses the next step. **CLASS EXERCISE  |  5 MIN** 

**A. PREDEFINED WORKFLOW** 

**B. DYNAMIC AGENT CYCLE** 

**Shuffled:  Store · Input · Validate · Output · Extract** 

**Shuffled:  Observation · Environment · State + Model policy · Action** 



<!-- Start of picture text -->
Write the sequence: Write the sequence:<br>________________________ ________________________<br>Next-step decision maker: __________________ Next-step decision maker: __________________<br><!-- End of picture text -->

**For B, add one short phrase showing where the cycle returns after Observation.** 



<!-- Start of picture text -->
fo] NANYANG TECHNOLOGICAL UNIVERSITY SINGAPORE<br><!-- End of picture text -->

19 

**PART 2** 

#### **Discussion: Answer** 

For a fixed document-processing workflow and a dynamic agent cycle, reconstruct the order and identify who chooses the next step. **ANSWER** 

**A. PREDEFINED WORKFLOW** 

**B. DYNAMIC AGENT CYCLE** 

**Shuffled:  Store · Input · Validate · Output · Extract** 

**Shuffled:  Observation · Environment · State + Model policy · Action** 

**Sequence: Input → Extract → Validate → Store → Output** 

**Sequence: State + Model policy → Action → Environment → Observation** 

**Next-step decision maker: developer-defined sequence** 

**Next-step decision maker: model policy within allowed actions** 

**After Observation: update State, then begin the next decision cycle.** 



<!-- Start of picture text -->
fo] NANYANG TECHNOLOGICAL UNIVERSITY SINGAPORE<br><!-- End of picture text -->

20 

**PART 2** 

#### **Discussion: Set Action Permissions** 

A school is configuring a Campus Event Assistant. Assign one permission level to each of its six possible actions. **CLASS EXERCISE  |  7 MIN** 

|**ACTION**|**EXECUTE**<br>**AUTOMATICALLY**|**REQUIRE**<br>**CONFIRMATION**|**DO NOT ALLOW**<br>**EXECUTION**|
|---|---|---|---|
|Check classroom availability|□|□|□|
|Recommend venues|□|□|□|
|Reserve a venue|□|□|□|
|Draft an invitation email|□|□|□|
|Send emails to 300 students|□|□|□|
|Make a payment to a vendor|□|□|□|





<!-- Start of picture text -->
fo] NANYANG TECHNOLOGICAL UNIVERSITY SINGAPORE<br><!-- End of picture text -->

21 

**PART 2** 

#### **Discussion: Answer** 

A school is configuring a Campus Event Assistant. Assign one permission level to each of its six possible actions. 

###### **ANSWER** 

|**ACTION**|**EXECUTE**<br>**AUTOMATICALLY**|**REQUIRE**<br>**CONFIRMATION**|**DO NOT ALLOW**<br>**EXECUTION**|
|---|---|---|---|
|Check classroom availability|✓|||
|Recommend venues|✓|||
|Reserve a venue||✓||
|Draft an invitation email|✓|||
|Send emails to 300 students||✓||
|Make a payment to a vendor|||✓|





<!-- Start of picture text -->
fo] NANYANG TECHNOLOGICAL UNIVERSITY SINGAPORE<br><!-- End of picture text -->

22 

**PART 2** 

###### **Part 3** 

**Anatomy of an AI Agent** 

- Goal and model policy 

- Tools, memory, environment, and feedback 

- Reflection, evaluation, and harness 

The model supplies a decision policy; the system determines what it can do 



#### **Core Components: Implementation View** 

Slide 8 defined one decision cycle; this page shows the parts that implement and control it. 



<!-- Start of picture text -->
GOAL TOOLS / ACTIONS<br>desired result + stop condition interfaces that do work<br>MODEL / POLICY<br>selects the next action<br>Reasoning / planning and evaluation shape decisions<br>MEMORY / CONTEXT ENVIRONMENT<br>task-relevant state returns observations<br>HARNESS / RUNTIME  ·  loop · permissions · budgets · logs<br><!-- End of picture text -->



24 

**PART 3** 

#### **Running Example: Travel Planning Assistant** 



<!-- Start of picture text -->
USER REQUEST FIXED CONSTRAINTS<br>Plan a weekend trip from Singapore to Kuala  • Depart Friday after 10:00<br>Lumpur. • Prefer train travel<br>• Train + hotel ≤ SGD 500<br>Starting state • Check cancellation terms<br>No itinerary has been selected yet. • Booking requires confirmation<br><!-- End of picture text -->

**Success: one feasible itinerary with verified availability, cost, and terms; no booking without confirmation.** 



25 

**PART 3** 

#### **Model and Goal** 

The model proposes decisions; the goal tells the system what counts as progress and completion. 



<!-- Start of picture text -->
Chat with DeepSeek Al<br><!-- End of picture text -->

###### **TWO DIFFERENT RESPONSIBILITIES** 

Given current State, choose or rank a **MODEL / POLICY** next Action. Specify the desired Outcome, **GOAL** constraints, and stop condition. 

Concrete model example: DeepSeek A model can generate or score candidate next steps. 

**A foundation model is one component; it becomes part of an agent only inside a loop with state and actions.** 



<u>Image/source: DeepSeek official site</u> 

26 

**PART 3** 

#### **Tools and Actions** 

A tool exposes a bounded interface; an action is one concrete invocation through that interface. 



<!-- Start of picture text -->
SEARCH search_trains(from, to,  → Returns departure times, seats,  Find Friday trains after 10:00<br>depart_after) and fares<br>CALENDAR check(date, time) → Returns user availability Confirm the user is free at 11:00<br>CALCULATOR total(items) → Returns calculated cost Add train fare and hotel cost<br>Tool schema constrains requests; permissions constrain execution.<br><!-- End of picture text -->



27 

**PART 3** 

#### **Memory and Context** 

Context is what the model can use now; memory is how useful information is retained or retrieved. 



<!-- Start of picture text -->
CURRENT CONTEXT WINDOW<br>PERSISTENT MEMORY<br>write<br>Goal: feasible trip within SGD 500 —___»<br>Travel preferences<br>Past itinerary choices<br>Saved loyalty details<br>Recent searches and calendar observations<br>|<br>retrieve<br>Candidate schedules, fares, and terms<br>Keeping everything is not good memory: select, retrieve, and expire information deliberately.<br><!-- End of picture text -->



28 

**PART 3** 

#### **Reasoning and Planning** 

Reasoning evaluates the current situation; planning organizes candidate steps toward the goal. 



<!-- Start of picture text -->
REASONING: WHAT SHOULD HAPPEN NEXT? PLANNING: HOW CAN THE GOAL BE REACHED?<br>Read current State 1 Check available travel dates<br>↓<br>Compare constraints 2 Compare route, time, and price<br>↓<br>Choose or rank an Action 3 Verify budget and cancellation terms<br><!-- End of picture text -->

**A plan is a working hypothesis; observations may change which planned step is appropriate.** 



29 

**PART 3** 

#### **Reflection and Evaluation** 

Evaluation checks a result; reflection uses that evidence to improve the next attempt. 



<!-- Start of picture text -->
ATTEMPT EVALUATE REVISE<br>Recommend Train A at 08:00 —_—> Check user calendar > Choose a later departure<br>Observation: unavailable before<br>10:00<br>repeat only if the goal is not met<br><!-- End of picture text -->

**Useful reflection must be grounded in a test, rule, rubric, or other observable criterion.** 



30 

**PART 3** 

#### **Environment and Observation** 

The environment is what the agent can read or change; observations report what actually happened. 



<!-- Start of picture text -->
ENVIRONMENT<br>e> search_trains(SIN, KL, after 10:00)ACTION ——><br>Travel search service<br>AGENT<br>chooses an Action User calendar<br>updates State<br>— OBSERVATION -——_ Booking policy<br>Train B 11:00; seats available; SGD 120<br><!-- End of picture text -->

**An agent should report the observation it received—not invent a successful outcome.** 



31 

**PART 3** 

#### **Harness and Runtime — Real System Examples** 

A harness turns model outputs into a controlled loop with tools, permissions, state, and logs. 



**CLAUDE CODE** Coding agent with repository and terminal actions 

<u>Official product/project page</u> 



**CODEX** 

Open-source coding agent and execution loop 

<u>Official product/project page</u> 



**OPENCLAW** Self-hosted agent runtime and integrations 

<u>Official product/project page</u> 



32 

**PART 3** 

#### **Worked Example: A Coding Agent Fixes a Test** 

Map every component to one realistic, bounded software-engineering task. 

|**COMPONENT**|**CONCRETE ROLE IN THE EXAMPLE**|
|---|---|
|**Goal**|Make the checkout calculation correct without breaking related tests; stop only after verification.|
|**State / Context**|Issue description, files inspected, current patch, test results, and remaining constraints.|
|**Model / Policy**|Choose whether to inspect code, edit a file, run a test, or ask the user.|
|**Tools / Actions**|Read and edit the relevant repository files; run the named tests.|
|**Environment / Observation**|Repository and test runner return file contents, pass/fail status, and logs.|
|**Reflection / Evaluation**|Compare test output with the goal and diagnose the remaining failure.|
|**Harness / Runtime**|Maintain the loop, sandbox commands, enforce approvals, limits, and logging.|
|**This is a teaching tr**|**ace of a real coding-agent task pattern—not a claim of guaranteed autonomous success.**|





33 

**PART 3** 

#### **Worked Trace: Components in Motion** 

Each row shows which component is active and what new observation changes the next decision. 

|**#**|**ACTIVE COMPONENT**|**TRACE**|
|---|---|---|
|**1**|**Goal + State**|The checkout test fails; success requires this and all related tests to pass.|
|**2**|**Model / Policy**|Choose to inspect the failing assertion and coupon calculation.|
|**3**|**Tool / Action**|Read the test and edit the checkout calculation.|
|**4**|**Environment / Observation**|Target test passes, but another discount edge-case test now fails.|
|**5**|**Evaluation + State**|Goal is not met; record the regression and identify the missing boundary.|
|**6**|**Model + Tool**|Revise the condition and run the full relevant test set.|
|**7**|**Observation + Stop**|All relevant tests pass; present the diff and request human review.|



**The first passing test is not enough: evaluation catches a regression before the agent stops.** 



**PART 3** 34 

#### **Discussion: Match Components and Roles** 

Using the component definitions from this Part, match each numbered component with its primary responsibility. **CLASS EXERCISE  |  6 MIN** 

**NUMBERED COMPONENTS LETTERED RESPONSIBILITIES** 1  Goal A  Keeps task-relevant information available 2  Model / Policy B  Runs the loop and enforces limits 3  Tools / Actions C  Defines the result and stop condition 4  Memory / Context D  Returns what happened after an action 5  Environment / Observations E  Chooses the next action from current state 6  Reflection / Evaluation F  Checks results against criteria 7  Harness / Runtime G  Performs work through a bounded interface **Write seven pairs:  1–__   2–__   3–__   4–__   5–__   6–__   7–__** 



<!-- Start of picture text -->
fo] NANYANG TECHNOLOGICAL UNIVERSITY SINGAPORE<br><!-- End of picture text -->

**PART 3** 35 

#### **Discussion: Answer** 

Using the component definitions from this Part, match each numbered component with its primary responsibility. 

###### **ANSWER** 

**NUMBERED COMPONENTS LETTERED RESPONSIBILITIES** 1  Goal A  Keeps task-relevant information available 2  Model / Policy B  Runs the loop and enforces limits 3  Tools / Actions C  Defines the result and stop condition 4  Memory / Context D  Returns what happened after an action 5  Environment / Observations E  Chooses the next action from current state 6  Reflection / Evaluation F  Checks results against criteria 7  Harness / Runtime G  Performs work through a bounded interface **Completed pairs:  1–C   2–E   3–G   4–A   5–D   6–F   7–B** 



<!-- Start of picture text -->
fo] NANYANG TECHNOLOGICAL UNIVERSITY SINGAPORE<br><!-- End of picture text -->

**PART 3** 36 

###### **Part 4** 

**Reasoning and Planning in Agents** 

- Chain-of-Thought and self-consistency 

- Tree of Thoughts and task decomposition 

- Reflection and dynamic replanning 

Spend computation where a task benefits from deliberation 



#### **Direct Answer or Deliberate Reasoning?** 

Use the lightest strategy that is adequate for the task and its consequences. 



<!-- Start of picture text -->
DIRECT ANSWER DELIBERATE REASONING<br>Prompt Task<br>Choose a venue for 80 students within $200 before<br>Translate “Good morning” into Chinese.<br>18:00.<br>Response<br>check<br>check budget check time<br>早上好。 capacity<br>Several constraints create useful intermediate checks.<br>One familiar transformation; low need for search.<br><!-- End of picture text -->

**Extra reasoning is useful when it exposes constraints or evidence—not simply because a task sounds difficult.** 



38 

**PART 4** 

#### **Chain-of-Thought Prompting** 

The original paper contrasts a direct answer with a worked chain of intermediate steps. 

###### **HOW TO READ FIGURE 1** 



<!-- Start of picture text -->
Standard Prompting Chain-of-Thought Prompting<br>Woden) S\Ci)<br>Q: Roger has 5 tennis balls. He buys 2 more cans of Q: Roger has 5 tennis balls. He buys 2 more cans of<br>tennis balls. Each can has 3 tennis balls. How many tennis balls. Each can has 3 tennis balls. How many<br>tennis balls does he have now? tennis balls does he have now?<br>A: The answer is 11. A: Roger started with 5 balls. 2 cans of 3 tennis balls<br>ach is 6 tennis balls. 5 + 6 = 11. The answer is 11<br>Q: The cafeteria had 23 apples. If they used 20 to<br>make lunch and bought 6 more, how many apples Q: The cafeteria had 23 apples. If they used 20 to<br>do they have? make lunch and bought 6 more, how many apples<br>_ Nedo they have? S ]<br>Weds Motto ~<br>( A:So The answer is 27. $€ \| & The<br>{answers 9. v<br><!-- End of picture text -->

- Standard prompting gives an 

- **1** answer with no worked intermediate relation. 

- CoT prompting includes a 

- **2** demonstration with a naturallanguage reasoning chain. 

- The model then generates 

- **3** intermediate steps before its final answer. 

<u>Open the original paper</u> 



Wei et al., “Chain-of-Thought Prompting Elicits Reasoning in Large Language Models,” NeurIPS 2022, Fig. 1. 

39 

**PART 4** 

#### **Self-Consistency** 

Sample several reasoning paths, then aggregate the most consistent final answer. 



<!-- Start of picture text -->
Greedy decode<br>_<br>Chain-of-thought if (This means she uses 3+ 4=7eggsevery day.<br>prompting {Prompt } |_| ~| Language“model || totalShe sells she sells the remainder 7 * $2 = $14 for per $2 day. per egg, so in ~| The answer is $14.<br>\ _) The answer is $14. be 2<br>si-consisten aiiaaliad Samplea aa diversese setset of Marginalize9 out reasoningg paths<br>reasoning paths ©, to aggregate final answers<br>(/_lot@:1f and thereare 3 cars in the parking ~ aeShe has 16-3-4=9eggsed| = 11<br>‘cars are2 morein the carsparking arrive,lot? how many /|// $18left. Soper sheday. makes $2*9= |1 The answeris $18. )\\ -<br>‘A: There are 3 cars in the parking lot |  (SSSa) | \<br>already.nd eee2 moreThe arrive.eonmeNow there are (> | | / Giencaefomainderfor oceans $2 (16-43),4 The answer \ \<br>G: Janets ducts lay 6 eggs per day. )\[ Language |// (= $26 pet day is $26.)\N Vv<br>She eats three for breakfast every oda le /<br>friendsmorning everyand  daybakes withmuffins four.Shefor her sells. | \___/ \!\ ((Sheghe haseats 163 -for 3=breakfast, 13 left. Thenso | / /<br>the remainder for $2 per egg. How she bakes muffins, so she | The answer is $18.<br>much does she make every day? has 13 - 4= 9 eggs left. So<br>\ a yA she has 9 eggs * $2= $18. | y<br><!-- End of picture text -->

###### **THREE OPERATIONS** 



<!-- Start of picture text -->
Generate multiple<br>SAMPLE diverse reasoning<br>paths.<br>Read the final answer<br>COMPARE produced by each<br>path.<br>Select the answer with<br>AGGREGATE the strongest<br>agreement.<br><!-- End of picture text -->



<!-- Start of picture text -->
Open the original paper<br><!-- End of picture text -->



<!-- Start of picture text -->
fo] NANYANG TECHNOLOGICAL UNIVERSITY SINGAPORE<br><!-- End of picture text -->

Wang et al., “Self-Consistency Improves Chain of Thought Reasoning in Language Models,” ICLR 2023, Fig. 1. 

40 

**PART 4** 

#### **Tree of Thoughts** 

ToT searches over candidate intermediate states instead of following only the first linear chain. 



<!-- Start of picture text -->
( Sin \ ( ra ) ( Pi ce Li<br>C , ' . ) 1<br>Input J Se Input D ‘ Input D) p C Input: y) _ thought |<br>Lo t Ss 1<br>| Oooo: |<br>||i'<br>T<br>|;<br>@e@©®é £ |:i:<br>jo | YWjrtyvore | __<br>y»7 y\<br>CaaaOutput Outputmaa ») CuaeOutput) i (Output)ects<br>(a) Input-Output (c) Chain of Thought —_(c) Self Consistency<br>Prompting(10) Prompting (CoI) with CoT (CoT-SC (d) Tree of Thoughts(ToT)<br><!-- End of picture text -->

###### **WHAT CHANGES FROM CoT?** 



<!-- Start of picture text -->
Generate several<br>Branch<br>candidate thoughts.<br><!-- End of picture text -->

Estimate which partial **Evaluate** states are promising. <mark>L]</mark> 

Keep, prune, or **Search** backtrack across branches. 

Yao et al., “Tree of Thoughts: Deliberate Problem Solving with Large Language Models,” NeurIPS 2023, Fig. 1. 



<!-- Start of picture text -->
Open the original paper<br><!-- End of picture text -->

**PART 4** 



41 

#### **Task Decomposition** 

Break a broad goal into observable subgoals with explicit completion checks. 



<!-- Start of picture text -->
GOAL  ·  Fix checkout behavior without breaking other tests<br><!-- End of picture text -->



<!-- Start of picture text -->
1 2 3 4<br>REPRODUCE LOCALIZE CHANGE VERIFY<br>Run the failing test Inspect assertion and  Edit the smallest  Run target and related<br>relevant code relevant condition tests<br>Check: failure is observed Check: likely cause is  Check: diff matches the  Check: no observed<br>identified hypothesis regression<br><!-- End of picture text -->

**A useful subgoal ends in an observation that tells the agent whether to continue.** 



42 

**PART 4** 

#### **Reflection: Self-Refine and Reflexion** 

Both iterate with feedback, but they store and use that feedback differently. 

###### **SELF-REFINE** 

###### **REFLEXION** 



<!-- Start of picture text -->
Feedback .<br>Sd) Refine<br>Model M<br>o g<br>Figuresame model1: Given M anto getinputfeedback(O), SELF-REFINE(). The feedbackstarts byis  generatingpassed backan output and passing it back to the<br>generated output (2). Steps to M, which refines the previously<br>instantiated with a language model(D) andsuch(@) as GPT-3.5iterate untiland doesa stopping condition not involve humanis met. assistance.SELF-REFINE is<br><!-- End of picture text -->



<!-- Start of picture text -->
Taco | ooa<br>1” |e etna amma<br>vaten | 18/0 Hoiatie alt genarsted wait tants Gil Sneed<br>‘ erg EE IRE gees barre meee naa<br>vole lamers ——J<br>Trajectory be: apeckianleis ange TREY 9F foster have in common in novelists<br>sevion<br>Figure 1: Reflexion works on decision-making1] prograrmmingl£3] and reasoning[f tasks<br><!-- End of picture text -->

Generate → feedback → refine the same output within one task. 

Evaluate a trajectory → write a reflection → use it as episodic memory in another attempt. 

<u>Madaan et al., Self-Refine (2023), Fig. 1</u> 

<u>Shinn et al., Reflexion (2023), Fig. 1</u> 



<!-- Start of picture text -->
(@ NANYANG TECHNOLOGICAL UNIVERSITY SINGAPORE<br><!-- End of picture text -->

43 

**PART 4** 

#### **Discussion: Choose a Reasoning Strategy** 

For each classroom task, choose the reasoning strategy that best matches its structure. Use each strategy once. **CLASS EXERCISE  |  5 MIN** 

**Strategies: Self-Consistency · Reflection · Direct ·  ToT · CoT** 

|**#**|**TASK**|**STRATEGY**|
|---|---|---|
|**A**|Translate one short sentence.|________________|
|**B**|Solve a multi-step arithmetic word problem with visible steps.|________________|
|**C**|Aggregate the final answers from several sampled reasoning paths.|________________|
|**D**|Explore a puzzle with branches, pruning, and backtracking.|________________|
|**E**|Revise a draft after a checker finds a missing date.|________________|





<!-- Start of picture text -->
fo] NANYANG TECHNOLOGICAL UNIVERSITY SINGAPORE<br><!-- End of picture text -->

44 

**PART 4** 

#### **Discussion: Answer** 

|For each classroom task, choose the reasoning strategy that best matches its structure. Use each strategy once.<br>**WER**|
|---|
|**Strategies: Self-Consistency · Reflection · Direct ·  ToT · CoT**|
|**#**<br>**TASK**<br>**STRATEGY**|
|**A**<br>Translate one short sentence.<br>**Direct**|
|**B**<br>Solve a multi-step arithmetic word problem with visible steps.<br>**CoT**|
|**C**<br>Aggregate the final answers from several sampled reasoning paths.<br>**Self-Consistency**|
|**D**<br>Explore a puzzle with branches, pruning, and backtracking.<br>**ToT**|
|**E**<br>Revise a draft after a checker finds a missing date.<br>**Reflection**|



**ANSWER** 



<!-- Start of picture text -->
fo] NANYANG TECHNOLOGICAL UNIVERSITY SINGAPORE<br><!-- End of picture text -->

45 

**PART 4** 

###### **Part 5** 

**How Agents Work** 

- Observe → decide → act 

- ReAct traces and dynamic state 

- Stops, budgets, approvals, and failures 

A controlled loop over state, tools, and environment feedback 



#### **The Agent Loop at Runtime** 

Earlier slides defined one cycle and its components; here we follow repeated execution over time. 



<!-- Start of picture text -->
1  OBSERVE 2  DECIDE 3  ACT 4  UPDATE<br>Read state and latest  Select the next allowed  Invoke a tool or ask the  Record result and check<br>result action user progress<br><!-- End of picture text -->



Coding-agent example: inspect a failing test → edit a file → run tests → observe a regression → revise. 

The harness repeats the loop until success, a limit, an approval gate, or an unrecoverable error. 

<u>OpenAI: Unrolling the Codex agent loop</u> 



47 

**PART 5** 

#### **ReAct: Reasoning and Acting in One Trace** 

The paper's HotpotQA example requires search observations to answer a multi-hop question. 

###### **Task background: Apart from the Apple Remote, what other device can control the program it was designed for?** 



<!-- Start of picture text -->
(a) wotopot ox (ay nant (Reason AS<br>Question: Aside from the Apple Renote, what other device | | thooght 1: 1 need to search Apple Renote and find the<br>meat3 wages ch “ GheSot 1 1: ‘Thesearchapple [ipplR e moteRemote]is a remote control introcucea in:<br>{_tae) standasa_] (Ge) Ast-onty OctoberFrontsRE2003medaTeenEeH!by Apple. 5originally03<.0 designed to control the<br>Act 1: Soarch(Appie Renote] ‘tought 2: Apple Renote was originally designed to control<br>Obs 1: The Apple Remote is a the Front Row media center program. I need to search<br>remote control — HM next and find what other device can control it.<br>(Gb) cof (Ranson Only) aot 21 secreh[Proot Row]<br>by step. NEBR! | | Cow 2: covis now tind Cerone | | iapeaerat :<br>originally designed to. Fowl. Siniiar: —<br>Anteract with Apple 1. Ye 3: Front Row is not found. 1 need to search<br>(RBBISERUNESWIBETESRELOTIEM! | | act 3: search| RESHENREM<br>by APhone, (Pad, and Ped | | (eostware) dot 3: search '<br>iphone, iPad, and iPod discontinued media center ia<br>Keyboard function keys.<br>Anaver: iPhone, iPad, iPod<br>— ig) [aot 4s. rin x det 4: Fini)a gh<br><!-- End of picture text -->



<!-- Start of picture text -->
HOW ReAct SOLVES IT<br>Identify what program<br>Thought Apple Remote<br>controlled.<br>Action +  Search Apple Remote<br>Obs. → observe Front Row.<br>Now search Front Row<br>Thought<br>for another controller.<br>Use the retrieved<br>Finish<br>evidence to answer.<br><!-- End of picture text -->

Yao et al., “ReAct: Synergizing Reasoning and Acting in Language Models,” ICLR 2023, Fig. 1 (HotpotQA excerpt). 

<u>Open the original paper</u> 



<!-- Start of picture text -->
@@$5 NANYANG TECHNOLOGICAL UNIVERSITY SINGAPORE<br><!-- End of picture text -->

48 

**PART 5** 

#### **State Update and Recovery** 

When results differ from expectations, update state before choosing a bounded recovery action. 

**OBSERVATION UPDATE STATE Test still fails Record evidence REVISE RETRY** Change the action using new Repeat only if the failure evidence may be transient 



<!-- Start of picture text -->
CHOOSE A RECOVERY PATH<br>ASK / APPROVE STOP / ESCALATE<br>Request missing information  Report the blocker when<br>or authority safe progress ends<br><!-- End of picture text -->

**Re-planning is one possible recovery behavior; accurate state update and bounded choice are the essentials.** 



49 

**PART 5** 

#### **Runtime Controls Around the Loop** 

Controls are placed before action, after observation, and before the agent declares success. 

**BEFORE ACTION AFTER OBSERVATION BEFORE FINISH** Is the action registered? Did the action fail? Is the success condition observed? Are parameters valid? Should state be updated? Are outputs verified? Is approval required? Has a retry limit been reached? Is the status report honest? 

**These gates turn permissions, observations, evaluation, and stop conditions into runtime rules.** 



50 

**PART 5** 

#### **Discussion: Put the Agent Loop in Order** 



<!-- Start of picture text -->
A coding agent is repairing an incorrect checkout calculation. Order the events from reproducing the failure to a verified stop.<br>CLASS EXERCISE  |  6 MIN<br>Goal: make the checkout test pass without breaking the related tests.<br>A Edit the coupon calculation B Observe all relevant tests pass<br>C Run the failing checkout test D Observe the assertion failure<br>E Inspect the relevant test and code F Run the target and related tests<br>G Present the verified diff for review H Stop the task<br>Order: ____ → ____ → ____ → ____ → ____ → ____ → ____ → ____<br>Success condition: ________________________________________________<br><!-- End of picture text -->



<!-- Start of picture text -->
fo] NANYANG TECHNOLOGICAL UNIVERSITY SINGAPORE<br><!-- End of picture text -->

51 

**PART 5** 

#### **Discussion: Answer** 



<!-- Start of picture text -->
A coding agent is repairing an incorrect checkout calculation. Order the events from reproducing the failure to a verified stop.<br>ANSWER<br>Goal: make the checkout test pass without breaking the related tests.<br>A Edit the coupon calculation B Observe all relevant tests pass<br>C Run the failing checkout test D Observe the assertion failure<br>E Inspect the relevant test and code F Run the target and related tests<br>G Present the verified diff for review H Stop the task<br><!-- End of picture text -->

**Order: C → D → E → A → F → B → G → H** 

**Success condition: target and related tests are observed to pass; the verified diff is ready for review.** 



<!-- Start of picture text -->
fo] NANYANG TECHNOLOGICAL UNIVERSITY SINGAPORE<br><!-- End of picture text -->

52 

**PART 5** 

#### **Discussion: Find the Runtime Violations** 

A coding agent has reached its retry limit. Identify every policy violation, then write a safe next action and an honest status. **CLASS EXERCISE  |  6 MIN** 



<!-- Start of picture text -->
RUNTIME POLICY TRACE<br>•  Only registered read / edit / test actions 1. Run target test → still fails<br>•  Maximum two test attempts before stopping 2. Run target test → still fails<br>•  Approval before installing a dependency 3. Run target test a third time<br>•  Success requires all relevant tests to pass 4. Install a new package without approval<br>5. Report “fixed” without running related tests<br><!-- End of picture text -->

Safe next action: __________________________________________________________ Honest status message: ____________________________________________________ 



<!-- Start of picture text -->
fo] NANYANG TECHNOLOGICAL UNIVERSITY SINGAPORE<br><!-- End of picture text -->

53 

**PART 5** 

#### **Discussion: Answer** 

A coding agent has reached its retry limit. Identify every policy violation, then write a safe next action and an honest status. **ANSWER** 



<!-- Start of picture text -->
RUNTIME POLICY TRACE<br>•  Only registered read / edit / test actions 1. Run target test → still fails<br>•  Maximum two test attempts before stopping 2. Run target test → still fails<br>•  Approval before installing a dependency 3. Run target test a third time   ✗ VIOLATION<br>•  Success requires all relevant tests to pass 4. Install a new package without approval   ✗ VIOLATION<br>5. Report “fixed” without running related tests   ✗ VIOLATION<br>Safe next action: stop after the retry limit; preserve the failure log and ask for review or approval of a new approach.<br>Honest status: not fixed; the target still fails and the related tests have not been verified.<br><!-- End of picture text -->



<!-- Start of picture text -->
fo] NANYANG TECHNOLOGICAL UNIVERSITY SINGAPORE<br><!-- End of picture text -->

54 

**PART 5** 



<!-- Start of picture text -->
aoe<br>Wee7<br>sos<br><!-- End of picture text -->

# Thanks 

##### Q&A 



55 

