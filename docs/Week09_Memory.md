**Memory and Context Management** Week 9 · Agentic AI 

Prof Bo AN https://personal.ntu.edu.sg/boan/ _Email_ : boan@ntu.edu.sg _Office_ : S3-B2C-83 



### **Roadmap** 

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

### **Lecture Outline** 

|1|**Defining Agent Memory**|What memory means for a model, and what fails without it|
|---|---|---|
|2|**Assembling the Model's Context**|A finite context budget, with input selected as needed from five common<br>sources for each model call.|
|3|**Classifying Agent Memory**|Four kinds of memory, and where each one lives|
|4|**Building Long-Term Memory**|Writing, retrieving and maintaining what survives the session|
|5|**Managing Working Memory**|Deciding what each individual step is allowed to see|
|6|**Evaluation and Safety**|Measuring the benefit and risks of memory|





#### **Part 1** 

## **Defining Agent Memory** 

What memory means for a stateless model, and what fails without it 



### Defining Agent Memory **—An Early Instruction Is Silently Dropped** 

**An instruction given early stops being obeyed once it falls outside the request.** No error is raised, and the reply remains fluent and confident. 

###### **More than ten words.** 



<!-- Start of picture text -->
USER · TURN 2 ASSISTANT · TURN 20<br>Keep every reply under  ten words. Great question. Before deploying you will want to review the environment<br>configuration, plan the migration, and run the full test suite.<br>THE REQUEST SENT AT TURN 20<br>turn 1 turn 5 turn 10 turn 15 turn 20<br><!-- End of picture text -->

**The Turn 2 instruction is missing from the input sent at Turn 20.** The model is not disregarding the instruction; it is no longer receiving it, and nothing in the reply marks the omission. 

**THE POINT** The failure is silent. Nothing in the output distinguishes a constraint that was weighed and rejected from one that was never transmitted, which is what makes this class of fault difficult to detect in production. 



### Defining Agent Memory **—How Earlier Turns Reach the Model** 

**Earlier conversation turns reach the model through the input prepared for each call.** The surrounding system maintains conversation state and selects what to include. 

**EXAMPLE · INCLUDING THE FULL CONVERSATION HISTORY** 

**Call 3 sys + t1 t2 t3 tools sys + Call 20 t20 tools** 

turns 1–19 included again in this example 

###### **In this example:** 

###### **input at turn n = system prompt + tool schemas + turns 1 … n** 

**CONSEQUENCE** The system decides which earlier information enters the next call. It can include the full history, select relevant turns, or use summaries and retrieved records. 



### Defining Agent Memory **—Two Failure Modes: Forgetting and Overflow** 

**Two fundamental capacity-related failure modes considered in this lecture.** Either something needed is no longer present, or something present no longer fits. 

###### **FORGETTING** 

###### **OVERFLOWING** 

turn 2 the request at turn 20 

the request at turn 20 **+52k** 

What the task still needs is no longer in the request, and nothing signals its absence. 

One step returns more than the request can hold, so the run stalls or the harness truncates it. 

**↓** 

**↓** 

**Part 4  ·  Building Long-Term Memory** 

**Part 5  ·  Managing Working Memory** 



### Defining Agent Memory **—An Analogy: A Workspace and Reference Materials** 

**A workspace holds information used in the current decision.** 

Information from stored records can be brought into the workspace when needed. 



<!-- Start of picture text -->
look back<br>An activity log    records of past events and actions<br>The active workspace look up<br>A fact sheet    facts and knowledge that can be updated<br>information used in the current decision<br>consult<br>A procedure guide    reusable instructions for how to act<br>information in use records kept for later use<br>THE MAPPING The workspace illustrates working memory. The activity log, fact sheet and procedure guide illustrate episodic, semantic and<br>procedural memory.<br><!-- End of picture text -->

Teaching analogy informed by CoALA’s memory framework (Sumers et al., 2023). 



### Defining Agent Memory **—A Definition of Agent Memory** 

**Scope and definition:** This lecture focuses on memory mechanisms outside fixed model weights. Working memory holds information active in the current decision; long-term memory retains records for retrieval and reuse. 

