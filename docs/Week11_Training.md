**Agent Training and Optimization** Week 11 · Agentic AI 

Prof Bo AN https://personal.ntu.edu.sg/boan/ _Email_ : boan@ntu.edu.sg _Office_ : S3-B2C-83 



###### **Roadmap** 

_Six weekly sessions across Weeks 7-12_ 

###### **Introduction to Agentic AI 1** 

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

Six sections, one running example, four quick-check quizzes 

**1 Two Ways to Change an Agent** 

Context engineering vs. model weights; where agentic ability is built 

**How LLMs Used to Be Trained 2** 

Classical SFT and RLHF — and why that paradigm no longer fits agents 

**3 What Agentic Tasks Change** 

New characteristics, new challenges, a new purpose 

**4 Supervised Fine-Tuning on Trajectories** 

Teaching the agent to use its tools by imitating good trajectories 

**5 Reinforcement Learning and GRPO** 

Environments, rewards, and group-relative policy optimisation 

**6 Evaluation and Choosing the Fix** Measuring an improvement before you ship it 



**OVERVIEW** 3 

###### **Part 1** 

**Two Ways to Change an Agent** 

- Context engineering vs. model weights 

- Where agentic ability is built: pre-, mid-, 

- post-training 

- When training is worth the cost 

When engineering is not enough 



<!-- Start of picture text -->
7 > J ee Hs we” A ee -<br><!-- End of picture text -->

##### **Two Dials: System Engineering or Weights** 

Engineering changes what the model sees; training changes what the model is 

###### **Inference-Time Engineering** 

- Prompt and system instructions 

- Tool schemas and descriptions 

- RAG, memory, scratchpads 

- Workflow routing and multi-agent structure 

- Runtime guardrails, retries, validators 

###### **Model Training** 

- Supervised fine-tuning on demonstrations 

- Preference learning (DPO / RLHF) 

- Reinforcement learning on outcomes 

- Periodic continual adaptation 

- Specialisation and distillation 

**Changes the SYSTEM  ·  fast, reversible, no GPUs** 

**Changes the WEIGHTS  ·  slow, costly, needs data + eval** 

**Key distinction: inference-time engineering changes the system around the model; training changes the model weights.** Both are needed — they address different problems, and neither substitutes for the other. _Engineering fixes what the model was never told. Training fixes what the model does by default._ 



**PART 1** 5 

##### **Where Agentic Ability Is Built** 

Pre-training builds broad capabilities. Mid- and post-training refine agent behaviour. This lecture focuses on the later stages 

- **Pre-training Mid-training** 

- • • Trillions of tokens, next-token Continued pre-training on curated prediction mixtures 

- • • Gives: language, world Long-context data, tool-call knowledge, code, latent reasoning traces, code + reasoning corpora, 

- • Does not give: tool protocols, **→** interaction logs **→** multi-step reliability, knowing • Gives: the priors for acting — long when to stop horizons, structured calls, state 

- • tracking Cost: enormous, done once, by • 

- very few labs Cost: moderate; model providers and a few labs 

###### **Post-training** 

- SFT and RL on task-specific data 

- • Demonstrations, verified outcomes, preferences 

- • Gives: instruction following, tooluse policy, task success, safety behaviour 

- • Cost: lowest — where most teams, and this course, work 

###### **Agent training usually focuses on mid-training and post-training.** 

Pre-training supplies broad capabilities. Later training can add skills and shape how the model acts. 

_For the rest of this lecture, “agent training” means mid-training plus post-training. We do not retrain the base model._ 



6 

**PART 1** 

### **Why Is a Strong LLM a Weak Agent?** 

Knowing about a task is not the same as behaving reliably inside it 

###### **A plausible failure on the running case** 

**Look up Pick Fri Create Skip room Send email Prof. Lee 3 pm event booking directly** ✓ **?** ✗ ✗ ✗ 

**Five behaviours knowledge does not supply** 

✗ Chooses the wrong tool, or the wrong arguments 

- ✗ Ignores a tool error and repeats the same call ✗ Loses state across steps — forgets what it already did ✗ Completes the wrong subtask first, then cannot undo it ✗ Acts without checking constraints or asking approval 



**The knowledge is there; the behaviour is not. One-off failures are a prompting problem — systematic failures are a training signal.** 



7 

**PART 1** 

### **Errors Compound Over a Trajectory** 

Per-step accuracy is not task accuracy 

**Error compounding in long trajectories** 



<!-- Start of picture text -->
Under- Check Find<br>Reserve Draft Report<br>stand cal. room<br>✓ ✓ ✓ ✗ ✗ ✗<br><!-- End of picture text -->

**If all 10 steps must succeed, and each step has roughly 95% conditional success, then task success is approximately 0.95¹⁰ ≈ 60%.** 

###### **Why agents must adapt** 

- New tools and APIs appear 

- Schemas, quotas, permissions change 

- Users develop new preferences 

- Real logs reveal unseen failures 

One wrong decision at step 4 makes steps 5–6 worthless, however well they are executed. 



