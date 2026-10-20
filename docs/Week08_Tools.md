**Tools, Skills, and Action Interfaces** Week 8 · Agentic AI 

Prof Bo AN https://personal.ntu.edu.sg/boan/ _Email_ : boan@ntu.edu.sg _Office_ : S3-B2C-83 



## **Roadmap** 

Six weekly sessions across Weeks 7–12 

**Introduction to Agentic AI 1** 

Agents, autonomy, reasoning & planning  (Wk 7) 

- **Tools, Skills, and Action Interfaces** 

- **2** Function calling, MCP, CodeAct, computer use  (Wk 8) 

**3** 

   - **Memory and Context Management** Memory types, context engineering, RAG  (Wk 9) 

- **Harness, Runtime, and Multi-Agent Systems** 

- **4** The loop, harnesses, orchestration  (Wk 10) 

- **Agent Training and Optimization** 

- **5** SFT, RLHF, PPO/GRPO, evaluation  (Wk 11) 

**Industry Applications 6** Deployment, safety, real-world systems  (Wk 12) 



2 

## **Today: Four Questions** 

**1 Tools & Action Interfaces** Why does a model need tools at all? 



- **2 Skills** How do you package a workflow for reuse? 



- **3 Safety & Reliability** How do you keep a wrong call contained? 



- **4 Summary & Next** What should you carry away? 



**By the end: read a schema, choose an interface, package a skill, gate risky actions.** 

**OVERVIEW** 



<!-- Start of picture text -->
fo] NANYANG TECHNOLOGICAL UNIVERSITY SINGAPORE<br><!-- End of picture text -->

3 

### **Part 1 Tools &** 

### **Action Interfaces** 

- Why agents need tools 

- Anatomy & the calling loop 

- Function · code · API · MCP · GUI 

- Choosing an interface 

From describing actions to taking them. 



#### **The Limits of a Pure LLM** 

_Grounding language in external systems_ 

LLMs reason fluently but fail at things simpler systems do trivially. Tools are the main mechanism through which an agent interacts with external systems and takes actions. 

###### **Knowledge cutoff** 

No events after training; search grounds it in current data. **_e.g._** _“What's the latest iPhone?” → can't know; a search tool fetches it._ 

###### **Hallucinated facts** 

Guesses plausibly; retrieval replaces “recall” with “look up”. **_e.g._** _Asked for a citation, it invents a real-looking DOI that doesn't exist._ 

###### **Weak computation** 

Approximates arithmetic; a calculator / code tool is exact. **_e.g._** _1234 × 5678 → often wrong; a code tool returns 7,006,652._ 

###### **No side effects** 

Can only describe an action; an API actually does it. **_e.g._** _“Email the team” → it drafts text; send_email() actually sends._ 

###### **Tools convert the model from a describer of actions into a taker of actions.** 

_Framing after Schick et al., Toolformer (2023); Weng, “LLM-Powered Autonomous Agents” (2023)._ 



**PART 1** 5 

#### **The Core Idea of a Tool** 

_Outsource what the model is bad at to deterministic programs_ 

###### **The model decides** 

WHEN to act and WITH WHAT arguments. It reasons about the goal and picks a tool. 

###### **The tool does the work** 

A deterministic program / service returns an exact, real result the model can use. 

**Analogy:** a person + a calculator + a search engine. Same person, far more capable - because the hard parts are delegated to reliable tools. 

```
without tool :  model guesses "1,642"     # often wrong
with a tool  :  calc("234*7") -> 1638     # exact, every time
```



6 

**PART 1** 

#### **An Intuition: Guess vs Look Up** 

_Same question, two ways — “Do I need an umbrella in Beijing today?”_ 

**Without a tool** `user  : umbrella in Beijing today? model : "Probably not — it's usually dry."` ✗ **guessed from memory — may be wrong** 

**With a tool** `model : get_weather( {"city":"Beijing"}) tool  : {"temp_c":21,"rain":true} model : "Yes — bring an umbrella."` ✓ **grounded in today's real data** 