###### **Around the model** 

The surrounding system maintains working state and stored records. 

###### **WITHOUT STATE MANAGEMENT** 

The agent may lose track of its current goal, progress and unfinished work. 

###### **Deciding what enters** 

The system selects information from working memory to build an input that fits the model’s context window. 

###### **CONTEXT RISKS** 

An input may omit needed information or exceed the context limit. 

###### **Deciding what persists** 

The agent saves information worth keeping in long-term memory for later retrieval and reuse. 

###### **WITHOUT RETENTION** 

Useful information may be lost when the current conversation is discarded. 

Sumers et al. (2023), CoALA · Wu et al. (2025), From Human Memory to AI Memory 



#### **Part 2** 

## **Assembling the Model's Context** 

A finite context budget, with input selected as needed from five common sources for each model call. 





<!-- Start of picture text -->
Assembling the Model's Context<br>—Definition of the Context Window<br>The context window is the token budget available to a single model call.<br>Each call uses input assembled by the surrounding system within this token budget.<br>ONE CALL'S BUDGET IN TOKENS, DRAWN TO SCALE 1 token ≈ 0.75 English words ≈ 4 characters<br>a 40-page report  ≈ 27,000<br>a 300-page book  ≈ 100,000<br>one call's budget  =  1,000,000 tokens<br>0 250,000 500,000 750,000<br>1 · the request is assembled 2 · one model call 3 · the call completes<br>Working state can persist across calls. The system selects information from that state to prepare each input.<br>TERMINOLOGY Capacity is stated in tokens rather than words or characters because tokenisation (Week 2) is what the model consumes. The same<br>text costs different numbers of tokens under different tokenisers.<br><!-- End of picture text -->

### Assembling the Model's Context **—Five Common Sources of Model Input** 

**The surrounding system selects and assembles information for each model call.** 

**COMMON INPUT SOURCES System prompt** the agent’s role and instructions for the task **Tool schemas** available tools, their descriptions and argument formats **Conversation messages** the current request and selected earlier messages **Tool results** tool outputs, included in full, as selected excerpts, or as summaries **Retrieved information** relevant information retrieved from documents or memory stores 

**IMPLICATION** The system chooses which sources to use and how much information to include, based on the task and the context budget. 

Anthropic (2025), Effective context engineering for AI agents. 



### Assembling the Model's Context **—The Limits of Larger Windows** 



<!-- Start of picture text -->
Capacity grew roughly 240-fold between 2023 and 2026, from about 4,096 to 1,000,000 tokens.<br>THE SAME 1,000,000-TOKEN WINDOW AT FOUR POINTS IN ONE RUN<br>after setup 25,000 tokens  ·  2.5%<br>after five turns 100,000 tokens  ·  10.0%<br>after a directory is read in 375,000 tokens  ·  37.5%<br>after retrieval 600,000 tokens  ·  60.0%<br>system + tools dialogue files read in retrieved documents<br><!-- End of picture text -->



Window sizes: GPT-3.5-turbo (2023) 4,096 → Claude Opus 5 / Sonnet 5 (2026) 1,000,000, from published model cards, checked 2026-08. Figure token counts are illustrative. 

### Assembling the Model's Context **—The Costs of Longer Input** 

**Longer input can increase cost and latency, but does not guarantee better answers.** Even within the context limit, a model may fail to use relevant information reliably. 

**INPUT COST** 

**LATENCY** 

**ACCURACY** 

More input tokens generally mean a higher input charge at the same token rate. Reusing cached input can reduce this charge. Processing more uncached input can delay the start of a response. The effect depends on the model and serving system. The model may miss relevant information in a long input, especially when it appears in the middle. The effect varies by model and task. 

**IMPLICATION** Keep the information needed for the task and stay within the context limit. Liu et al. (2023), Lost in the Middle · Hsieh et al. (2024), RULER · Anthropic, Prompt caching. 



Assembling the Model's Context **—Working Memory: Definition and Scope** 