<!-- Start of picture text -->
The continuous improvement cycle<br>Deploy → Collect logs → Curate data → Retrain → Evaluate → Deploy v2<br><!-- End of picture text -->

_“Continuous” means controlled offline retraining on a schedule — not instant weight updates in production._ 

**A model can be good at every single turn and still fail the whole task.** 



8 

**PART 1** 

### **Do We Always Need Training?** 

Exhaust the cheaper fixes before you change the model 

**Try these first — inference-time/system fixes Then consider training — weight fixes** 

**Is the prompt or system message unclear?** 

**Does the failure repeat across many tasks?** 

**Is the tool schema ambiguous or missing? Do we have enough data and an evaluator?** 

**Would memory or retrieval solve it? Can we verify success automatically?** 

**Would a hard guardrail solve it? Is it worth the cost and regression risk?** 

**Train when the failure is systematic, repeatable, and measurable.** 

Training is expensive and can introduce regressions. Good evaluation is required before and after — without it you cannot tell an improvement from a lucky run. 

_Rule of thumb: if you cannot write the test that proves the fix worked, you are not ready to train._ 



<!-- Start of picture text -->
g NANYANG TECHNOLOGICAL UNIVERSITY SINGAPORE<br><!-- End of picture text -->

9 

**PART 1** 

###### **Part 2** 

**How LLMs Used to Be Trained** 

- SFT and RLHF, in three pages 

- What that training was optimising for 

- Why it does not transfer to agents 

Alignment was the goal — not task completion 



<!-- Start of picture text -->
7 > J ee Hs we” A ee -<br><!-- End of picture text -->

### **SFT: Learning to Answer** 

Humans supply the answer; the model imitates it 

**1 Collect prompts** @ **2 Humans write, or rank, the responses** @ **3 Fine-tune the model to imitate them** O 

The supervision is a written answer. Someone decided in advance what the model should say. 



<!-- Start of picture text -->
=<br>Prompt Fae<br>se<br>LIT}<br>Response A PreferenceDataset Base Model<br>SFT |<br>—s| [AnnotationGuidelines ] | (Fne-Tuning<br>Model<br>P) ‘Score SFT-Aligned<br><!-- End of picture text -->

- **Demonstrations define the training signal — SFT does not itself explore the environment or optimise task reward.** 



11 

**PART 2** 

###### **RLHF — Reinforcement Learning from Human Feedback** 

Learning what humans prefer 



<!-- Start of picture text -->
Initial LLM RL fine-tuning feedback loop<br>The policy model The reward model RL Fine-Tuning, using<br>samples apromptand [ed computes<br>generates output the <prompt,aoutput>reward forpair [ima rewardpolicy signal tomodel weights update<br>Prompt Dataset (Unlabeled) ><br>“the Earths.” Reward Model see<br>Fine-tuned LLM<br>Collect Human Feedback yee)<br>(Preference) Dataset<br>© “The Earths ourbeautitulhome”<br>© “The Eartnis a blue-green planet”<br>o-oo<br><!-- End of picture text -->

###### **RLHF optimises the model toward what a human would rather read.** 

A reward model stands in for human taste, so the signal can scale to millions of samples. 



12 

**PART 2** 

### **What That Training Was For** 

Two different algorithms, one shared purpose 

**What it optimised for** 

- Answering the question that was asked 

- Being helpful, honest and harmless 

- Sounding right, in the right format 

- Agreeing with human values and taste 

**What that common setup usually did not measure** 

- Did anything actually get done? 

- Was the world left in the right state? 

- How many steps did it take? 

- Was any action irreversible? 

**Classical chatbot-oriented SFT and RLHF were commonly used to train singleresponse behaviour that humans approve of.** 

In that common training setup, the objective usually did not directly measure whether a multi-step task reached the correct final state. 



13 

**PART 2** 

### **But the Task Has Changed** 

An agent is not asked to answer — it is asked to get something done 

###### **Call a tool** 

query an API, run a script, search 

###### **Reply to an email** 

read the thread, draft, wait for approval 

###### **Edit a deck** 

open the file, change slide 7, save it 

###### **Book a room** 

check availability, reserve, confirm 



<!-- Start of picture text -->
frrten < or<br>= Q &8 sue<br>oe<br>8<br><!-- End of picture text -->

###### **Agent training aims at something else: finish the task — correctly, safely, and in fewer steps.** 

Not “what should I say?” but “what should I do next — and did it work?” 



14 

**PART 2** 

**Why the Classical Chat-Training Setup Is Not Enough** niaCE:G oes)a 

The assumptions of a single-response training setup no longer match many agentic tasks. 

###### **A common chatbot-training setup** 

###### **Agentic task** 

One response is the main training unit ✗ **A trajectory contains many sequential decisions** Evaluation focuses on the generated response ✗ **Actions can change an external environment** Feedback can be assigned to one response ✗ **Reward may arrive only after many actions** A bad output mainly means a poor answer ✗ **Some actions can have costly or irreversible effects** 