**Same question: without a tool the model guesses; with a tool it looks up the real answer.** 



7 

**PART 1** 

#### **Reasoning vs Acting** 

_The think – act – observe loop (ReAct)_ 



<!-- Start of picture text -->
Thought Action Observation<br>→ →<br>reason about what to do next call a tool with arguments read the tool's result<br>loop until the model can answer<br><!-- End of picture text -->

- **Reasoning without acting** guesses - it can't see the world, so it hallucinates. 

- **Acting without reasoning** is blind - no plan for which tool or why. 

- **ReAct interleaves both:** think, act, observe, then condition the next thought on real data. 



_Yao et al., ReAct: Synergizing Reasoning and Acting in Language Models (2022)._ 

**PART 1** 8 

#### **Anatomy of a Tool** 

_A tool = name + description + typed parameters — every field, annotated_ 

**get_weather (JSON Schema)** `{ "name": "get_weather", "description": "Get today's weather for a city.", "parameters": { "type": "object", "properties": { "city": {"type": "string"} }, "required": ["city"] } }` 

###### **name** 

the identifier the model emits to call it 

**description** prompt text written for the model, not for humans — it drives selection 

###### **parameters** 

typed inputs: type · required · enum 

###### **Vague or overlapping descriptions are a top cause of wrong tool selection.** 

_Sources: OpenAI function-calling docs; Anthropic tool-use docs (2025)._ 



**PART 1** 9 

#### **Function / Tool Calling: The Mechanics** 

_The model proposes; your runtime disposes — a worked example_ 

**Declare Decide** send tool schemas (name, → model emits a structured call<sup>→</sup> 

send tool schemas (name, desc, params) 

**Execute Return** your code runs the real → append result; model function/API continues 

**One turn, end to end** `Declare :  tools = [ get_weather(city) ] Decide  :  assistant -> get_weather({"city": "Beijing"}) Execute :  runtime runs it -> {"temp_c": 21, "rain": true} Return  :  assistant -> "Yes - it's raining, bring an umbrella."` 

**The model only proposes the call; your code executes it and feeds the JSON result back.** 

_Sources: OpenAI function-calling & Agents SDK docs; Anthropic tool-use docs (2025)._ 



**PART 1** 10 

#### **A Real Message Sequence** 

_How the roles hand off, turn by turn_ 

```
user       ->  "Do I need an umbrella in Beijing today?"
assistant  ->  tool_call: get_weather({"city": "Beijing"})
tool       ->  {"temp_c": 21, "rain": true}
assistant  ->  "Yes -it's raining in Beijing, bring an umbrella."
# assistant paused, waited for the tool result (observation),
# then answered -conditioned on real data, not memory.
```

**Four messages, three roles: the assistant speaks twice — to call the tool, then to answer.** 



<!-- Start of picture text -->
fo] NANYANG TECHNOLOGICAL UNIVERSITY SINGAPORE<br><!-- End of picture text -->

11 

**PART 1** 

#### **The Execution Boundary** 

_The execution boundary is your safety boundary_ 

###### **The Model** 

Chooses a tool and arguments. Produces text only. Never touches the real system. 

###### **The Runtime / Harness** 

Validates arguments. Enforces permissions. Executes and returns the result. 

- **The model only PROPOSES;** your code DISPOSES - it decides whether and how to run the call. 

- **Because the model can be wrong,** the runtime, not the model, holds the keys. This is where Part III's safety lives. 



**PART 1** 12 

#### **Malformed Calls** 

_Four ways a call breaks — the bad call and what the runtime says back_ 

###### **Wrong type** 

a value has the wrong data type `get_weather({"city": 100}) ERROR: "city" must be a string` 

###### **Missing required** 

omits a field the schema requires `create_event({"title": "Sync"}) ERROR: "date" is required` 

###### **Hallucinated argument** 

invents a param the schema never declared `get_weather({"city":"BJ","units":"c"}) "units" ignored — not in schema` 

###### **Hallucinated tool** 

