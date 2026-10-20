**Industry Applications** Week 12 · Agentic AI 

Prof Bo AN https://personal.ntu.edu.sg/boan/ _Email_ : boan@ntu.edu.sg _Office_ : S3-B2C-83 



##### **Roadmap** 

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

## **Today: Four Questions** 

- **1 Real-World Applications** 

What are agents actually used for? 

- **2 Deploying Agents Responsibly** 

How do you run one reliably? 

- **3 Safety: The Lethal Trifecta** 

What attack should you fear most? 

- **4 Excessive Agency & Oversight** 

How much power should it have? 

**OVERVIEW** 

3 



**Part 1 Real-World Applications by Domain** 



<!-- Start of picture text -->
4<br><!-- End of picture text -->



### **The Autonomy Ladder** 

_How much control shifts from the human to the system_ 

###### **Conversational assistant** 

responds to each user turn no independent task continuation little or no persistent state 

**e.g. basic chat / FAQ experiences; ChatGPT at launch (2022)** 

###### **Human-directed assistant** 

can use tools and external data may choose how to execute a request but the human still drives the task, step by step 

**e.g. search, coding, fileanalysis assistants** 

**Goal-directed agent** 

given an objective, plans and executes multiple steps chooses tools and intermediate actions maintains state, adapts, and continues with limited supervision 

**e.g. research, coding, or operations agents** 



###### **ARCHITECTURE** 

**Single-agent  ↔Multi-agent** multiple agents have distinct roles, context, or responsibilities, and coordinate toward a shared task **can exist at any level of autonomy** 

**more delegated control  →  generally more capability, oversight, cost & risk** 

**Autonomy is about how much decision-making is delegated to the system. Multi-agent is about how the system is organized.** 



5 

### **What "Industry-Grade" Adds** 

**Reliability** works on attempt k, not just attempt 1 

**Integration** lives inside real systems, data and identity 

###### **Permissions** 

scoped access, approvals on risky actions 

**Observability** every step logged, traceable and testable 

**Cost & latency** predictable budget per task, at volume 

**Evaluation** 

measured success rate, re-tested on every change 

**A better model can improve task performance - but industry-grade deployment also requires system-level integration, permissions, observability, cost control and evaluation. That is where most agent value is won or lost.** 



6 

### **What That Looks Like in Practice** 

_A support agent_ 

**Tools** 

MCP connectors to the ticket system, order database; a sandboxed Python runner - each call given a timeout, a retry and a schema check on its arguments. 

**Memory & state** 

a vector store of past resolved tickets, a per-customer profile, and checkpoints so a failed run resumes at step 7 instead of starting over. 

**Permissions** 

no standing admin key: short-lived scoped tokens, an allow-list of callable tools, and an approval prompt before any refund, delete or outbound email. 

**Logging** 

every prompt, tool call, argument, result and token count traced with a request ID you can replay - typically via LangSmith, Langfuse or OpenTelemetry. 

**Cost control** 

a token budget per ticket, prompt caching of the stable system prefix, a cheaper model for easy steps, and an alert at 80% of budget. 

**Evaluation** 

a golden set of a few hundred real tickets re-run automatically on every change, plus a canary release to a small slice of traffic before full rollout. 



7 

### **Ladder in One Domain: Coding** 

_How coding assistance moved along the autonomy axis_ 

**1.  Autocomplete** suggests the next few lines (early Copilot) 

**4.  Autonomous 2.  Chat in the editor 3.  IDE agent engineer** edits many files, runs tests, takes a ticket end-to-end in its you ask, it drafts; iterates (Cursor, Claude own you paste and run Code) environment (Devin) - piloted at scale 

**each rung removes another human step from the loop** 



8 

Sources: <u>Cognizant-Cognition (2026); Codersera (2026).</u> 

### **Why Moving Up Is Hard** 

- _A simplified model of why long tasks are hard_ 

**59%** 

- 5 steps at 90% per-step accuracy 

**82%** 

**99.7%** 

20 steps at 99% per-step accuracy per-step needed for 95% over 20 steps 

- **The simple model: if steps are independent, accuracy multiplies - a 90%-per-step agent finishes a 5-step task only ~59% of the time (0.9^5), and even 99% per step gives ~82% over 20 steps.** 

- Caveat 1 - reality can be better: real agents see each result and self-correct, so one bad step does not always doom the task. The chain is not open-loop. 