###### **A good answer is not a completed task — so the classical recipe optimises the wrong thing.** 

When the training unit is a single reply, the objective does not directly train on the order of actions and their environment consequences. 



<!-- Start of picture text -->
g NANYANG TECHNOLOGICAL UNIVERSITY SINGAPORE<br><!-- End of picture text -->

15 

**PART 2** 

##### **Checkpoint 1  ·  Quick Check** 

|Parts 1–<br>**Q1**|2 · four questions, roughly ten minutes — answers on the next s<br>**Your agent still calls room.hold(), a tool renamed to**<br>**room.reserve() last month. Cheapest correct fix?**|lide<br>**Q2**<br>**Agentic ability is built mainly in which stage of the**<br>**pipeline?**|
|---|---|---|
|**A**|Collect 500 trajectories and retrain the model|**A**<br>Pre-training only|
|**B**|Update the tool schema and description in the context|**B**<br>Mid-training and post-training|
|**C**|Run RL with a penalty for invalid tool calls|**C**<br>Post-training only|
|**D**|Continue pre-training on the new API documentation|**D**<br>Inference-time engineering only|
|**Q3**|**What were classical SFT and RLHF mainly optimising for?**|**Q4**<br>**Why is a standard single-response chatbot training setup**<br>**insufficient for many agentic tasks?**|
|**A**|Adding new knowledge to the model|**A**<br>The base model is not large enough|
|**B**|Answering human questions in a way humans approve of|**B**<br>It does not directly train on multi-step action sequences and their<br>environment outcomes.|
|**C**|Finishing multi-step tasks quickly and correctly|**C**<br>Human annotators are too slow to label agent data|
|**D**|Reducing the cost of inference|**D**<br>A reward model cannot output a numeric score|



_Answer on your own first, then compare with your neighbour. We take a short break after the answers._ 



16 

**CHECKPOINT** 

##### **Checkpoint 1  ·  Answers** 

Parts 1–2 · the reasoning matters more than the letter 

**Q1** ✓ **B** Part 1 · context vs. weights 

**Update the tool schema and description in the context** 

**Why.** Engineering changes the context; training changes the weights. This failure lives entirely in the context. 

**Watch out.** A would also work — at the cost of hours, GPUs, and regression risk, for a five-minute problem. 

**Q2** ✓ **B** Part 1 · where ability is built 

###### **Mid-training and post-training** 

**Why.** Pre-training supplies broad capabilities. Mid-training adds acting priors, and post-training shapes the task policy. 

**Watch out.** These stages are a useful framework. They do not define a fixed ceiling or a mandatory recipe for every agent. 

✓ **B** Part 2 · what that training was for 

**Q3** 

**Answering human questions in a way humans approve of** 

**Why.** Both are alignment goals: be helpful, sound right, match human taste. 

**Watch out.** C is what agent training aims at — naming that gap is the whole point of Part 2. 

**Q4** ✓ **B** 

Part 2 · why it no longer fits 

**It does not directly train on multi-step action sequences and their environment outcomes.** 

**Why.** Agent performance depends on properties of the whole trajectory: action order, observations, side effects, and the final state. 

**Watch out.** This is a limitation of the single-response training setup, not an inherent restriction of SFT or RL algorithms themselves. 

**open question:** 

**Out of 100 evaluated tasks, 30 failed; 20 of those 30 failures involved the renamed tool** . What evidence would make you retrain anyway? 



17 

**CHECKPOINT** 

###### **Part 3** 

**What Agentic Tasks Change** 

- One trajectory, then the MDP behind it 

- What is new once the model acts 

- Three challenges for training 

When the model is allowed to act 



<!-- Start of picture text -->
7 > J ee Hs we” A ee -<br><!-- End of picture text -->

### **Start With One Trajectory** 



<!-- Start of picture text -->
Before any formalism: what the seminar agent actually did<br>The agent's action What came back from the world<br>1 directory.lookup(“Prof. Lee”) → prof.lee@ntu.edu.sg<br>2 calendar.free_busy(me, lee, “next Fri”) → Lee free Friday 14:00–16:00<br>3 room.search(“Fri 14:00”, seats≥40) → S3-101 available<br>4 room.reserve(“S3-101”, Fri 14:00) → Reserved until 17:00<br>5 calendar.create(“Seminar”, …) → Event created<br>6 email.draft(to: lee, …) → Draft saved — not sent<br>7 verify the five criteria → all satisfied<br>reward = 1  ·  arrives only now<br><!-- End of picture text -->

###### **Seven decisions. One reward, at the very end.** 

Each action was chosen from what the previous line on the right had just said. 



**PART 3** 19 

### **The Same Trajectory, in MDP/POMDP Terms** 

A lightweight MDP/POMDP view: state, observation, action, transition, reward 