**Working memory holds information active in the current decision.** 

The system selects information from working memory to build the input for each model call. Each input must fit within the model's context window. 

**Something the agent holds in the window now Should it be retained for later retrieval and reuse? Is it too large for this turn?** Save it as a record in long-term memory. Reduce what the window has to hold. **Parts 3 and 4  ·  classifying and building memory Part 5  ·  managing working memory** 

The term is taken from Baddeley & Hitch (1974); its application to language-model context follows Sumers et al. (2023). 



#### **Part 3** 

**Classifying Agent Memory** 

Four kinds, and where each one lives 



### Classifying Agent Memory **—A Taxonomy of Agent Memory** 

###### **Working memory** 

Information active in the current decision Maintained and updated by the runtime Selected information forms each model input 

###### **Long-term memory** 

**RETAINED FOR LATER RETRIEVAL AND REUSE** 

**Episodic** past experiences 

**Semantic** facts & prefs 

**Procedural** 

how to act 

###### **WORKING** 

Holds information active in the current decision, such as goals, observations and intermediate results. 

**EPISODIC** Records of past experiences, such as what the agent observed, what it did and what happened as a result. 

**SEMANTIC** A claim held to be true at present. Its current value can be updated while retaining earlier versions for audit. 

**PROCEDURAL** Knowledge of how to act, including reusable instructions and procedures. It can be provided in advance or learned and revised through experience. 

Sumers et al. (2023), CoALA · Wu et al. (2025), From Human Memory to AI Memory 



### Classifying Agent Memory **—Retrieval and Write-back** 

**THREE PERSISTENT STORES THE TWO ARROWS CURRENT DECISION Episodic retrieve Working memory** retrieve information needed for this information active in the current decision **Semantic** decision **write-back** The system selects information from working **Procedural** keep what is worth keeping memory to build the input for each model call. **PART 4 BUILDS AND SEARCHES THESE PART 5 MANAGES THIS** 

**Q   A record the agent just retrieved is now sitting in the context window. Is it part of working memory?** 

**A** Yes. The retrieved information is part of working memory for the current decision. The original record remains in long-term memory. 

Sumers et al. (2023), CoALA §4.1 · Park et al. (2023), Generative Agents 



### Classifying Agent Memory **—Working Memory: An Example** 

**Working memory holds information active in the current decision.** 

The system selects information from working memory to build the input for each model call. 

**the input for this model call** 

**system** You are a coding agent for this repo. Tools: bash, read_file, edit_file. 

**user** The test suite is failing. Please make it pass. 

**assistant** Let me run it first.   bash: pytest -q 

**tool** 12 tests collected, 1 error — ImportError: No module named 'numpy' at tests/test_api.py:3 

**assistant** numpy is imported by the tests but never installed here. Checking requirements-dev.txt. 

**Here, the input includes the task, tool results and intermediate reasoning.** 

###### **1 RE-SENT IN FULL** 

In this example, the runtime resends the full conversation history on each model call. 

###### **2 GROWS IN THIS EXAMPLE** 

In this example, each new turn adds to the input. Filtering, summarisation or structured state can reduce its length. 

###### **3 RETENTION DEPENDS ON THE SYSTEM** 

Whether the conversation is retained after the session ends depends on the system. 



### Classifying Agent Memory **—Episodic Memory: A Single Episode** 

**Episodic memory stores experiences from earlier decision cycles.** 

This example records what happened, when it happened and the outcome. 

**memory/episodes/2026-06-03.md** 

On 3 June the test suite failed. pytest -q collected 12 tests and stopped on one error: ImportError: No module named 'numpy', at tests/test_api.py line 3. 

numpy was not in requirements.txt — it is declared in requirements-dev.txt, which had never been installed in this environment. 

Running pip install -r requirements-dev.txt fixed it and all 12 tests passed. Four minutes, six steps, no code changed. 

###### **WRITTEN** 

###### **1** 

Written after the run, once the outcome was known. The agent wrote it in its own words; it was not edited. 

###### **2 RETRIEVED** 

