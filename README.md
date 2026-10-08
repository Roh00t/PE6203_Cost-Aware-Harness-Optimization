# Cost-Aware Agent Harness Optimization

**PE6203 Continuous Assessment 2 (CA2): Agentic AI Implementation Project**

## The Problem

The problem we are solving is not a lack of artificial intelligence; it is a lack of operational efficiency.

Meta AI’s TUA-Bench exposes a critical vulnerability in modern agentic workflows. A frontier setup like Claude Code with Claude Opus 4.8 solves only 65.8% of these 120 real-world terminal tasks, yet it burns a massive $173.61 per run doing so. Conversely, cheaper open-weight models crash at a ~47% success rate. Standard wrappers let these lightweight models drown in their own context window, hallucinate tool calls, and loop endlessly on simple terminal errors.

## The Mission

Our mission is to decouple capability from cost. We are building a hyper-efficient, cost-aware agent harness that wraps a cheap, fixed base model and forces it to operate on the accuracy-cost Pareto frontier.

We will prove that a ruthlessly optimized execution loop—one that manages context, intercepts errors, and budgets tokens dynamically—can make a lightweight open-weight model rival an expensive proprietary model.

---

## Tech Stack

To achieve this, we bypass bloated, stateful frameworks (like LangChain or AutoGen) and build on **`mini-swe-agent`**, wired directly into the **Harbor** orchestration framework.

* **The Execution Substrate (Harbor + Docker):** Harbor natively orchestrates TUA-Bench. Every task runs in an isolated, resettable Docker Linux container. This provides a safe, ephemeral sandbox to execute raw terminal commands without risking host system corruption.


* **The Harness Layer (`mini-swe-agent`):** We utilize a radically minimal Python scaffold. Instead of using fragile JSON function-calling, it forces the agent to interact purely via Bash (`subprocess.run`) with a strictly linear history. This gives us complete programmatic control to inject our own state compaction algorithms, budget trackers, and stall detectors directly into the message loop before the model ever sees it.

---

## System Architecture

Our architecture relies on a strict separation of concerns. We separate the agent's cognitive instructions from the runtime execution and safety constraints.

### 1. Documentation & Theoretical Blueprints

* **`system_architecture.md`**: The engineering blueprint. This defines the finite state machine of our harness loop (Assemble Context → Validate → Execute → Write Back) and documents explicit optimization strategies, such as how context history is compressed and massive terminal outputs are offloaded.
* **`guardrails.md`**: The safety and execution boundary. This defines our deterministic intercepts. It outlines blocked commands (e.g., preventing irreversible deletes), sets strict retry limits (e.g., maximum 3 attempts on a malformed command), and dictates the exact error strings the harness will inject if the agent hallucinates a tool.

### 2. Cognitive Prompting & Procedural Memory

* **`claude.md` (or `agent_instructions.md`)**: The core operational playbook. This acts as the agent's procedural memory, containing the system prompt, the format for emitting Bash commands, rules for reading standard output (`stdout`), and the strict criteria for when the agent is allowed to declare a task "complete."

### 3. The Runtime Implementation

* **`harness.py`**: The brain of the operation. This Python script manages the loop. This is where we write the code to truncate observations, inject the "Remaining Budget: X Tokens" counter into the prompt, and programmatically detect if the agent is stuck in an error loop (e.g., comparing the hash of the current proposed command against the previous three).
* **`evaluate.py`**: The telemetry and benchmarking runner. It fires up the Harbor Docker containers, runs `harness.py` against the TUA-Bench tasks, records the execution-based verifier results, and outputs the raw token/dollar logs needed to plot our final Accuracy-Cost Pareto curve.



---

## Target Optimization Surfaces

This stack gives us absolute programmatic control over every token the model consumes and every command it executes across the five core optimization surfaces:

1. **Context Management**
2. **Tool Interface**
3. **Budget Allocation**
4. **Failure Detection & Recovery**
5. **Pre-Submission Verification**