calls a tool name that doesn't exist `search_order({...}) ERROR: no such tool — did you mean search_orders?` 

**The model is stochastic — assume some calls are malformed, and validate before executing.** 



**PART 1** 13 

#### **From One Tool to Many** 

_With several tools available, name + description + schema strongly influence selection_ 

###### **Weak description** 

- “search” 

Which search? The model guesses and often picks wrong. 

###### **Strong description** 

jira_search(query): find Jira issues by text Name-spaced, specific, unambiguous. 

- **Fewer, well-chosen tools win:** if a human can't tell which tool to use, neither can the agent. 

- • **Name-space related tools:** asana_search, jira_search, github_search - clear scope prevents mis-selection. 



_Anthropic, “Writing Effective Tools for AI Agents” (2025)._ 

14 

**PART 1** 

#### **Teaching Models to Use Tools** 

_A research progression - why modern models call tools well_ 

###### **Toolformer (2023)** 

Self-supervised: the model teaches itself to call APIs, keeping only calls that reduce next-token loss. 6.7B beats GPT-3 zero-shot. 

**_e.g._** _Insight: tool use can be learned, not hand-coded._ 

###### **ToolLLM / ToolBench** 

Scales to 16,000+ real REST APIs; DFSDT (depth-first search-based decision tree) explores & backtracks; a neural retriever selects APIs. 

**_e.g._** _Insight: retrieval scales tool choice to thousands._ 

###### **Gorilla (2023)** 

Retriever-aware training; surpasses GPT-4 at writing correct API calls; adapts to changing APIs; AST-match hallucination check. 

**_e.g._** _Insight: training cuts hallucinated call syntax._ 

**2023** 

Toolformer: learn to call APIs<sup>→</sup> 

**2023** Gorilla: accurate call syntax<sup>→</sup> 

**2023-24** 

ToolLLM: 16k APIs + search<sup>→</sup> 

**2024-25** Native tool use in GPT-4, Claude, Gemini 

_From research prototypes to tool use built into the models you use today._ 

_Schick et al. (2302.04761); Qin et al. (2307.16789); Patil et al., Gorilla (2305.15334)._ 



15 

**PART 1** 

#### **In-Class Exercise · Diagnose the Tools** 

_For each tool definition, name the flaw. Answer on your own, then click to reveal._ 

**Options** well-designed · vague · dangerous · over-broad 

**1.** jira_search(query) — find Jira issues by text 

**2.** search(q) — “searches” 

**3.** run_sql(query) — any SQL, incl. DROP 

**4.** do_task(request) — anything the user asks 

**5.** get_weather(city) — today's weather 

**6.** exec_shell(cmd) — any shell command 

**well-designed vague dangerous over-broad well-designed dangerous** 

**_Why:_** _A good tool has one clear job and a description the model can route on; constrain or split the rest._ 



16 

**PART 1** 

#### **Interface 1: Function / Tool Calling** 

_Interface 1 — a single typed call to a stable service_ 

- **A model-friendly wrapper:** you expose a clean schema; the runtime calls the real API. 

- **Best when well-defined:** get_weather, create_calendar_event, search_orders. 

- **Predictable & cheap to secure:** typed, easy to validate, log and rate-limit — but one call = one action. 

**Example — one call, one typed result** `assistant -> create_calendar_event( {"title": "Sync", "date": "2026-08-12", "with": ["bo@ntu.edu.sg"]}) tool      -> {"event_id": "evt_918", "status": "created"}` 

**The default choice whenever a stable API exists for the capability you need.** 



17 

**PART 1** 

#### **Interface 2: Code as Action (CodeAct)** 

_Interface 2 — the action space becomes executable code_ 

###### **Why it's powerful** 

One action can loop, branch, use variables and compose many tools. Interpreter errors return as observations to self-debug. Up to ~20% higher success than JSON/text actions. 

###### **Why it's risky** 

Executable code can do anything - it must run in a sandbox with least privilege and resource limits. And a sandbox is not a guarantee: escapes and misconfigurations happen, so cap credentials, network reach and blast radius too. 