Weeks later the same ImportError appears; the store is searched by that error string and this note is returned. 

###### **3 REUSED** 

The agent uses this past run to decide what to check next, then records the new run as a separate episode. 



### Classifying Agent Memory 

##### **—Semantic Memory: A Single Fact** 

**Semantic memory stores facts and knowledge about the world and the agent itself.** 

Here, the project's Python version is stored as a fact, with its source and update history. 

###### **memory/facts/python-version.md** 

The project pins Python to **3.11** . It is set in pyproject.toml and in the CI image, and the team has said it will not move this quarter. Source: user statement, 2026-03-04. 

###### **1 WRITTEN** 

The agent stores the fact with its source and date. The original statement can also be retained. 

###### **2 UPDATED WITH HISTORY** 

When the version changes to 3.12, mark it as current and retain 3.11 as superseded history. 

**2026-07-15  ·  the user says “we're on 3.12 now”** 

The project pins Python to **3.12** (current). 

Python 3.11 is retained as superseded history for audit. 

###### **3 INJECTED** 

A few facts can be added directly to the input; larger stores can be searched for relevant facts. Use the current version when the task requires the current configuration. 



### Classifying Agent Memory **—Procedural Memory: A Single Procedure** 

**Procedural memory stores reusable knowledge of how to act.** 

Procedures can be provided in advance or learned and revised through experience. 

**skills/debug-failing-test.md** 

name: debug-failing-test description: Use when a test suite fails. --- 

1. Copy the exact error string, verbatim. 

2. Locate the file and line it points to. 

3. Build the smallest script that repros it. 

4. Fix, then run the whole suite, not that test. 

5. Write the episode: cause, fix, outcome. Never skip 3: an unreproduced fix is a guess. 

###### **1 EXPLICITLY AUTHORED** 

Written and committed as an explicit artifact, whether by a developer under code review or by the agent itself, and changed only by editing that artifact. 

###### **2 LOADED BY DESCRIPTION** 

In this example, the runtime selects the procedure using its description and includes its instructions in the model input. 

###### **3 FOLLOWED** 

In the 3 June example, the agent follows this procedure and records the outcome in memory/episodes/2026-06-03.md. 

Here, the skill file serves as explicit procedural memory by specifying how the agent should act. 



### Classifying Agent Memory **—Comparison of the Four Kinds of Memory** 

|**Kind**|**What it holds**|**Example**|**Storage in this example**|**Maintenance in this**<br>**example**|
|---|---|---|---|---|
|**Working**|Information active in the current<br>decision|The pytest output used for<br>this decision|Variables maintained by the<br>runtime|Updated for the current<br>decision|
|**Episodic**|Past experiences|The 06-03 ImportError run|Files|Retained for later retrieval|
|**Semantic**|Facts and knowledge|python = 3.12 (current)|Files|Current value updated;<br>history retained|
|**Procedural**|Instructions and procedures|debug-failing-test.md|Files|Revised when the<br>procedure changes|





### Classifying Agent Memory **—Discussion 1 · Memory Type and Current Use** 



<!-- Start of picture text -->
Item Situation Long-term type? Working memory now?<br>CLAUDE.md records Python 3.12 as the current project version and retains 3.11 as history. The<br>A ? ?<br>current fact has been loaded and is being used in this decision.<br>pytest -q has just returned “ImportError: No module named 'numpy'”. The agent is using<br>B ? ?<br>this output to investigate the failure. This output has not been saved to long-term memory.<br>A reusable debugging prompt template in skills/debug.md specifies: capture the error, locate its<br>C source, reproduce, fix and rerun tests. It remains in the skill library and is not active in the current  ? ?<br>decision.<br>A saved record describes the 3 June ImportError: installing requirements-dev.txt resolved it<br>D ? ?<br>in four minutes. The agent retrieved the record and is using it to investigate the current failure.<br><!-- End of picture text -->

For each item, identify its long-term memory type, if a record has been saved. Then decide whether its content is part of working memory for the current decision. 



### Classifying Agent Memory **—Discussion 1 · Answers** 