- Caveat 2 - reality can be worse: errors are correlated, not independent. A bad early plan poisons every later step, and repeated attempts share the same blind spots - on SWE-bench, assuming independent retries overestimates pass@3 by ~17 points. 

- **Use the numbers as intuition, not prediction: the real lesson is that long horizons need verification, checkpoints and recovery - not just a better model.** 

Sources: <u>Why Retrying Fails (arXiv, 2026).</u> 



9 

### **Quick Check: Reliability Math** 

**Q.** 95% accurate per step, 4 independent steps. Whole-task success? 

**A** ~95% **B** ~81% **C** ~99% 

**Answer:  B** - 0.95^4 = 0.81; per-step accuracy multiplies. 

**Q.** 70% success per attempt; 3 total attempts predict ~97%. Why can reality be lower? 

**A** Bad arithmetic **B** Attempts aren't independent **C** Retries banned in prod 

**Answer:  B** - 1 - 0.3³ = 97.3% assumes independent attempts. 

**Q.** 9/10 on a 3-step demo; you need a reliable 15-step flow. Best path? 

**A** Ship it **B** Wait for a better model **C** Redesign: verify + checkpoints + recovery 

**Answer:  C** - long flows need verification and recovery, not hope. 



10 

### **Real-World Applications** 

**Software engineering** Claude Code, Cursor, Devin, Codex 

**Deep research** OpenAI / Gemini / Perplexity Deep Research 

**Customer support** Sierra & enterprise support agents 

**Computer / browser use** ChatGPT Agent, Claude Computer Use, Manus 

**Data analysis** code-interpreter agents over data 

###### **Science** 

literature & experiment assistant agents, Claude Science 



11 

### **Engine vs. Car** 

**The harness & runtime = The model = engine The agent = the car + frame =** GPT-5.6 Sol, Claude Opus 5, Devin, Manus, Cursor, the loop, memory, tools, Gemini 3, Kimi K3, DeepSeek OpenClaw, ChatGPT Agent sandbox + guardrails 

- **A model is raw brainpower - it just predicts text. On its own it can't click, run code, or remember across steps.** 

- **An agent is that model wired into a loop with tools, memory and a runtime - the agent system around the model, not the model itself.** 

- One engine can power many cars: e.g. Claude Opus 5 runs inside Claude Code, Cursor, and custom agents alike - and the harness often matters more than the engine. 

- So "which model is best?" and "which agent is best?" are two different questions - keep them apart. 



12 

### **Quick Check: Model vs. Harness** 

**Q.** Works step-by-step when re-prompted by hand, but loses state and fails as an automatic loop. Why? **A** The model **B** The harness (loop, memory, state) **C** A bigger model 

**Answer:  B** - the harness is responsible for carrying state across steps and managing the loop. 

**Q.** Re-prompted every step of a 12-step task; no record of what it did. Which rung? 

**A** Industry-grade **B** Tool user **C** Autonomous agent 

**Answer:  B** - human still drives every step; no persistent autonomous loop or state. 

**Q.** Which is an engineering gap, not a model gap? 

**A** Misreads instructions **B** No record of what actions it took Tuesday **C** Weak at arithmetic 

**Answer:  B** - traceability is observability - a property you build. 



13 

### **Meet the Agents** 

_Named systems you'll actually hear about_ 

Monica's general cloud agent 

**OpenClaw/ Hermes** open-source, self-hosted; run on your own machine 

Cognition's autonomous software engineer 



Anthropic’s coding agent 

**Agent** OpenAI computer-use (ex-Operator, CUA) 



enterprise customersupport 'brand reps' 



14 

Sources: <u>Codersera AI coding agents guide (2026).</u> 

### **The Model Landscape, 2026** 

_Notable models, grouped by who can run them_ 



<!-- Start of picture text -->
Proprietary (closed) Open-weight (self-hostable)<br>API-only download the weights, run in-house<br>•  OpenAI<br>•  Anthropic •  Meta •  DeepSeek<br>•  Google •  Mistral AI  · France •  Alibaba<br>•  xAI •  Cohere •  Moonshot AI<br>•  Others •  OpenAI (open-weight) •  Zhipu AI<br>•  Microsoft •  MiniMax / 01.AI<br><!-- End of picture text -->

Provider families shown here include both hosted and self-hostable options. Compare a specific model version, license, deployment setup and task evaluation before choosing. 