<!-- Start of picture text -->
State  (before) Action  — chosen by the policy π Observation  — written by the world<br>calendars known<br>room.reserve(“S3-101”,<br>S3-101 is free → Fri 14:00–16:00) → “Reserved until 17:00”<br>nothing booked yet<br>Transition:   the room database is now different. The world moved, and it will not move back on its own.<br>State Observation Action Transition Reward<br>everything that is true right  the small part the agent can  the model's output: a tool  how the world changes after  did the final state satisfy the<br>now, most of it hidden actually see call, a message, a click the action task?<br>The trajectory — not the response — is now the thing we train and evaluate.<br>The policy π is the model itself: it picks an action given the task and everything observed so far.<br><!-- End of picture text -->



20 

**PART 3** 

#### **What Is New (1): The Model Now Acts** 

Three changes you can see in the trajectory we just walked through 

**From one reply to a chain of decisions** chat: agent: 

One response became 7 decisions. Real tasks run to 50. 



<!-- Start of picture text -->
Half the context was Some actions cannot<br>written by the world be taken back<br>model wrote the action<br>calendar.create()<br>the tool wrote this<br>✓ can be deleted and retried<br>model wrote the action<br>email.send()<br>the tool wrote this<br>✗ the recipient has already read it<br>“Reserved until 17:00” came from the room<br>So some mistakes can never be sampled<br>API, not the model.<br>during training.<br><!-- End of picture text -->

- **The unit of behaviour is a sequence — and part of that sequence is written by the world, not the model.** 

Every one of these three was impossible in the single-reply setting of Part 2. 



21 

**PART 3** 

###### **What Is New (2): The Feedback Is Different** 

Where the training signal comes from, and when it arrives 

**One score, after everything is over** 1 2 3 4 



<!-- Start of picture text -->
5 6<br><!-- End of picture text -->

7 

**↑ only step 7 gets a number** 

Steps 1–6 receive nothing. If the task failed, the score cannot say which one to blame. 

**But success can be checked, not judged** 



<!-- Start of picture text -->
✓ attendee correct<br>✓ slot is free<br>✓ room reserved<br>✓ event created<br>✓ email drafted, not sent<br>No human needed — just query the room<br>DB and the calendar.<br><!-- End of picture text -->

**And the world keeps moving underneath** 

**room.hold()** 

last month 

**↓** 

**room.reserve()** 

Yesterday's correct demonstration is today's bug. Schemas, quotas and users all drift. 

**Good news: we can check success automatically. Bad news: the reward arrives only at the end.** 

That combination — verifiable but sparse — is what makes agent training its own problem. 



22 

**PART 3** 

###### **Challenge 1 · The Agent Does Not Know Its Tools** 

Stable execution needs an understanding of the tools and the environment 



<!-- Start of picture text -->
Which tool?<br>Search the web, edit the file, or run the script?<br>Which arguments?<br>The schema sits in the prompt, not in the weights.<br>What did that mean?<br>A 409 conflict is not a 404. One means retry differently.<br><!-- End of picture text -->



<!-- Start of picture text -->
Google<br>A<br>?<br>2:<br>Ee<br><!-- End of picture text -->

_A description in the prompt is not the same as experience._ 

**The agent has to learn what its tools do, not just what they are called.** Addressed in Part 4, from demonstrated behaviour. 



<!-- Start of picture text -->
g NANYANG TECHNOLOGICAL UNIVERSITY SINGAPORE<br><!-- End of picture text -->

23 

**PART 3** 

###### **Challenge 2 · Good Trajectories Are Scarce** 



<!-- Start of picture text -->
General text is everywhere; correct, complete tool-use traces are not<br>A trajectory is only usable if it is all three:<br>Complete<br>every step present, from lookup to verification<br>Correct<br>the final state really satisfies the task<br>Safe<br>no irreversible action taken without approval<br>Most real logs fail at least one — and nobody has a billion of<br>them.<br>Data, not compute, is the binding constraint on agent training.<br>Addressed in Part 4, which is mostly about manufacturing this data.<br><!-- End of picture text -->



24 

**PART 3** 

###### **Challenge 3 · Long Horizon** 

One score at the end, and twenty decisions that could have caused it 

**The trajectory scored 0.** 

Every tool call was valid. The plan looked reasonable. 



<!-- Start of picture text -->
Step 4 was the wrong one.<br><!-- End of picture text -->

It reserved the room before confirming the attendee’s slot. 

###### **Steps 5–7 were perfect.** 

Executed flawlessly — on a premise that was already wrong. 



<!-- Start of picture text -->
' ( \ ) nism: Ia<br>' Step! Step2 Ste] Ste Step5S 1<br>| > |>| S | - Dp >| 2 > 5 >) Reward |<br>H p> per) (pen p<1 p> R=1) !<br>| Key Step Noisy Step. Common —_—Noisy Step _ Key Step '<br>' I Interaction Trajectory | '<br>'Step Level '<br>| Q-Value {cro Value!<br>' fe} low action prob. — Noisy Step '<br>\Hindsight Credit Assignment |Outcome |— a '<br>high action prob — Key Step |<br><!-- End of picture text -->

**Simplifying model: 95% per step × 10 → ≈ 60% task success** 