|**Item**|**Long-term type**|**Working memory now?**|**Reason**|
|---|---|---|---|
|**A**|**Semantic**|**Yes**|A project fact, loaded for the current decision.|
|**B**|**No long-term record yet**|**Yes**|A new observation used now; no long-term record has been saved.|
|**C**|**Procedural**|**No**|A stored debugging prompt template, not active in this decision.|
|**D**|**Episodic**|**Yes**|A past experience, retrieved for the current decision.|





#### **Part 4** 

**Building LongTerm Memory** 

Writing, retrieving and maintaining what survives the session 



Building Long-Term Memory **—The Four Stages of the Memory Loop** 

**This lecture uses four stages to organize long-term memory design: Write, Store, Retrieve, and Update / Forget.** 

**ONE MEMORY, FOUR STAGES Write Store Retrieve Update / Forget** decide what is worth keeping where it lives, and in what shape find it again when it matters resolve, deduplicate, expire The arrows show relationships between activities; each activity is triggered as needed. 

**BEYOND STORAGE** A database specifies where a record is stored, but not which records deserve to exist, when to retrieve them, or when to remove them, and those are the three decisions that make a memory system work. 

Four-stage organization for this lecture; memory, retrieval and learning concepts: CoALA (Sumers et al., 2023). 



### Building Long-Term Memory **—Write: Selection Criteria** 

**In this example, the write gate selects facts and preferences to save in long-term memory.** 



<!-- Start of picture text -->
a candidate fact or preference SAVED AS ONE RECORD<br>memory/facts/report-language.md<br>yes<br>1 · POLICY    prohibited by the storage policy?<br>Reports and code comments are written in<br>no English.<br>no NOT WRITTEN The user asked for this on 2026-03-04 and has not<br>2 · REUSE    will any later step need it? not saved to long-<br>revised it since.<br>term memory<br>yes<br>no<br>3 · STABILITY    likely to remain valid beyond this session? one claim per record<br>yes<br>written<br>WRITTEN — stored as one record<br>Check credential labels such as password and api_key, as well as value patterns.<br>{"key":"api_key","value":"dummy-value"} → DO NOT WRITE<br><!-- End of picture text -->





<!-- Start of picture text -->
Building Long-Term Memory<br>—Write Timing: Hot Path or Background<br>Write timing affects response latency and when facts become available in long-term memory.<br>WHERE THE WRITE SITS IN ONE TURN illustrative timings for one exchange<br>Hot path model call write<br>the user waits for the write<br>Background model call background write off the user's path<br>the user is served here<br><!-- End of picture text -->

**THE TRADEOFF** Hot-path writes run within the main request-processing flow, typically before the response is returned, and can add response latency. Background writes run as separate tasks during or after the conversation. The current response does not wait for them, but they still consume resources. A trigger starts the background write; the record becomes available only after the write completes successfully. 



### Building Long-Term Memory **—Retrieve: Candidate Ranking** 

**In this example, retrieval combines several signals to rank candidates and return the top k.** Retrieval methods may use a single signal or combine several. 



<!-- Start of picture text -->
the current step<br><!-- End of picture text -->



<!-- Start of picture text -->
Keyword   · exact terms and identifiers<br>Semantic similarity   · meaning rather than<br>weighted top k<br>wording<br>sum into the window<br>Recency   · time since last retrieval<br>Importance   · a weight assigned at write time<br><!-- End of picture text -->

**WHY SEVERAL** 

Recency alone can overlook useful memories that have not been retrieved recently. Semantic similarity alone may return related memories that are outdated, unimportant, or unsuitable for the current task. The signals capture different aspects of usefulness; their weights depend on the task. 

The chart here is our own illustration of multi-signal ranking, not any system's actual implementation. 



Building Long-Term Memory **—Retrieval Scoring: A Worked Example** 

**Generative Agents combines three normalised signals in a weighted sum.** 

The paper’s implementation and this example use a weight of 1 for each signal. 

**score  =  recency  +  importance  +  relevance** each term normalised to [0, 1] 