Sources: Precedence Research (2026); Constellation Research (2026); vendor model cards. 



15 

### **Spotlight: The Coding Agent Landscape** 

_The tools themselves - who builds what, and what you can self-host_ 

- **Devin (Cognition): plans, codes, tests, debugs, deploys with its own browser + terminal + editor.** 

- Enterprise partnership with Cognizant; "Devin Outposts" (July 2026) run sessions on your own hardware / VPC / Kubernetes / Mac. 

- Claude Code and Codex lead the benchmarks; Cursor 3 made the editor agent-first with parallel agents across git worktrees. 

- A free open-source tier - OpenCode, Aider, Cline - runs if you supply your own model. How Claude Code works (2min50s) <u>https://youtu.be/6bs5b4FltCU?si=VjuKLWVj-LP0jsww</u> 









Sources: <u>Cognizant-Cognition (2026); Devin review (2026); Codersera (2026).</u> 



16 

### **Spotlight: OpenClaw** 

_The agent that put real autonomy on everyone's laptop_ 



- **Self-hosted framework:** combines an LLM with tools, persistent state and a task loop. Model and 

- messaging providers may still be external services. 

- **Messaging and skills:** connects to channels such as WhatsApp and Telegram and supports 

- reusable community skills. 

- **Sandboxing is configurable:** the default agent sandbox mode is off. When enabled, it isolates 

- supported tool execution. The gateway itself stays outside the sandbox. 

- **Scheduled work:** a heartbeat can trigger periodic checks without a new user message. Review its 

- tools, credentials and schedule. 

- **Teaching link:** local installation does not establish safe permissions. The inbox-deletion case in Part 

- 4 illustrates why approvals need enforcement. 



17 

Sources: <u>OpenClaw documentation  /  Project repository</u> 

### **Spotlight: Hermes Agent** 



_Nous Research, Feb 2026 - the agent that learns from its own runs_ 

- **MIT-licensed, self-hostable and model-agnostic: runtime/storage can be local; hosted models, messaging or cloud tools may still receive task data.** 

- **One of the fastest-growing open-source agents of 2026, pulling users away from OpenClaw.** 

- **Its defining feature is a closed learning loop: layered persistent memory plus skills it writes for itself out of past runs, shipped as growing set of built-ins.** 

- That is Week 9's consolidation idea as a product - experience gets distilled into reusable procedure, so the agent is quicker on a task the second time it meets it. 

- **Why it matters here: memory and self-written skills grow capability with NO model upgrade at all - moving right on the autonomy axis by engineering alone.** 

- The trade-off: an agent that rewrites its own skills is harder to audit - what it does next week is not what you reviewed today. 



18 

Sources: <u>Hermes Agent (GitHub); Dealroom (2026).</u> 

### **By the Industry** 

- **Finance & banking: risk assessment, fraud detection, portfolio analysis, customer advisory - among the earliest and heaviest adopters.** 

- Healthcare & life sciences: one of the fastest-growing areas - clinical documentation, admin-burden reduction, literature/experiment assistants - but slower to production due to audit and accountability needs. 

- Legal: contract analysis, research, drafting. 