###### **Example — one action does the whole job** 

```
# one action loops, composes tools, and returns a value
rows  = search_orders(user_id)        # a tool call, inside code
total = sum(r.amount for r in rows)
return {"orders": len(rows), "total": total}   # -> {"orders": 7, "total": 812.5}
```



_Wang et al., Executable Code Actions Elicit Better LLM Agents / CodeAct (2402.01030)._ 

18 

**PART 1** 

#### **Interface 3: API / HTTP Calls** 

_Interface 3 — wrap an existing REST/HTTP service as a tool_ 

- **A wrapper around a REST API:** hides auth, endpoints and pagination behind a schema. 

- **Most production actions live here:** create_calendar_event, search_orders, post_message. 

- **The runtime makes the real HTTP call;** the model only sees a clean, typed interface. 

**Example — the tool hides the HTTP call** `tool   :  search_orders(user_id="u_1001") HTTP   :  GET /v1/orders?user=u_1001      (runtime adds the auth header) result :  [{"id":"o_88","amount":42.0}, ...]   -> handed back to the model` 

**Function calling and API wrapping are two views of one idea: a schema over a real service.** 



19 

**PART 1** 

#### **Interface 4: Model Context Protocol (MCP)** 

_Interface 4 — Anthropic's open standard (2024), “USB-C for AI”_ 

Solves the M × N integration problem: instead of a custom connector per app-tool pair, tool builders ship servers and app builders ship clients (M + N). 

**Tools Resources** model-controlled actions app-controlled read-only data 

**Prompts** user-controlled templates 

**Example — a GitHub MCP server, called over JSON-RPC** `host   -> server :  {"method": "tools/call", "params": {"name": "create_issue", "arguments": {"repo":"agent", "title":"bug"}}} server -> host   :  {"result": {"issue": "#1423", "url": "github.com/..."}}` 

**One server works with any MCP client unchanged — build once, plug in anywhere.** _Anthropic, Model Context Protocol (Nov 2024); modelcontextprotocol.io spec._ 



20 

**PART 1** 

#### **Interface 5: GUI / Computer Use** 

_Interface 5 — when there is no API, act like a person_ 

- **Sees a screenshot,** emits mouse / keyboard actions — click, type, scroll. 

- **Universal but costly:** works with any UI, no integration; but slower, brittle (UI changes break it), hard to supervise. 

- **Use it as a fallback:** only when no stable API or MCP server exists. 

**Example — filling a form that has no API** `screenshot                # read the current screen click(x=612, y=340)       # focus the "Amount" field type("420.00") click("Submit")  ->  screenshot   # verify it went through` 

**Maximum generality, minimum reliability — the rightmost point on the spectrum.** _Anthropic Computer Use (2024); OpenAI Operator (2025)._ 



21 

**PART 1** 

#### **Categories of Tools** 