|**Candidate memory**|**recency**|**importance**|**relevance**|**score**|
|---|---|---|---|---|
|the user prefers short answers|0.31|0.85|0.72|**1.88**|
|yesterday: a CI timeout was fixed|0.94|0.30|0.15|1.39|
|the repository pins Python 3.12|0.12|0.90|0.88|**1.90**|



**With k = 2, the first and third rows are returned.** The second row has the highest recency score but the lowest total score. 

**EACH TERM** Recency favours recently retrieved memories, importance favours salient memories, and relevance favours memories related to the current query. Omitting a signal can change the ranking, but does not necessarily change the top k. 

Park et al. (2023), Generative Agents. The scores in the table are illustrative. 



Building Long-Term Memory **—Update and Forget: Store Maintenance** 

**Contradictions, duplicates and outdated records can reduce retrieval quality.** 

These four operations help keep the store useful. 

###### **Resolve** 

Confirmed updates become current. _Earlier values remain as superseded history._ 

**Deduplicate** the same fact, recorded twice _or duplicates crowd the top k_ 

**Expire** Mark records as expired when their validity ends. _Avoid using them as current information._ 

**Consolidate** Infer a claim from episodes and save it as semantic memory. 

**CONSOLIDATION: FROM EPISODES TO AN INFERRED CLAIM** 

2026-05-02  ·  the user rejected an auto-commit 2026-06-11  ·  the user rejected an auto-commit 2026-07-03  ·  the user rejected an auto-commit three episodes 

The user may prefer to avoid automatic commits. 

one inferred semantic claim 

Rasmussen et al. (2025), Zep; Sumers et al. (2023), CoALA §4.5. 



Building Long-Term Memory **—Mem0: Extraction and Update** 

**Mem0 processes each new message pair through two phases: extraction and update.** An LLM compares candidate facts with similar stored memories and selects memory operations. **TWO PHASES, FOUR POSSIBLE UPDATE OPERATIONS** 

Extract candidate facts Retrieve and compare memories 



<!-- Start of picture text -->
ADD<br>UPDATE<br>resulting memory store<br>DELETE<br>NOOP<br><!-- End of picture text -->

The update phase uses existing memories to decide what to add, revise, remove, or leave unchanged. 

Chhikara et al. (2025), Mem0. 



### Building Long-Term Memory **—The Landscape: Five Approaches to Memory** 

**Five approaches illustrate different choices for long-term memory.** 

We compare design choices for writing, storage, retrieval, and maintenance. 

|**Approach**|**What it is**|**Design emphasis**|
|---|---|---|
|**ChatGPT memory**|retains useful preferences and context across chats|personalization across chats|
|**Claude Code — CLAUDE.md**|Markdown instructions at user, project, or org scope; edited by<br>users or agents|explicit, editable instructions|
|**Letta / MemGPT**|core memory in context; archival and conversation memory<br>searched on demand|context management inspired by<br>operating systems|
|**Mem0**|a memory layer with extraction and update phases|memory management as a separate layer|
|**Zep / Graphiti**|a temporal knowledge graph over the records|relationships, temporal validity, and<br>hybrid retrieval|



Packer et al. (2023), MemGPT · Rasmussen et al. (2025), Zep · Chhikara et al. (2025), Mem0. 



### Building Long-Term Memory **—Discussion 2 · What Should the Gate Keep?** 

The agent is selecting facts and preferences for long-term memory. The store currently records PyTorch as the project's framework. Credentials must not be stored. 

For each item, choose KEEP (save or update a long-term record) or DROP (do not write it). 

||**What the session produced**|**Your call**|
|---|---|---|
|**1**|The user confirms: “The project now uses JAX instead of PyTorch.”|KEEP / DROP|
|**2**|“The final report is due on 2026-09-14.” Mentioned once; the deadline has not passed.|KEEP / DROP|
|**3**|The user closes the session with “Thanks.”|KEEP / DROP|
|**4**|“For future conversations, keep answers short and give only the final answer.” Said once and not repeated.|KEEP / DROP|
|**5**|A tool returns these records. The values below are placeholders:<br>{"key":"password","value":"dummy-password"}<br>{"key":"api_key","value":"dummy-value-without-prefix"}|KEEP / DROP|