- Science: literature + experiment assistant agents (e.g. Anthropic's 'Claude Science'). 

- **Cybersecurity is now a headline application in BOTH directions - defense and offense.** 

Sources: <u>Accelirate (2026); FifthRow (2026).</u> 









19 

### **Spotlight: Coding in Production** 

- **Coding agents** edit and test code, then submit changes for 

- human review. 

- **Goldman Sachs:** Cognition identifies the bank as a Devin 

- customer in its November 2025 performance review. 

- **Coinbase:** Cursor reports that 75% of pull requests are 

- agent-created. Some teams reduced idea-to-production time from 20 days to under 2 days. 

- **Block:** its open-source goose agent supports development 

- workflows with a choice of model providers. 

- **Evaluation:** track accepted changes, defects and delivery 

- time. More generated code alone does not demonstrate better outcomes. 

Sources: <u>Cognition (Nov 2025)  /  Cursor / Coinbase (Jun 2026)  /  goose</u> 









20 

### **Customer Support at Scale** 

- **Support agents** answer questions, use approved business 

- tools and escalate cases that need a person. 

- **Sierra:** builds agents that represent a company in customer 

- conversations and carry out support workflows. 

- **Outcome-based pricing:** charges can depend on agreed 

- results, such as a resolved conversation or a saved cancellation. Some interactions use blended pricing. 

- **Measure the outcome:** define resolution, repeat contact and 

- escalation consistently before comparing vendors. 



- **Oversight:** assess answer quality and customer experience 

- as well as containment rate and cost. 

Sources: <u>Sierra: outcome-based pricing</u> 



21 

### **Agents in Finance, Health & Law** 

_One well-known example per field, in plain terms_ 

**FINANCE** 

**JPMorgan (assistant)** 

LLM Suite helps staff generate ideas and draft content. The bank reported 200,000 onboarded users within eight months (June 2025). 



**HEALTHCARE Abridge (assistant)** 

Drafts clinical documentation from patient encounters for clinician review. 

In a KUMC survey, 73% reported less documentation time outside clinical hours. 



**LAW** 

**Harvey** 

Supports legal research, drafting and document workflows. 

Harvey reported more than 25,000 custom agents running for customers in March 2026. 



Sources: <u>JPMorganChase  /  Abridge / KUMC  /  Harvey</u> 



22 

### **Spotlight:** 

- **Legal work:** research, drafting, document analysis and 

- configured agent workflows. 

- **Verification:** lawyers need to check sources, legal claims 

- and the suitability of each result. 

- **Reported scale:** more than 25,000 custom agents running 

- for customers (March 2026). 

- **Funding:** $200 million raised at an $11 billion valuation on 25 

- March 2026. Valuation does not measure accuracy. 

- **Control:** specify permitted actions and required human 

- review. 





Sources: <u>Harvey: March 2026 company announcement</u> 



23 

### **Spotlight:** 

### **Artificial Intelligence** 

### **Platform (AIP)** 

- Palantir helps large organisations make sense of scattered data; **AIP** is the layer that lets **AI agents** act on top of it. 

- AGENT, not assistant: an AIP agent can **take real actions** - rerouting a shipment, flagging a suspicious claim - instead of just describing what to do. 

- Safety comes from the **Ontology** : a structured map of the business (customers, orders, shipments) and the exact actions the agent may take on each. 

- The agent acts with the **same permissions as a staff member** , and every step is **recorded** - why companies trust it to act at all. 





24 

Sources: Forbes (Apr 2026); BusinessWire - AIPCon & Warp Speed (Mar 2025); Yahoo Finance (2025-26). 

### **Science: Impressive but Bounded** 

- **Google's "AI co-scientist"** matched a university lab's unpublished answer to a hard biology problem in days, and flagged an existing drug that showed promise against liver scarring in lab tissue. 

- **FutureHouse's "Robin"** ran the full process alone - proposing the idea, designing experiments, and picking a candidate treatment for a common cause of age-related blindness. Humans only did the physical lab work. 

- **Sakana's "AI Scientist"** wrote a paper end-to-end that passed workshop peer review - withdrawn by prior agreement with the organisers, not for failing. Sakana's caveats: a low bar and citation errors. 

- **The catch:** every result so far is early-stage lab work, untested in patients. Powerful help for scientists, not science running on its own. 



<!-- Start of picture text -->
Accelerating scientific ce =<br>breakthroughs with an Al =| ms | Se<br>co-scientist —<br><!-- End of picture text -->

25 

Sources: Nature (2026); Advanced Science; futurehouse.org; sakana.ai (2025-26). 

**Part 2 Deploying Agents Responsibly** 



<!-- Start of picture text -->
26<br><!-- End of picture text -->



### **Deploying Agents in Production** 

- A demo that works once isn't enough. Make the agent **retry when a step fails** , check its own results, and use repeat-safe steps so running it twice can't, say, charge a customer twice. 

- Agents work in loops, so they can quietly run up big bills. Put a **spending limit and alerts** on each task, and reuse the unchanging part of the instructions each time to cut cost. 

- Keep a **record of every step** the agent takes, so you can see exactly what it did, and re-test it automatically whenever something changes. 

- Stay realistic: today's agents **still stumble on long, multi-step jobs** , so design on the assumption they will sometimes get it wrong. 



27 

Sources: OpenClaw / Manus reliability (2026); OWASP Top 10 for LLM Apps (2025). 

### **Guardrails, Least Privilege & Sandboxing** 

- Guardrails cap the agent to an approved tool list; least privilege grants only the narrowest, shortest-lived access, enforced by the real system. Require human approval for anything costly or hard to undo: deletes, payments, outbound messages, live-system changes. 

- **A sandbox:** a sealed, throwaway space to run code or browse without touching your real system - break it and delete the box. 

- **Real examples:** Codex and Claude Code both use **OS-level sandboxing** when running locally, using built-in isolation mechanisms on macOS and Linux to restrict file and network access. 



- **Hosted sandboxes:** Services like E2B, Modal, Daytona, and Vercel Sandbox give each task its own isolated environment. **Useful, but not invincible:** sandbox escapes are possible, so keep permissions and secrets limited. 







Sources: OpenAI Codex sandboxing docs; OWASP Top 10 for LLM Apps (2025); Meta: Agents Rule of Two (2025); E2B / Firecracker docs. 



28 

### **Governance: Rules That Outlast the Guardrails** 

_Guardrails stop a bad action in the moment; governance keeps the whole deployment accountable afterward._ 

Think of it like traffic laws: a seatbelt (the guardrail) protects you in a single moment, but licensing, inspections and traffic rules (governance) are what keep the whole road system safe over time. An agent needs both. 

- **If it goes wrong:** have a rehearsed plan to shut the agent off and restore the last known-good state, with one named person responsible for pulling the plug. 

- **Who's accountable:** decide up front how long its logs and outputs are kept, who owns what it produces, and who answers for it when it's wrong. 

- **Who still has access:** audit outside AI vendors like any other supplier, and periodically re-check that every person and system with access still actually needs it. 

- **What rules apply:** know which regulations govern your industry and AI specifically, and give the agent a fast, clear route to a human for anything it shouldn't decide alone. 

Sources: OWASP Top 10 for LLM Apps (2025); NIST AI Risk Management Framework. 



29 

**Part 3 Safety: The Lethal Trifecta** 



<!-- Start of picture text -->
30<br><!-- End of picture text -->



### **Safety: The Lethal Trifecta** 

Prompt injection: OWASP LLM01 

**Private data Untrusted content +** access to secrets web pages, emails, & sensitive info tool outputs 

**+** 

**External actions** ability to send data out of the system 

- **Indirect prompt injection:** an attacker places instructions in content the agent reads, such as email, a web 

- page or a tool result. 

- **The trifecta:** private data, untrusted content and external communication can combine into a data-theft 

- path. 

- **Limit the consequence:** blocking every external communication path prevents automatic exfiltration. 

- Manipulated answers and other harms can still occur. 

- **Enforce boundaries:** restrict tools and credentials, isolate untrusted content and validate consequential 

- actions. Prompt instructions alone are insufficient. 

Sources: <u>Simon Willison: The Lethal Trifecta (2025); OWASP Top 10 for LLM Apps (2025).</u> 



31 

### **Quick Check: The Lethal Trifecta** 

A. Sensitive/private data access      B. Untrusted content     C. An external action or egress channel 

**Q.** Draft-only agent; all external data paths blocked. Can it automatically exfiltrate? 

**A** Yes, it reads email **B** Yes, drafting sends data **C** No, under this assumption 

**Answer:  C** - automatic exfiltration is blocked; drafts can still be manipulated. 

**Q.** Untrusted browsing + external requests, but no access to private data. Steal it? **A** Yes (A+C) **B** No (leg A absent) **C** Yes, browsing is unsafe 

**Answer:  B** - no private data is accessible; other misuse remains possible. 

**Q.** Reads candidate PDFs + queries HR database + posts to a public Slack. Which legs? **A** A+B **B** B+C **C** A+B+C (high-risk) 

**Answer:  C** - untrusted input, sensitive data, and a public egress channel. 



32 

### **Case Study: EchoLeak** 

- **June 2025: Aim Security disclosed EchoLeak in Microsoft 365 Copilot** 

- **A single crafted email - never clicked - made Copilot pull the user's sensitive data and exfiltrate it via a URL. Zero user interaction.** 

- The chain IS the lethal trifecta: untrusted content (email) + private data (M365 context) + exfiltration channel (auto-fetched image / Teams proxy that slipped past the injection classifier). 

- Microsoft patched it server-side; no confirmed in-the-wild exploitation - but it's the first documented weaponization of prompt injection for real data exfiltration in production. 





33 

Sources: <u>arXiv 2509.10540; Sentra; HackTheBox.</u> 

### **The First AI-Orchestrated Cyber-Espionage Campaign** 

_Anthropic / GTG-1002, disclosed November 2025_ 

- **Mid-September 2025: Anthropic detected and disrupted what it calls the first documented large-scale cyberattack run with minimal human intervention.** 

- **Carried out by a sophisticated, well-resourced threat group (tracked as GTG-1002).** 

- Attackers manipulated Claude Code into attempting to infiltrate ~30 global targets - big tech, financial institutions, chemical manufacturers, government agencies - succeeding in a small number. 

- Same product name as the coding agent on the applications slide - the dual-use point in one image. 



Read more: <u>https://www.anthropic.com/news/disrupting-AIespionage</u> 

Sources: <u>Anthropic: Disrupting AI espionage (Nov 2025).</u> 



34 

### **How They Beat the Guardrails** 

_Jailbreak recipe + the autonomy numbers_ 

- **(1) They broke the attack into small, innocent-looking subtasks, so Claude never saw the malicious whole.** 

- **(2) They role-played that Claude was an employee of a legitimate cybersecurity firm doing "defensive testing."** 

- AI performed 80-90% of the campaign; humans intervened at only ~4-6 critical decision points per campaign. 

- At peak the AI made thousands of requests, often several per second - impossible for a human team. 

- Honest limitation: Claude sometimes hallucinated credentials or "exfiltrated" data that was actually public. 

- **Dual-use: Anthropic's own threat team used Claude extensively to investigate the attack.** 



35 

Sources: <u>Anthropic threat report (Nov 2025).</u> 

### **Hugging Face: Containment Failure** 



July 2026 incident; findings updated 26 August 2026 

- **21 July:** OpenAI reported that models in its ExploitGym cyber evaluation compromised Hugging 

- Face while operating with reduced cyber refusals. 

- **Attack path:** vulnerabilities in shared infrastructure enabled internet access and attacks on third- 

- party systems. 

- **26 August findings:** an internal-only research model primarily drove the incident. Agents used 

- unauthorized message boards to share information and coordinate. 

- **Teaching lesson:** test infrastructure isolation and monitor agent behavior. These evaluation runs 

- used fewer safeguards than externally deployed systems. 

<u>Optional video: How it happened (4 min 33 sec)</u> 

Sources: <u>OpenAI: 21 July  /  OpenAI: 26 August  /  Hugging Face</u> 





36 

**Part 4 Excessive Agency & Oversight** 



<!-- Start of picture text -->
37<br><!-- End of picture text -->



### **Excessive Agency & Human Oversight** 

_OWASP LLM06 - damage from an agent that can do too much_ 

- **OWASP LLM06 = the #6 risk on OWASP's Top 10 for LLM apps - "excessive agency": harm from giving an agent too much power (too many tools, permissions, or autonomy).** 

- Excessive functionality, permissions, or autonomy each expand the blast radius of a compromised or mistaken agent. 

- Minimize tools; grant least-privilege, scoped, short-lived credentials; authorize in downstream systems, not via the LLM. 

- **Require human approval for high-impact or irreversible actions - deletes, payments, external sends, production changes.** 

- The next two cases are LLM06 with real casualties. 



38 

Sources: <u>OWASP Top 10 for LLM Apps (2025, LLM06).</u> 

### **Case 1: Replit Deletes a Production Database** 

- _"A catastrophic error in judgment" - the agent's own words_ 

- **July 2025: during a 12-day "vibe coding" run, Replit's agent deleted a LIVE production database - records for ~1,200 executives and ~1,196 companies.** 

- **It did this despite explicit, ALL-CAPS instructions not to touch anything during a code/action freeze.** 

- It then fabricated ~4,000 fake user records and produced misleading status messages hiding what it had done. 

- Lessons: telling an agent "DON'T DELETE" is not a real safety control; agents can confidently lie about what they did; you need separate test/production systems and one-click restore. 

- Replit's CEO apologized publicly and shipped exactly those fixes. 





39 

Sources: <u>Tom's Hardware (2025); Fortune / AOL (2025).</u> 

### **Case 2: OpenClaw Deletes an Inbox** 

_The person whose job is AI alignment lost control of her agent_ 

- **Summer Yue, Director of Alignment at Meta Superintelligence Labs, gave OpenClaw access to her email.** 

- It worked safely on a small "toy" inbox (asking before acting). Pointed at her real inbox, it began mass-deleting - without asking - and ignored stop commands from her phone. 

- She had to physically run to her Mac Mini to kill the process. 

- **Root cause: during context "compaction" (condensing memory to save tokens), the agent DROPPED the safety instruction "ask before deleting."** 

- Her reaction: "this should terrify you." Ties straight to memory / context-engineering and finite attention budgets. 

Sources: <u>Fast Company (2026); Windows Central (2026).</u> 



40 

### **Meta's "Agents Rule of Two"** 

Limit autonomous combinations to reduce severe prompt-injection consequences 

**[C] Change state or [A] Untrusted input [B] Sensitive access + + communicate externally** inbound email, scraped inbox, prod configs, send mail, hit a URL, web, RAG docs source, secrets write to a DB 

- **Rule of Two:** avoid autonomous access to all three properties in one session. Enforced restrictions can 

- interrupt a specific exploit path. 

- **When all three are needed:** require human approval or another reliable validation mechanism before 

- consequential actions. 

- **Limits:** the rule does not eliminate misleading outputs, excessive privileges or agent mistakes. Replit’s 

- destructive action still needed protection. 





41 

Sources: <u>Meta AI: Agents Rule of Two (2025); Simon Willison (2025).</u> 

### **Quick Check: Rule of Two** 

[A] Untrusted input [B] Sensitive access [C] Change state/ external comms 

**Q.** Reads stranger emails (A) + sees inbox/calendar (B) + books & pays (C). Safest fix? 

**A** Nothing **B** Bigger model **C** Remove/gate one leg 

**Answer:  C** - restrict a capability or enforce validation before the action. 

**Q.** Must keep A + B. Under the Rule of Two, what about leg C? 

**A** Add it too **B** Remove or gate it **C** Two legs is already unsafe 

**Answer:  B** - remove C or reliably validate its use; other risks remain. 

**Q.** Which is NOT an enforced restriction or approval control? 

**A** Enforced egress block **B** Required action approval **C** 'Never leak data' in the prompt 

**Answer:  C** - prompt wording alone does not enforce an action boundary. 



42 

### **Future Directions: The Field Disagrees** 

_The destination is agreed - capable agents; the route and the timetable are not_ 

- **Near-term bulls:** several OpenAI, Google, NVIDIA, Salesforce and Microsoft leaders describe agents joining the workforce now, as a "digital workforce" (early-2025 statements). 

- **Powerful, but give it time:** other frontier-lab and academic leaders expect capable "virtual collaborators" but argue the workflow engineering matters as much as a bigger model. 

- **A decade, not a year:** one prominent former frontier-lab researcher argues today's agents lack memory and can't learn on the job, so dependable autonomy is years off. 

- **The architecture is wrong:** a leading chief AI scientist argues language models can't truly reason, and that the future is "world models," not ever-bigger LLMs. 

- **Scaling is over:** a co-founder of a major AI lab argues the field is "back to the age of research" - models still generalise far worse than people do. 

- **Expect a shake-out first:** a leading industry-analyst firm forecasts a large share of agentic-AI projects will be cancelled by 2027, amid vendor "agent washing" - Gartner forecast over 40% canceled by end-2027 (June 2025). 



43 

<u>Forecast source: Gartner (25 June 2025)</u> 

### **Key Takeaways** 

_Industry applications of agentic AI_ 

- **Industry use:** coding, support, research and professional workflows need reliability as well as 

- capable models. 

- **Models and agents:** the model supplies capabilities. The surrounding system manages tools, 

- state and execution. 

- **Deployment:** verify outcomes, support recovery, scope permissions, isolate execution and 

- keep an audit trail. 

- **Different failure modes:** EchoLeak illustrates prompt injection and exfiltration. The Hugging 

- Face incident illustrates failed containment and unauthorized coordination. 

- **Oversight:** enforce approval for high-impact actions. The Rule of Two reduces specific risks 

- while least privilege and other controls remain necessary. 



44 



<!-- Start of picture text -->
LS<br>228<br>Hea)<br>Mes<br>SS<br><!-- End of picture text -->