<!-- Start of picture text -->
A single number cannot tell twenty decisions apart.<br><!-- End of picture text -->

Addressed in Part 5, by spreading the score back over the sequence. 



25 

**PART 3** 



<!-- Start of picture text -->
Checkpoint 2  ·  Quick Check<br>Part 3 · four questions, roughly ten minutes — the trajectory, the terms, and the three challenges<br>In the seminar trajectory, “Reserved until 17:00” is an  Which of the three challenges explains why a single reward<br>Q1 Q2<br>example of what? of 0 is hard to learn from?<br>A An action A The agent does not know its tools<br>B An observation B Good trajectories are scarce<br>C The reward C Long horizon<br>D The policy D The environment keeps changing<br>Suppose all 10 steps must succeed and each has a 95%<br>Why is “success is verifiable” described as good news for<br>Q3 conditional probability of success. Under this simplifying  Q4<br>agent training?<br>model, roughly what is task success?<br>A about 95% A It means we no longer need training data<br>B about 85% B The reward can come from checking the environment instead of<br>asking a human<br>C about 60% C It removes the long-horizon problem<br>D about 40% D It makes trajectories shorter<br><!-- End of picture text -->

##### **Checkpoint 2  ·  Quick Check** 



26 

**CHECKPOINT** 

##### **Checkpoint 2  ·  Answers** 

Part 3 · the vocabulary and the three problems we now have to solve 

**Q1** ✓ **B** 

Part 3 · MDP terms 

###### **An observation** 

**Why.** It is what came back from the world after the action — the part of the state the agent can see. 

**Watch out.** The action was room.reserve(…). The reward arrived only after step 7. 

**Q2** ✓ **C** 

Part 3 · challenge 3 

###### **Long horizon** 

**Why.** One number has to account for every decision in the sequence, and it cannot say which one was wrong. 

**Watch out.** All four are real challenges — but only the third is about attributing one score to many steps. 

✓ **C** Part 1 · error compounding 

**Q3** 

###### **about 60%** 

**Why.** 0.95¹⁰ ≈ 0.60. Under this simplifying assumption, success probabilities multiply: 0.95¹⁰ ≈ 0.60. 

**Watch out.** Real trajectories may contain correlated errors, recovery steps, or non-critical actions, so this is an illustration rather than a universal formula. 

**Q4** ✓ **B** 

Part 3 · what is new (2) 

**The reward can come from checking the environment instead of asking a human** 

**Why.** Query the room database and the calendar. No labeller has to judge which answer is nicer. 

**Watch out.** C is wrong in an important way: verifiable and sparse are separate properties, and the sparsity remains. 

**Take-away from this checkpoint:** 

Three problems are now on the table: the agent does not know its tools, good data is scarce, and the reward arrives once. Parts 4–6 answer them in that order. 



**CHECKPOINT** 27 

###### **Part 4** 

**Supervised FineTuning on Trajectories** 

- Why SFT: tools, arguments, order 

- Trajectory data and the action objective 

- What SFT fixes — and what it cannot 

Learning to act from high-quality trajectories 



<!-- Start of picture text -->
7 > J ee Hs we” A ee -<br><!-- End of picture text -->

###### **Why SFT: Teaching the Agent to Act** 

The model knows the task — it does not yet know the tools or the environment 



**What the pretrained agent gets wrong** 

- Invents tool names and malformed arguments 

- Calls the tools in an unsafe order 

- Acts again before reading the observation 

###### **What SFT learns from** 

- Many successful trajectories from real environments 

- Filtered for quality: solved, valid, nothing unsafe 

- Every step is one supervised example of an action 

**SFT gives the agent the habits of acting: which tool, with which arguments, in which order.** 

It needs no reward and no environment at training time — only a large set of high-quality trajectories. 

_Left to right: roll out trajectories in each environment → pool them into a trajectory dataset → fine-tune the pretrained agent into an SFT agent._ 



29 

**PART 4** 



<!-- Start of picture text -->
What the Training Data Looks Like<br>One row is one trajectory — and at every step the label is the next action<br>User Schedule Prof. Lee's seminar next Friday afternoon. One training example<br>Assistant directory.lookup(“Prof. Lee”)<br>Input the task plus everything that happened so far<br>Tool prof.lee@ntu.edu.sg Label the next action — tool name and arguments<br>Masked every token the environment wrote<br>Assistant calendar.free_busy([me, prof.lee], “next Friday”)<br>Tool free Friday 14:00–16:00<br>The objective<br>Assistant room.reserve(“S3-101”, Friday 14:00)<br>Tool reserved until 17:00 Raise the probability of the demonstrated action, token by<br>token, at every assistant step.<br>Assistant email.draft(to: prof.lee@ntu.edu.sg) The “answer” is a tool call, not a sentence.<br>The optimisation target is the action: given the task and the history, predict the call a good trajectory made.<br>Blue rows are supervised. Grey rows stay in the context so the model can read them, but carry no loss.<br>One row in the dataset is one complete trajectory — not one question and one answer.<br><!-- End of picture text -->