_A practical taxonomy - what tools DO (vs how they're invoked)_ 

###### **Retrieval / search** 

web, vector store, DB **_e.g._** _Google, Pinecone, Postgres_ 

###### **Code execution** 

Python, Bash, sandboxes **_e.g._** _Code Interpreter, E2B, Docker_ 

###### **App / API integration** 

email, GitHub, Slack, CRM **_e.g._** _Gmail, GitHub, Slack, Salesforce_ 

###### **Computer & browser use** 

screenshot + mouse/keyboard **_e.g._** _Computer Use, Playwright_ 

**Vision / multimodal** OCR, image understanding **_e.g._** _GPT-4V, Gemini, Tesseract_ 

###### **System** 

files, shell, browser control **_e.g._** _filesystem, subprocess, DevTools_ 

**Computer use needs no per-app integration - but it is slower and riskier than a real API.** 



22 

**PART 1** 

#### **The Action-Interface Spectrum** 

_One table to carry away_ 

|**Interface**|**Structure**|**Flexibility**|**Reliability**|**Interface**<br>**risk**|**Typical use**|
|---|---|---|---|---|---|
|**Function / API**|High|Low|High|Low|stable APIs|
|**Code as action**|Medium|High|Medium|High|ad-hoc logic|
|**MCP**|High|Medium|High|Low|reusable tools|
|**GUI / Computer use**|Low|High|Low|High|no-API systems|



Risk here is the interface's own exposure, not the action's blast radius — a typed transfer_funds tool is high-risk however it is called, and MCP servers still need access control and input validation. 

**Pick the topmost interface that can do the job - each row down trades reliability for generality.** 



**PART 1** 23 

#### **Choosing an Interface** 

_A simple decision guide_ 

###### **Is there a stable API or MCP server?** 

→  Use function calling / MCP. Most reliable. 

**Need loops, composition, or ad-hoc logic?** 

→  Use code as action, in a sandbox. 

**Only a GUI exists, no programmatic access?** 

→  Fall back to computer / browser use. 

**Worked:** “export last month's invoices to a spreadsheet” — a billing API exists → function calling; loop over pages in code; only if the portal is UI-only, fall back to computer use. 

**Prefer structure; add generality only where the task truly requires it.** 



<!-- Start of picture text -->
fo] NANYANG TECHNOLOGICAL UNIVERSITY SINGAPORE<br><!-- End of picture text -->

24 

**PART 1** 

#### **In-Class Exercise · Choose the Interface** 

_For each capability, pick the best interface. Answer on your own, then click to reveal._ 

**Options** function · code · MCP · computer 

**1.** Weather from a service with a REST API 

**2.** Weather from a site with no API, only a web page 

**3.** Filter 300 orders, sum the totals, group by month 

**4.** Post to Slack via your team's Slack MCP server 

**5.** Submit a legacy web-only expense form (no API) 

**6.** Look up one order by id from the orders service 

**function computer code MCP computer function** 

**_Why:_** _Pick the leftmost interface that can reach the system: API exists → function; only a UI → computer._ 



25 

**PART 1** 

### **Part 2 Skills** 

- Tool vs skill 

- Anatomy of a skill (SKILL.md) 

- Composing & reusing skills 

- Progressive disclosure & design 

From single calls to reusable procedures. 



#### **Tool vs Skill** 

_Different granularity, different purpose_ 

**Tool Skill Granularity** one atomic call a multi-step method **Contains** a schema steps, guidance, + tools/code **Example** send_email(...) “schedule a meeting” **Reused by** one call site many agents & tasks 

**A tool is a single verb; a skill is the playbook that knows when and how to use several.** 



27 

**PART 2** 

#### **Anatomy of a Skill** 

_Anthropic Agent Skills: YAML frontmatter (name + description) + a Markdown procedure_ 

**SKILL.md  ·  frontmatter + Markdown** 

###### **Trigger** 

the description says when to use it — the routing signal 

```
name: schedule-meeting
description: Book a meeting. Use when asked.
```

```
---
## Steps
1. calendar_search -find a free slot
```

###### **Procedure** 

the steps in Markdown, and the tools they call 

`2. propose the slot to the user 3. on confirm, send_invite ## Avoid` 

- `never double-book` 

###### **Boundaries** 

what it must NOT do 

###### **name + description are required — the description is what routes to the skill.** 

_Anthropic Agent Skills (2025)._ 



28 

**PART 2** 

#### **Composing & Reusing Skills** 

_Reusable, composable - and a form of procedural memory_ 

- **Shared across agents:** one skill library serves many agents and tasks. 

- **Skills compose:** a skill can call tools and even other skills. 

- **Procedural memory:** know-how the agent keeps and reuses — Voyager grows its own skill library. 

**Example — a skill that composes tools and another skill** `skill: weekly-report 1. metrics = query_dashboard(range="7d")   # a tool` 

`2. draft   = summarise(metrics)             # a tool` 

`3. run skill: format-and-post(draft)        # calls another skill` 

**Build once, reuse everywhere — like a function library or an SOP manual for a fleet of agents.** _Wang et al., Voyager (2305.16291); Anthropic Agent Skills (2025)._ 