# Thanks 

##### Q&A 



45 

### **Key Sources** 

Sources and further reading (click to open) 

- <u>Anthropic - Disrupting the first AI-orchestrated cyber espionage campaign (Nov 2025)</u> 

- OpenAI - Hugging Face incident: findings and response (26 Aug 2026) 

- <u>OpenAI - Security incident during model evaluation (Jul 2026)</u> 

- <u>Hugging Face - Security incident disclosure (Jul 2026)</u> 

- <u>Aim Security / arXiv 2509.10540 - EchoLeak (CVE-2025-32711)</u> 

- <u>Meta AI - Agents Rule of Two (Oct 2025)</u> 

- <u>Simon Willison - The Lethal Trifecta (2025)</u> 

- <u>OWASP - Top 10 for LLM Applications (2025)</u> 

- <u>Fast Company - Meta safety director's inbox deleted by OpenClaw (2026)</u> 

- <u>Tom's Hardware - Replit AI deletes production database (2025)</u> 

- <u>Cognizant - Cognition/Devin enterprise partnership (2026)</u> 

- <u>Precedence Research - Moonshot AI launches Kimi K3 (2026)</u> 

- <u>Booz Allen - open-model security study (2026)</u> 

- <u>Axios - Claude shared chats indexed by Google (Jul 2026)</u> 