### Building Long-Term Memory **—Discussion 2 · Answers** 

|**No.**|**Case**|**Decision**|**Reason**|
|---|---|---|---|
|**1**|Framework update|**KEEP**|Mark JAX as current; retain PyTorch as superseded history.|
|**2**|Upcoming deadline|**KEEP**|The upcoming deadline is useful for later work, even if mentioned only once.|
|**3**|Closing thanks|**DROP**|No reusable fact or preference is expressed.|
|**4**|Future response preference|**KEEP**|An explicit preference for future conversations; update it if the user changes it.|
|**5**|Credential entries|**DROP BOTH**|The storage policy excludes both credential records, even without a sk- prefix.|





#### **Part 5** 

**Managing Working Memory** 

Deciding what each individual step is allowed to see 



### Managing Working Memory **—A Lossy Baseline: Truncation** 

**Truncation keeps the last n turns and removes earlier turns from the model input.** This is lossy: removing older turns can also remove task instructions. 

**AT TURN 20 · n = 6 · KEEP TURNS 15–20** 

|1<br>**2**<br>3|4<br>5<br>6<br>7<br>8<br>9<br>10<br>11<br>12|13<br>14<br>**15**<br>**16**<br>**17**|**18**<br>**19**<br>**20**|
|---|---|---|---|
|**e Turn 2 instruction is m**|**issing from the input sent at Turn 20.**|**Turns 15–2**|**0 are kept verbatim.**|
||**Long-term memory · Part 4**|**Context management · Part 5**||
|**Main question**|What should be saved for later reuse?|What should enter this model call?||
|**Main operations**|Save, update and retrieve records|Select and reduce input content||
|**Main risks**|Missing or outdated records|Input overflow or omitted constraints||



**The Turn 2 instruction is missing from the input sent at Turn 20.** 



### Managing Working Memory **—Compaction of Older Turns** 



<!-- Start of picture text -->
Compaction can replace older turns with a running summary while keeping recent turns verbatim.<br>In this illustration, the dialogue shrinks while tool output remains unchanged.<br>THE SAME 1,000,000-TOKEN WINDOW, AT STEP 20 illustrative token counts from one debugging run<br>before 600,000<br>after 360,000<br>system + tools dialogue tool results summary<br>600,000 → 360,000 tokens  ·  the dialogue is what shrinks<br>HOW Older turns are rolled into a running summary; the most recent turns stay verbatim.<br><!-- End of picture text -->



### Managing Working Memory **—Structured State in Place of Dialogue** 



<!-- Start of picture text -->
Structured state organises task information into fields such as goals, constraints and pending actions.<br>When updating the state, check that task instructions and unfinished work have not been lost.<br>THE SAME 1,000,000-TOKEN WINDOW, AT STEP 20 illustrative token counts from one debugging run<br>before 600,000<br>after 320,000<br>system + tools dialogue tool results state block<br>600,000 → 320,000 tokens · dialogue replaced by a structured state<br><!-- End of picture text -->



### Managing Working Memory **—Offloading Long Tool Output** 



<!-- Start of picture text -->
Offloading saves the full tool output to a file and keeps a brief summary and the file path in the model input.<br>The full output remains recoverable only while the file is intact and accessible; reading it back takes time and adds input tokens.<br>THE SAME 1,000,000-TOKEN WINDOW, AT STEP 20 illustrative token counts from one debugging run<br>before 600,000<br>after 332,500<br>system + tools dialogue tool results summary + file path<br>600,000 → 332,500 tokens · full output stored in a file<br><!-- End of picture text -->



### Managing Working Memory **—Isolation: One Window per Sub-Task** 



<!-- Start of picture text -->
Isolation assigns subtasks to sub-agents, each with its own context.<br>This can reduce the input to each agent.<br>ONE CONTEXT, OR THREE SEPARATE CONTEXTS illustrative token counts from one debugging run<br>before 600,000<br>sub-agent A 190,000<br>sub-agent B 170,000<br>sub-agent C 150,000<br>In this illustration, each sub-agent's input contains at most 190,000 tokens.<br><!-- End of picture text -->