29 

**PART 2** 

#### **Progressive Disclosure** 

_Load a skill's details only when it's relevant_ 

- **Don't preload everything:** dumping every skill into the prompt wastes context and distracts the model. 

- **Retrieve on demand:** load the relevant skill when the task calls for it. 

- **Benefit:** the context stays lean and the agent stays focused. 

**Example — 60 skills available, 1 loaded** `Registered skills : 60   (names + one-line triggers only) Request           : "book a room with Bo tomorrow" Loaded in full    : 1    (schedule-meeting)  — the other 59 stay collapsed` 

**Progressive disclosure scales capability without bloating the prompt.** 



30 

**PART 2** 

#### **Designing Good Tools & Skills** 

_Tools are contracts between deterministic systems and non-deterministic agents_ 

- **Fewer, well-chosen tools:** if a human can't say which tool to use, neither can the agent. 

- **Namespacing:** prefix related tools (asana_search, jira_search) to narrow the choice. 

- **Return high-signal context:** natural-language results, not opaque IDs or raw dumps; paginate and truncate. 

- **Actionable errors:** guide self-correction (“847 results - narrow the range”), not a bare “ERROR”. 

- **Poka-yoke:** constrain arguments so mistakes are impossible (e.g. require absolute paths). 



_Anthropic, “Writing Effective Tools for AI Agents” (2025)._ 

31 

**PART 2** 

#### **In-Class Exercise · Tool or Skill?** 

_Is each a single tool, or a skill (a reusable multi-step workflow)? Answer, then click to reveal._ 

**Options** tool · skill 

**1.** send_email(to, body) **tool 2.** “Schedule a meeting”: find slot, propose, invite **skill 3.** get_weather(city) **tool 4.** “Onboard a new hire”: accounts, laptop, orientation **skill 5.** search_orders(user_id) **tool 6.** “Handle a refund”: verify, check policy, refund **skill** 

**6.** “Handle a refund”: verify, check policy, refund 

**_Why:_** _A tool is a single verb; a skill is the playbook that knows when and how to sequence several._ 



32 

**PART 2** 

### **Part 3 Safety & Reliability** 

- Real actions, real consequences 

- Permissions & human-in-the-loop 

- Sandboxing & least privilege 

- Observability & error handling 

Capability without control is dangerous. 



#### **Real Actions, Real Consequences** 

_Real actions have real, sometimes irreversible, consequences_ 

###### **Read (reversible)** 

get_weather → worst case a wrong forecast search_orders → retry freely, but it returns customer data 

###### **Write (high risk)** 

send_email → can't be unsent transfer_funds / delete_file → irreversible 

- **Blast radius:** the more powerful the tool, the more damage a wrong call can do. 

- **The model is stochastic:** it will sometimes pick the wrong tool or arguments. 

- **So design for failure:** assume some calls are wrong and contain them. 

**Real case** a coding agent handed a raw shell once ran a delete on the wrong path — one call, permanent data loss. 



34 

**PART 3** 

#### **Permissions & Human-in-the-Loop** 

_Gate high-risk actions before they run_ 

- **Tier your tools:** auto-allow authorized, appropriately scoped reads; require confirmation for writes; block the truly dangerous. 

- **Human-in-the-loop:** ask for approval before irreversible actions. 

- **Confirm with context:** show the exact action and arguments — for a read, also what it returns and to whom. 

**Example** send_email(to=all_customers) → requires explicit human approval before sending. 

**The runtime asks permission; the model never gets to skip the gate.** 



35 

**PART 3** 

#### **Sandboxing & Least Privilege** 

_Contain what code and tools can touch_ 

###### **Sandbox code execution** 

Run generated code in an isolated environment with CPU, memory, network and filesystem limits. Tools: Docker, gVisor, Firecracker, E2B. 

###### **Least privilege** 

Grant each tool only the minimum access it needs for the task — no standing admin rights. e.g. read-only OAuth scopes, scoped IAM roles. 