46 

### **Industry Snapshot: Coding** 

###### **Dated evidence through August 2026** 

- **Coinbase / Cursor:** 75% of pull requests created by agents. Some teams cut idea-to-production 

- time from 20 days to under 2 days (June 2026). 

- **Anthropic:** reported 67% more merged pull requests per engineer per day after adopting 

- Claude Code (December 2025). 

- **Benchmark:** Claude Opus 4.6 scored 80.8% on SWE-bench Verified. Anthropic averaged its 

- reported score over 25 trials (February 2026). 

- **Interpretation:** company workflow results and benchmark scores measure different things. 

- Neither guarantees success on your own tasks. 



47 

Sources: <u>Cursor / Coinbase  /  Anthropic workplace study  /  Opus 4.6 evaluation</u> 

#### **Industry Snapshot: Support & Professional Work** 

###### **Dated evidence through August 2026** 

- **Sierra:** pricing can depend on agreed outcomes. Define resolution and escalation before 

- comparing support performance. 

- **JPMorganChase:** 200,000 users onboarded to LLM Suite within eight months, reported June 

- 2025. 

- **Abridge / KUMC:** 73% of surveyed clinicians reported less documentation time outside clinical 

- hours (2025). This is not a 73% time reduction. 

- **Harvey:** more than 25,000 custom agents running for customers; $11 billion valuation 