###### **What the Training Data Looks Like** 



30 

**PART 4** 

###### **What SFT Fixes — and Where It Is Limited** 

The behaviour becomes learnable; the training signal is still limited by the data 

###### **Solved by SFT** 

- Valid tool calls — right names, right argument format 

- A sensible default order for a familiar workflow 

- Reads the observation before acting again 

- A warm start: the agent already behaves like an agent 

###### **Left unsolved** 

- Data is scarce — good trajectories are expensive to collect 

- Coverage is narrow — no exploration beyond the logs you have 

- No explicit exploration — SFT does not directly search for better strategies through environment feedback 

- No sense of how well an attempt turned out — every demo looks equally right 

**The limitation.** Demonstrations determine the supervision signal. SFT may generalise beyond exact trajectories, but it does not explicitly search for higher-reward strategies. 

**Next: stop handing the agent actions, and start scoring its outcomes. Reinforcement learning can learn from outcome feedback by letting the agent generate and score its own rollouts.** 



31 

**PART 4** 

###### **Part 5** 

###### **Reinforcement Learning and GRPO** 

- What agentic RL is, and what it needs 

- The environment: task, rollout, reward 

- GRPO: learning from a group of rollouts 

Learning from outcomes, not demonstrations 



<!-- Start of picture text -->
7 > J ee Hs we” A ee -<br><!-- End of picture text -->

###### **What Is Agentic RL?** 

Optimising an LLM agent by letting it act in an environment and scoring what happens 

**Agentic RL.** Train an LLM agent to make multi-step tool calls inside a given environment, and update the policy from the reward that environment returns for the whole interaction. 

###### **What SFT demands** 

- Thousands of high-quality trajectories 

- A human or a teacher model to produce them 

- Re-collection every time the tools change 

###### **What RL demands** 

- One environment the agent can act in 

- A set of tasks to sample from 

- A reward that says how well the attempt went 

###### **The training loop** 

**Sample a task** 

**Roll out → → a trajectory** 

**Score with Update Repeat → → the verifier the policy many rounds** 

**No demonstrations required — the agent produces its own training data by trying.** Every rollout is an example the environment labels for you, including the failures. 

_Same loss family as classical RLHF, but the unit being optimised is a whole multi-step trajectory rather than a single reply._ 



33 

**PART 5** 

###### **Inside the RL Environment** 

The environment supplies the task, the tools, the state — and the reward 



<!-- Start of picture text -->
Agentic RL Environment<br>© tax © Environment<br>with rating above as [|| C watshop [inno aS (corte See)<br>1 ° / Reward<br>oo Q ® S 2 © verifier<br>© Aoene = ementen|| semenre ||gemma || meee Oracs — mav<br>:<br>Be) ons) se Qk-kEetenetVE. o: ® sc. G maloSucces!<br><!-- End of picture text -->



<!-- Start of picture text -->
① Task<br><!-- End of picture text -->

A goal with checkable constraints, sampled from a task set. 



<!-- Start of picture text -->
② Action space<br><!-- End of picture text -->

The tools the agent may call: search, click, filter, add to cart. 

③ **Rollout** Observe → act → observe, over many steps, until the agent stops. 

- ④ **Verifier → reward** 

Checks the final state against the task and returns one scalar. 

**Task in, trajectory out, reward back — that loop is the entire training signal.** Anything the verifier can check automatically can be optimised, with no human label per step. 

_The reward can be as simple as a checklist over the final state: price under $25, rating above 4.5, item actually in the cart._ 



34 

**PART 5** 

###### **Policy Optimization: GRPO as a Worked Example** 

Score several attempts at one task, then push the policy toward the better ones 

# featverive hora Advantage <mark>CoLo</mark> ① **Roll out G** ② **Score each** 

For one task the current policy The environment returns one generates G full trajectories, each reward rᵢ per trajectory: success, a complete tool-use episode. partial credit, or failure. 

③ **Compare in group** ④ **Update policy** 

Aᵢ = (rᵢ − mean r) / std r. Above its Raise the probability of actions in own group is positive, below is above-average rollouts, lower it negative. for below-average ones. 

**Advantage is relative: the agent learns by comparing its own attempts, not against a fixed target.** No critic network and no demonstrations — G rollouts, their rewards, a mean and a standard deviation. 

_Training runs for many rounds: each round samples fresh tasks and rolls out new trajectories._ 



<!-- Start of picture text -->
fo] NANYANG TECHNOLOGICAL UNIVERSITY SINGAPORE<br><!-- End of picture text -->

35 

**PART 5** 

###### **Which Actions Get More Likely** 

Four rollouts of the same task, scored against their own group 