**Example — limits on a code sandbox and a DB tool's scope** `sandbox:  cpu=1  mem=512MB  timeout=5s  net=deny  fs=/tmp (read-write), rest read-only db-tool:  scope = orders:read           # NOT orders:write, NOT users:*` 

**Assume a call may be wrong or adversarial; limit the damage it can possibly do.** 



36 

**PART 3** 

#### **Observability** 

_You can only debug what you can see_ 

- **Log every tool call:** name, arguments, result, latency, and whether it errored. 

- **Keep the full trace:** the ordered sequence of messages and tool results per run. 

- **Why:** traces are how you find wrong tool choices, bad arguments, and loops. 

```
12:03:41  get_weather{city:"Beijing"}  ok       88ms
12:03:42  send_email{to:"all"}         BLOCKED  needs approval
```

**Instrument first - debugging an un-logged agent is guesswork.** 



37 

**PART 3** 

#### **Error-Handling Strategies** 

_Match the strategy to the failure — with examples_ 

###### **Retry** 

for transient errors (timeout, rate limit) **_e.g._** _HTTP 503 → wait 1s, retry up to 3×_ 

###### **Fallback** 

an alternative tool or a default value **_e.g._** _maps API down → use cached coordinates_ 

###### **Self-correct** 

hand the error back so the model fixes it **_e.g._** _“no such tool search_order” → retry search_orders_ 

###### **Fail gracefully** 

stop and tell the user when unrecoverable **_e.g._** _payment gateway down → “can't refund now, try later”_ 

**Feed errors back as observations — but cap retries so a bad call can't loop forever.** 



38 

**PART 3** 

#### **In-Class Exercise · Read, Approve, or Block** 

_Tier each tool call by its blast radius. Answer, then click to reveal. Two think-questions follow._ 

**Options** auto-allow · needs approval · block 

**1.** get_weather("Beijing") 

**auto-allow** 

**2.** create_draft(to, body) — nothing sent 

**auto-allow** 

**3.** send_email(to = all customers) 

**needs approval** 

**4.** run_sql("DROP TABLE users") 

**block** 

**_Why:_** _Authorized, scoped reads and reversible writes auto-run; irreversible ones need approval; unbounded ones are blocked._ 

**Think:** For “refund an order”, which interface, and what approval would you require? 

**Reference:** Stable refund API → function calling; it moves money → require human approval showing amount + order id (least privilege + HITL). 

**Think:** Five overlapping search tools — how would you redesign them? 

**Reference:** Fewer, name-spaced, single-responsibility tools (jira_search, order_search); or wrap a workflow as one skill. 



39 

**PART 3** 

### **Part 4 Summary & Next** 

- Chapter 2 in one screen 

- Extension questions 

- Next chapter preview 

Four pillars, and where we go next. 



#### **Summary** 

_Chapter 2 in one screen_ 

###### **Tools = capability** 

the main mechanism for acting on external systems **_e.g._** _get_weather, run_sql, send_email_ 

###### **Interfaces = form** 

function → code → API → MCP → computer use **_e.g._** _OpenAI functions, CodeAct, MCP, Computer Use_ 

###### **Skills = packaging** 

reusable, composable, loaded on demand **_e.g._** _a SKILL.md that orchestrates several tools_ 

###### **Engineering = trust** 

permissions, sandboxing, logging, errors **_e.g._** _approve send_email, sandbox code, log calls_ 

**Together: turning a model that describes actions into an agent that reliably takes them.** 



41 

**PART 4** 

#### **Extension & What's Next** 

_Two questions to take away - and where we go next_ 

- **Think about it:** for a “refund an order” action, which interface would you choose, and what approval would you require? 

- **Think about it:** how would you turn a wrong tool call into a lesson the agent remembers next time? 

**Next chapter →** Memory & Context Management - how tool results become memory the agent can store, summarise and reuse. 



42 

**PART 4** 



<!-- Start of picture text -->
Lo’<br>333<br>eed<br>Me<br>S82<br><!-- End of picture text -->

# Thanks 

##### Q&A 



43 