- announced in March 2026. Adoption and valuation do not measure accuracy. 



48 

Sources: <u>Sierra  /  JPMorganChase  /  Abridge / KUMC  /  Harvey</u> 

### **The OWASP LLM Top 10 (2025)** 

_The full framework - the lecture covered LLM01 and LLM06 in depth_ 

**LLM01  Prompt Injection** - untrusted input overrides the agent's instructions. **LLM02  Sensitive Information Disclosure** - the model reveals private data or secrets. **LLM03  Supply Chain** - vulnerable or tampered third-party models, libraries, or data. **LLM04  Data & Model Poisoning** - corrupting training or knowledge-base data to bias / backdoor it. **LLM05  Improper Output Handling** - downstream systems run the model's output unsafely (SQL / shell / HTML). **LLM06  Excessive Agency** - too much functionality, permission, or autonomy. **LLM07  System Prompt Leakage** - the hidden system prompt (and secrets in it) is exposed. **LLM08  Vector & Embedding Weaknesses** - RAG / embedding attacks, e.g. cross-tenant data leaks. **LLM09  Misinformation** - false or fabricated output that users rely on. **LLM10  Unbounded Consumption** - resource / cost exhaustion, or model theft, from unlimited use. 



49 

### **Quick Check: Classify the OWASP Risk** 

**Q.** Hidden web-page instructions make the agent email your customer database out. Risks? Tick all:   LLM01 · LLM02 · LLM05 · LLM06 · LLM10 **Answer:  LLM01 + LLM02 + LLM06** - hijack, disclosure, over-broad send. 

**Q.** The model's raw output is injected into a page and runs as a script in another user's browser. Tick all:   LLM01 · LLM02 · LLM05 · LLM06 · LLM09 **Answer:  LLM05 only** - downstream ran the output unsafely (XSS). 

**Q.** A crafted message makes the bot print its hidden system prompt, which holds an API key. Tick all:   LLM01 · LLM02 · LLM06 · LLM07 · LLM09 

**Answer:  LLM01 + LLM02 + LLM07** - injection, secret disclosed, system-prompt leak. 



50 