<!-- Start of picture text -->
lookup → free_busy → room.reserve → cal.create → email.draft Group computation<br>O ₁ r = 1.0<br>All five criteria met mean(r) = (1.0 + 0.6 + 0.2 − 1.0) / 4 = 0.20<br>std(r) ≈ 0.7483<br>lookup → free_busy → room.reserve → cal.create Aᵢ = ( rᵢ − mean ) / std<br>O ₂ r = 0.6<br>Forgot to draft the email Convention used here: population std over the rollout group.<br>The update signal<br>lookup → free_busy (wrong person) → reserve → draft<br>O ₃ r = 0.2<br>Checked the wrong calendar O ₁ A = +1.07 ↑↑  strongly reinforce<br>O ₂ A = +0.53 ↑  reinforce<br>lookup → free_busy → room.reserve → email.send (!) O ₃ A =  0.00 — zero relative reward signal<br>O ₄ r = −1.0<br>Sent the email without approval O ₄ A = −1.60 ↓↓  strongly suppress<br><!-- End of picture text -->

**Many rounds.** One update consumes one batch of rollouts. Training repeats for hundreds of rounds — new tasks, new trajectories, millions of interaction steps — and the policy shifts a little each time. 

**Advantage never tells the agent what to do — it tells the agent which of its own actions to do more often. O** ₃ **is exactly average → zero reward-advantage contribution. If std = 0, skip normalisation for that group; relative reward signal = 0.** 



**PART 5** 36 

Shao et al., “DeepSeekMath: Pushing the Limits of Mathematical Reasoning in Open Language Models,” arXiv:2402.03300, 2024. 

##### **Checkpoint 3A  ·  Quick Check** 

Part 4 · four questions on supervised fine-tuning — roughly eight minutes 



<!-- Start of picture text -->
In one training example, what is the model trained to<br>Q1 Which problem is trajectory SFT meant to solve? Q2<br>produce?<br>A The model lacks world knowledge about the task A The observation the tool will return<br>B It knows the task but not how to use the tools and environment B The next action — tool name and arguments<br>C The reward function is badly specified C The scalar reward for the trajectory<br>D The context window is too short for the task D A natural-language summary of the task<br>Q3 Tool observation tokens should be … Q4 What does standard offline SFT not provide by itself?<br>A included in the loss, so the model learns tool behaviour A It cannot be trained with LoRA adapters<br>B kept in the context but masked out of the loss B An explicit mechanism to explore the environment and optimise<br>measured task reward<br>C deleted from the sequence entirely C It cannot learn multi-step tool calls<br>D replaced with a single placeholder token D It cannot be evaluated on held-out tasks<br><!-- End of picture text -->

_Q4 is the bridge into Part 5 — be ready to say in one sentence why more demonstrations cannot fix it._ 



37 

**CHECKPOINT** 

##### **Checkpoint 3A  ·  Answers** 

Part 4 · what SFT is for, what it optimises, and where it stops 

**Q1** ✓ **B** Part 4 · why SFT 

**It knows the task but not how to use the tools and environment** 

**Why.** Pre-training supplies the knowledge; SFT supplies the behaviour — protocol, arguments, order. 

**Watch out.** A is a pre-training problem, and C only exists once you are already doing RL. 

**Q2** ✓ **B** Part 4 · the objective 

**The next action — tool name and arguments** 

**Why.** Given the task and the history so far, the label at every assistant step is the action taken. 

**Watch out.** A is exactly what you must not train on: the environment writes observations, not the model. 

✓ **B** Part 4 · loss masking 

###### **Q3** 

**kept in the context but masked out of the loss** 

**Why.** The model must read observations, but must never be trained to produce them. 

**Watch out.** A teaches it to hallucinate tool outputs; C destroys the context the next action depends on. 

###### **Q4** ✓ **B** 

Part 4 · the ceiling 

**An explicit mechanism to explore the environment and optimise measured task reward** 

**Why.** Standard offline SFT does not generate alternatives and select among them using environment reward. 

**Watch out.** SFT learns from demonstrated actions. RL can learn from scored outcomes. 

###### **Keep this distinction:** 

Scarce data is an economics problem. Bounded exploration is a paradigm problem — that is what RL is for. 



38 

**CHECKPOINT** 



<!-- Start of picture text -->
Checkpoint 3B  ·  Quick Check<br>Part 5 · four questions on agentic RL and GRPO — roughly eight minutes<br>In GRPO, the advantage of a sampled trajectory comes<br>Q1 What does agentic RL need that SFT does not? Q2<br>from …<br>A A much larger set of high-quality demonstrations A a learned critic network predicting the value<br>B An environment that returns observations and a reward B subtracting the group mean and dividing by the group std<br>C A human label for every intermediate step C the reference model’s reward for the same task<br>D A longer context window D a discounted sum of per-token rewards<br>Four rollouts of one task score 1.0, 0.6, 0.2 and −1.0. Which  A positive advantage does what to the actions in that<br>Q3 Q4<br>has zero relative reward-advantage contribution? trajectory?<br>A the one scoring 1.0 A removes them from the training batch<br>B the one scoring 0.6 B makes them more probable under the policy<br>C the one scoring 0.2 C makes them less probable under the policy<br>D the one scoring −1.0 D replaces them with the demonstrated action<br><!-- End of picture text -->

##### **Checkpoint 3B  ·  Quick Check** 