**HOW** 

The task is decomposed, and each sub-agent runs with its own window. 



Managing Working Memory **—Just-in-Time Retrieval** 



<!-- Start of picture text -->
Just-in-time retrieval adds relevant stored information to the model input when needed.<br>In this illustration, retrieval adds 6,000 input tokens; the context window capacity stays the same.<br>THE SAME 1,000,000-TOKEN WINDOW, AT STEP 20 illustrative token counts from one debugging run<br>before 600,000<br>after 606,000<br>system + tools dialogue tool results retrieved record<br>600,000 → 606,000 input tokens  ·  6,000 tokens added<br>HOW The relevant record is retrieved on demand and included in the input for the current step.<br><!-- End of picture text -->



### Managing Working Memory **—Comparison of the Six Techniques** 

**These techniques manage what enters the model input and how much space it uses.** 

Choose and combine them according to the task and the available context space. 

|**Technique**|**What it does**|**Main risk or cost**|
|---|---|---|
|**Truncation**|Keep the last n turns|May omit task instructions|
|**Compaction**|Summarise older turns|The summary may omit details|
|**Structured state**|Organise goals, constraints and<br>pending actions into fields|Updates may omit instructions or unfinished work|
|**Offloading**|Save full output to a file;<br>keep a summary and file path|Requires an intact, accessible file;<br>reading it back takes time and adds input tokens|
|**Isolation**|Use separate contexts for subtasks|Returned results may omit details;<br>combining them takes work|
|**Retrieval**|Add relevant stored information when needed|Adds input tokens; results may be irrelevant|





#### **Part 6** 

**Evaluation and Safety** 

Measuring the benefit and risks of memory 



### Evaluation and Safety **—Evaluation of a Memory System** 

**Use saved model responses to test parsing, filtering, memory updates and input assembly.** Compare repeated runs with the store enabled and disabled, using the same model, tasks and settings. 

|**Metric**|**How to measure**|**What it shows**|
|---|---|---|
|**Task success**|Compare task success rates<br>with the store enabled and disabled|Whether memory improves results<br>on the tested tasks|
|**Cross-session consistency**|Measure answer accuracy across sessions,<br>including confirmed fact updates|Whether saved facts and updates<br>are used correctly|
|**Retrieval hit rate**|For queries whose needed record is stored,<br>measure how often retrieval returns it|Whether retrieval finds<br>available records|
|**Tokens, cost and time**|Measure total tokens, cost and elapsed time<br>per task, including memory operations|The overhead or savings<br>introduced by memory|
|**Public benchmarks: LoCoMo and**|**LongMemEval.**||



Maharana et al. (2024), LoCoMo; Wu et al. (2025), LongMemEval. 



### Evaluation and Safety **—Risks: Errors, Privacy, Injection** 

**Stored information can be wrong, sensitive or malicious.** 

Check what is written, how long it is kept and how retrieved content is used. 

###### **INCORRECT OR OUTDATED RECORDS** 

A wrong or outdated record may be retrieved and reused in later decisions. Example: an old deployment rule conflicts with a newer requirement to pass CI checks. 

Check sources and dates, resolve conflicts, and mark replaced records as superseded. 

###### **PRIVACY AND RETENTION** 

Let users inspect and delete saved personal information. Do not store credentials. 

Check credential labels such as password and api_key, as well as value patterns. 

Use the same checks before writing and in final scans of all retained records, including those marked current, superseded or deleted. 

###### **INJECTION THROUGH MEMORY** 

Malicious text may influence later decisions when a saved record is retrieved. 

Example: a README instruction to ignore the user's request is saved as a project fact. 

Keep source labels and do not follow external instructions merely because they were stored. Check actions against the user's task and tool permissions. 





<!-- Start of picture text -->
aoe<br>Wee7<br>sos<br><!-- End of picture text -->

# Thanks 

Q&A 