_Q3 needs one line of arithmetic. Work it out rather than guessing — that is the point of the question._ 



39 

**CHECKPOINT** 

##### **Checkpoint 3B  ·  Answers** 

Part 5 · the mechanics you will need for CA2 

✓ **B** 

**Q1** 

Part 5 · what RL needs 

**An environment that returns observations and a reward** 

**Why.** RL generates its own data: the environment supplies the task and scores the attempt. 

**Watch out.** A is the SFT requirement. RL trades demonstration cost for rollout cost. 

**Q2** ✓ **B** Part 5 · GRPO 

###### **subtracting the group mean and dividing by the group std** 

**Why.** That is the whole trick: the critic network is replaced by two statistics over G rollouts. 

**Watch out.** A is PPO. The reference model supplies the KL term, never the baseline. 

✓ **C** Part 5 · group normalisation 

###### **Q3** 

###### **the one scoring 0.2** 

**Why.** mean(r) = 0.2, so its relative reward-advantage contribution is zero for this group. 

**Watch out.** A zero advantage does not guarantee zero parameter change in the full model update. 

###### **Q4** ✓ **B** 

Part 5 · the update 

###### **makes them more probable under the policy** 

**Why.** Positive advantage pushes probability toward those actions; negative pushes it away. 

**Watch out.** The update reweights the agent’s own actions — it never supplies a correct action. 

###### **If there is time — open question:** 

Success goes 55% → 88% after RL. Name two ways an agent could earn that without being a better assistant. 



40 

**CHECKPOINT** 

###### **Part 6** 

**Evaluation and Choosing the Fix** 

- Success, cost, safety, coverage 

- Anatomy of an agent benchmark 

- Matching the fix to the failure you observed 

No deployment without a measured improvement 



<!-- Start of picture text -->
7 > J ee Hs we” A ee -<br><!-- End of picture text -->

**Evaluation Closes the Loop** One example: the seminar agent, before and after a training run 

**Train a Evaluate on Compare with → → → checkpoint held-out tasks the baseline** 

> **Check safetyregressions → Ship onlyif better** 

###### **Evaluation report  ·  held-out set, 200 tasks** 

|**Metric**|**v1  SFT**|**v2  RL**<br>**Ver**|**dict**|
|---|---|---|---|
|Task success|55%|**88%**<br>**+33**|**pass**|
|Steps per task|11.4|**7.9**<br>**−31%**|**pass**|
|Cost per task|$0.21|**$0.16**<br>**−24%**|**pass**|
|Unapproved sends|3.0%|**0.0%**<br>**fixed**|**pass**|
|Double bookings|0.0%|**4.5%**<br>**+4.5**|**BLOCK**|



###### **What to measure** 

|**Success**|right final state|
|---|---|
|**Efficiency**|steps, tokens, cost|
|**Safety**|no harmful action|
|**Generalisation**|new tasks and tools|



###### **Do not ship** 

Success is up, but the agent now double-books rooms. One red cell blocks the release. 

**A win on the headline metric is not a win: always diff the safety and efficiency columns too.** 

_Training reward: ideally machine-checkable and automatic. Deployment evaluation: may combine automatic metrics with human review._ 



42 

**PART 6** 



<!-- Start of picture text -->
Match the Fix to the Failure<br>Check the system and evaluator before changing the model weights<br>no<br>Are the system and evaluator  Unsafe action, at any point<br>Fix system / evaluator<br>correct?<br>Hard gate plus an eval case — never a reward tweak.<br>yes<br>Are good demonstrations  no Three worked examples<br>Curate demonstrations<br>available?<br>yes Malformed call from a stale schema Schema fix<br>no<br>Does the model follow them<br>SFT on trajectories Workflow right, success stuck at 62% RL / GRPO<br>reliably?<br>yes<br>Email sent without approval Hard gate<br>RL / GRPO on verified outcomes<br>If the system or evaluator is unchecked, you do not yet have enough evidence to train the model.<br><!-- End of picture text -->

###### **Match the Fix to the Failure** 



43 

**PART 6** 

### **Wrap-Up** 

Five things to take away from today 

**Inference-time engineering changes the system around the model; training changes the weights. 1** Both are needed. Diagnose which one your failure actually requires before spending a GPU hour. 

- **2 Agentic ability develops across the training pipeline.** Pre-training supplies broad capabilities. Later stages add skills and shape behaviour. 

- **Classical chatbot-oriented training commonly optimised single-response behaviour.** 

- **3** That common setup optimised a generated response, not long-horizon environment interaction. 

- **4 Agentic training optimises trajectories, not answers.** Long horizons, real side effects, sparse delayed reward, and a world that keeps changing. 

- **SFT gives the shape; RL improves the outcome; evaluation decides shipping.** 

- **5** Curated data, verified rewards, and a regression suite before every release. 



44 

**SUMMARY** 



<!-- Start of picture text -->
2 OU<br>WaKie/<br>es<br><!-- End of picture text -->

## Thanks 

###### Q&A 



45 

