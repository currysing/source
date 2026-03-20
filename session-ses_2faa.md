# reward_loop.py detailed explanation

**Session ID:** ses_2faa55e7affeUewAfvOsL6wdd6
**Created:** 3/19/2026, 5:08:38 PM
**Updated:** 3/20/2026, 11:55:52 AM

---

## User

Explain in details and step by step about @eureka_loop\agents\reward_loop.py 

---

## Assistant (Plan · glm-5 · 50.1s)

_Thinking:_

The user wants a detailed, step-by-step explanation of the `reward_loop.py` file. Let me analyze the code and explain it thoroughly.

This file defines a `LoopAgent` that orchestrates the reward evolution process for the Eureka-like reward learning system. Let me break down each component:

1. **Imports** - The file imports necessary components
2. **_load_yaml helper** - A utility function to load YAML configuration
3. **build_reward_loop function** - The main factory function that creates the loop agent

Let me provide a comprehensive explanation of how this file works.

## Overview

`reward_loop.py` defines the **core orchestration loop** for the Eureka-like reward learning system. It creates a `LoopAgent` that iteratively evolves reward functions through a cycle of design, evaluation, selection, and reflection.

---

## Step-by-Step Breakdown

### 1. **Imports (Lines 1-8)**

```python
import yaml
from google.adk.agents import LoopAgent
from .llm_agents import RewardDesignerOpenAIAgent, RewardReflectorOpenAIAgent
from .evaluator_agent import CandidateEvaluatorAgent
from .selector_agent import SelectorAgent
from .human_reflection_agent import HumanReflectionAgent
from .increment_iteration_agent import IncrementIterationAgent
from .exit_checker_agent import ExitCheckerAgent
```

- **`yaml`** - Parses YAML configuration files
- **`LoopAgent`** - Google ADK agent that runs sub-agents in a repeat cycle
- **Sub-agents** - Each performs a specific role in the reward evolution cycle

---

### 2. **Helper Function: `_load_yaml` (Lines 10-12)**

```python
def _load_yaml(path):
    with open(path, "r") as f:
        return yaml.safe_load(f)
```

A simple utility that:
- Takes a file path
- Opens and parses YAML content
- Returns a Python dictionary

---

### 3. **Factory Function: `build_reward_loop` (Lines 14-30)**

This is the main entry point that constructs the loop agent.

#### Step 3.1: Load Configuration (Line 15)
```python
loop_cfg = _load_yaml("configs/loop_config.yaml")
```
Reads settings like `iterations`, `openai_model`, training parameters.

#### Step 3.2: Extract Model Name (Line 16)
```python
model = loop_cfg.get("openai_model", "gpt-4o-mini")
```
Gets the LLM model to use, defaulting to `gpt-4o-mini`.

#### Step 3.3: Create LoopAgent (Lines 18-30)
```python
return LoopAgent(
    name="RewardEvolutionLoop",
    sub_agents=[...],
    max_iterations=loop_cfg["iterations"]
)
```

---

### 4. **Sub-Agent Execution Order**

The loop runs these agents **sequentially** in each iteration:

| Order | Agent | Purpose |
|-------|-------|---------|
| 1 | `RewardDesignerOpenAIAgent` | Uses LLM to generate K reward function candidates |
| 2 | `CandidateEvaluatorAgent` | Trains and evaluates each candidate policy |
| 3 | `SelectorAgent` | Picks the best-performing candidate |
| 4 | `RewardReflectorOpenAIAgent` | LLM analyzes results, suggests improvements |
| 5 | `HumanReflectionAgent` | Optional human feedback injection |
| 6 | `ExitCheckerAgent` | Checks if termination criteria met |
| 7 | `IncrementIterationAgent` | Increments iteration counter |

---

### 5. **Loop Behavior**

```
Iteration 1: RewardDesign → Evaluate → Select → Reflect → Human → ExitCheck → Increment
Iteration 2: RewardDesign → Evaluate → Select → Reflect → Human → ExitCheck → Increment
...
Iteration N: (stops when max_iterations reached OR ExitChecker signals exit)
```

- **`max_iterations`** - Upper bound on loops (from config)
- **Early exit** - `ExitCheckerAgent` can terminate early if return threshold or plateau detected

---

### 6. **State Flow Between Agents**

Each agent reads/writes to the shared `ctx.session.state`:

| Key | Written By | Read By |
|-----|-----------|---------|
| `iteration` | SetupAgent, IncrementIterationAgent | All agents |
| `K` (candidates per iteration) | SetupAgent | RewardDesignerOpenAIAgent |
| `best_reward_code` | SelectorAgent | RewardReflectorOpenAIAgent |
| `candidate_results` | CandidateEvaluatorAgent | SelectorAgent |
| `reflection` | RewardReflectorOpenAIAgent | RewardDesignerOpenAIAgent (next iteration) |
| `exit_loop` | ExitCheckerAgent | LoopAgent (terminates loop) |

---

### 7. **Key Design Pattern**

The file follows the **Factory Pattern**:
- `build_reward_loop()` is a factory function
- Encapsulates agent creation and configuration
- Returns a configured `LoopAgent` ready for execution

---

## User

Explain in details and step by step about @eureka_loop\agents\selector_agent.py 

---

## Assistant (Plan · glm-5 · 23.8s)

_Thinking:_

The user wants a detailed, step-by-step explanation of the `selector_agent.py` file. Let me analyze this code thoroughly and provide a comprehensive breakdown.

## Overview

`selector_agent.py` implements the **SelectorAgent** - responsible for identifying and selecting the best-performing reward function candidate from evaluation results. It's a critical decision point in the reward evolution loop.

---

## Step-by-Step Breakdown

### 1. **Imports (Lines 1-7)**

```python
from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from typing import AsyncGenerator
import json
import numpy as np
from loguru import logger
```

| Import | Purpose |
|--------|---------|
| `BaseAgent` | Parent class for all ADK agents |
| `InvocationContext` | Session state and context access |
| `Event` | Signal yield for async iteration |
| `AsyncGenerator` | Type hint for async yield pattern |
| `json` | Parse `candidate_results` JSON string |
| `numpy` | `np.argmax()` for best score selection, `np.isnan()` for validation |
| `loguru.logger` | Structured logging |

---

### 2. **Class Structure (Line 9)**

```python
class SelectorAgent(BaseAgent):
```

- Inherits from `BaseAgent`
- Follows ADK agent pattern with `_run_async_impl` implementation

---

### 3. **Entry Point: `_run_async_impl` (Line 10)**

```python
async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
```

Async method that:
- Receives `InvocationContext` with session state
- Returns an async generator of `Event` objects

---

### 4. **Step 1: Validation - Check Data Exists (Lines 11-15)**

```python
logger.info("[SelectorAgent] Starting candidate selection...")

if "candidate_results" not in ctx.session.state:
    raise ValueError("[SelectorAgent] 'candidate_results' not found...")
```

**Purpose:** Ensures `CandidateEvaluatorAgent` ran successfully before this agent.

**Error if missing:** Upstream agent failure indicator.

---

### 5. **Step 2: Parse JSON Results (Lines 17-23)**

```python
try:
    results = json.loads(ctx.session.state["candidate_results"])
    logger.info(f"[SelectorAgent] Loaded {len(results)} candidate results")
except json.JSONDecodeError as e:
    logger.error(f"[SelectorAgent] Failed to parse candidate_results as JSON: {e}")
    logger.error(f"[SelectorAgent] candidate_results content (first 500 chars): ...")
    raise ValueError(f"[SelectorAgent] Invalid JSON in candidate_results: {e}")
```

**What it does:**
1. Parses the JSON string from session state
2. Logs number of candidates found
3. On failure: logs partial content for debugging, raises descriptive error

**Why JSON string?** Session state stores complex objects as serialized JSON strings.

---

### 6. **Step 3: Handle Empty Results (Lines 25-39)**

```python
if not results:
    llm_error = ctx.session.state.get("llm_output_error", "")
    eval_errors = ctx.session.state.get("evaluation_errors", "")
    
    error_parts = []
    if llm_error:
        error_parts.append(f"LLM parsing error: {llm_error}")
    if eval_errors:
        error_parts.append(f"Evaluation errors (all candidates failed):\n{eval_errors}")
    if not error_parts:
        error_parts.append("No candidate results were produced.")
    
    error_msg = "\n".join(error_parts)
    raise ValueError(f"[SelectorAgent] Empty candidate results. {error_msg}")
```

**Diagnostic approach:**
- Checks for upstream LLM parsing errors
- Checks for evaluation failures
- Provides detailed error message combining all failure sources

---

### 7. **Step 4: Extract and Validate Scores (Lines 41-58)**

```python
scores = []
for i, r in enumerate(results):
    score = r.get("score", -float('inf'))
    if isinstance(score, (int, float)) and not np.isnan(score):
        scores.append(float(score))
        logger.debug(f"[SelectorAgent] Candidate {i+1}: score={float(score):.2f}")
    else:
        scores.append(-float('inf'))
        logger.warning(f"[SelectorAgent] Candidate {i+1}: invalid score={score}, using -inf")

if not scores or all(s == -float('inf') for s in scores):
    logger.error(f"[SelectorAgent] All candidate scores are invalid. Scores: {scores}")
    raise ValueError("[SelectorAgent] All candidate scores are invalid (NaN or missing). ...")
```

**Score handling logic:**

| Case | Action |
|------|--------|
| Valid numeric score | Keep as float, log at debug level |
| Missing `score` key | Default to `-inf` (won't be selected) |
| NaN value | Convert to `-inf` |
| All scores invalid | Raise error - cannot select |

**Why `-inf`?** Ensures invalid candidates can never be selected by `argmax`.

---

### 8. **Step 5: Select Best Candidate (Lines 60-62)**

```python
best_idx = int(np.argmax(scores))
best = results[best_idx]
logger.info(f"[SelectorAgent] Selected candidate {best_idx + 1} (0-indexed: {best_idx}) with score={scores[best_idx]:.2f}")
```

- `np.argmax()` returns index of highest score
- `int()` converts numpy int to Python int
- Retrieves full candidate dict from results array

---

### 9. **Step 6: Validate Best Candidate (Lines 64-68)**

```python
if "reward_code" not in best:
    raise ValueError(f"[SelectorAgent] Best candidate {best_idx} missing 'reward_code' key")
if "eval" not in best or "avg_return" not in best["eval"]:
    raise ValueError(f"[SelectorAgent] Best candidate {best_idx} missing 'eval.avg_return' key")
```

**Required fields:**
- `reward_code` - The Python code for the reward function
- `eval.avg_return` - Average episode return from evaluation

These are downstream requirements for reflection and logging.

---

### 10. **Step 7: Store Results in Session State (Lines 70-73)**

```python
ctx.session.state["best_candidate_index"] = best_idx
ctx.session.state["best_reward_code"] = best["reward_code"]
ctx.session.state["best_candidate_summary"] = json.dumps(best, indent=2, default=str)
ctx.session.state["best_return"] = float(best["eval"]["avg_return"])
```

| State Key | Value | Used By |
|-----------|-------|---------|
| `best_candidate_index` | Index of selected candidate | Logging, artifacts |
| `best_reward_code` | Winning reward function code | `RewardReflectorOpenAIAgent`, `IncrementIterationAgent` |
| `best_candidate_summary` | Full JSON of best candidate | Artifacts, debugging |
| `best_return` | Average return from evaluation | `ExitCheckerAgent` (termination criteria) |

---

### 11. **Step 8: Log Completion and Yield (Lines 75-78)**

```python
logger.info(f"[SelectorAgent] Selection complete. Best return: {ctx.session.state['best_return']:.2f}")
logger.debug(f"[SelectorAgent] Best candidate summary: {ctx.session.state['best_candidate_summary'][:200]}...")

yield Event(author=self.name, content=None)
```

- Logs summary at INFO level
- Logs detailed JSON at DEBUG level (truncated to 200 chars)
- Yields `Event` to signal completion to the LoopAgent

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Session State (Input)                     │
├─────────────────────────────────────────────────────────────┤
│ candidate_results: "[                                       │
│   {\"score\": 125.5, \"reward_code\": \"...\", \"eval\": ...}, │
│   {\"score\": 98.2, \"reward_code\": \"...\", \"eval\": ...}  │
│ ]"                                                          │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
              ┌────────────────────┐
              │   SelectorAgent    │
              │                    │
              │  1. Parse JSON     │
              │  2. Validate       │
              │  3. Extract scores │
              │  4. argmax         │
              │  5. Validate best  │
              │  6. Store state    │
              └────────┬───────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                   Session State (Output)                     │
├─────────────────────────────────────────────────────────────┤
│ best_candidate_index: 0                                      │
│ best_reward_code: "def compute_reward(obs, action, ...)"     │
│ best_candidate_summary: "{\n  \"score\": 125.5, ... }"       │
│ best_return: 2500.75                                         │
└─────────────────────────────────────────────────────────────┘
```

---

## Key Design Decisions

1. **Defensive Programming**: Multiple validation layers catch errors early with descriptive messages
2. **Graceful Degradation**: Invalid scores become `-inf` rather than crashing, allowing partial success
3. **Type Safety**: Explicit `float()` conversions and `int()` for numpy returns
4. **Observability**: Comprehensive logging at INFO and DEBUG levels for traceability

---

## User

Explain in details and step by step about @eureka_loop\agents\llm_agents.py 

---

## Assistant (Plan · glm-5 · 2.9s)

_Thinking:_

The user wants a detailed explanation of the `llm_agents.py` file. Let me read itfirst.

**Tool: read**

**Input:**
```json
{
  "filePath": "C:\\Projects\\AgenticSystemDesign\\source\\eureka_loop\\agents\\llm_agents.py"
}
```

**Output:**
```
<path>C:\Projects\AgenticSystemDesign\source\eureka_loop\agents\llm_agents.py</path>
<type>file</type>
<content>1: import os
2: import json
3: from openai import OpenAI
4: from pydantic import PrivateAttr
5: from loguru import logger
6: 
7: from google.adk.agents import BaseAgent
8: from google.adk.agents.invocation_context import InvocationContext
9: from google.adk.events import Event
10: from typing import AsyncGenerator
11: 
12: client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
13: 
14: CANDIDATE_DELIM = "### CANDIDATE ###"
15: DESIGNER_SYSTEM = "You are a precise reward-function code generator for JAX/Brax environments."
16: 
17: def _designer_prompt(task_spec, env_code, best_reward_code, reflection, K, candidate_results: str | None = None):
18:     """
19:     Build the prompt for the Reward Designer.
20: 
21:     From iteration 2 onward, we include an explicit "Query with Feedback" section
22:     (policy training/eval results + reflection) similar to the Eureka paper diagram.
23:     """
24:     if best_reward_code:
25:         improvement_instruction = f"""IMPORTANT: You MUST generate {K} IMPROVED versions of the BEST REWARD SO FAR below.
26: - Each candidate should be a PROGRESSIVE IMPROVEMENT or VARIATION of the best reward
27: - Build upon the successful aspects identified in the feedback/reflection
28: - Try different approaches to address issues mentioned in the feedback/reflection
29: - Do NOT generate completely new rewards from scratch - they must be based on the best reward below"""
30: 
31:         feedback_block = f"""
32: QUERY WITH FEEDBACK (from the last iteration):
33: We trained RL policies using reward functions. Here are the results for ALL candidates from the last iteration.
34: 
35: POLICY RESULTS (JSON) - Contains results for ALL candidates:
36: {candidate_results if candidate_results else "(No candidate_results provided)"}
37: 
38: REFLECTION - Analysis of what worked, what failed, and HOW TO IMPROVE:
39: {reflection if reflection else "(No reflection available)"}
40: 
41: NOTE: This reflection may include both LLM-generated analysis and human feedback (if provided).
42: Pay special attention to any "HUMAN FEEDBACK" section, as it contains direct human insights.
43: 
44: CRITICAL INSTRUCTIONS:
45: 1. The "BEST REWARD SO FAR" below is the ONLY reward you should use as a base for improvement.
46: 2. The candidate_results JSON contains results for BOTH candidates (best and worse).
47: 3. The reflection contains THREE critical sections you MUST use:
48:    a) Analysis of what worked (preserve and enhance these aspects)
49:    b) Analysis of what failed (avoid these approaches)
50:    c) **IMPROVEMENT SUGGESTIONS** - The reflection includes "recommended_edits" and "prompt_seed" fields with SPECIFIC suggestions for how to improve the best reward
51: 4. Generate {K} improved versions based ONLY on the "BEST REWARD SO FAR" below.
52: 5. Do NOT use the worse candidate's reward code as a base - only learn from its failures.
53: 6. The worse candidate's results are provided for learning (what NOT to do), not for copying.
54: 
55: INSTRUCTION:
56: Carefully analyze the policy results and reflection above. The reflection contains:
57: - What worked in the best candidate (preserve and enhance)
58: - What failed in worse candidates (avoid)
59: - **SPECIFIC IMPROVEMENT SUGGESTIONS** in the "recommended_edits" and "prompt_seed" fields - USE THESE!
60: 
61: Generate {K} improved reward function candidates that:
62: - Are based ONLY on the "BEST REWARD SO FAR" below
63: - Preserve what worked in the best candidate (from reflection's "what_worked" and "strengths")
64: - Fix issues identified in the reflection (from reflection's "what_failed" and "weaknesses")
65: - **FOLLOW the specific improvement suggestions** from reflection's "recommended_edits" field
66: - Use the insights from reflection's "prompt_seed" field to guide your improvements
67: - Avoid the mistakes that caused the worse candidate to fail
68: - CRITICAL: If reflection mentions stability issues (falling, losing balance, becoming unstable), ensure your rewards include stability/balance terms:
69:   * Reward maintaining upright posture (body orientation angles)
70:   * Reward maintaining body height (prevent falling)
71:   * Penalize large orientation deviations
72:   * Balance speed and stability - the task requires BOTH"""
73:     else:
74:         improvement_instruction = f"""Generate {K} initial reward candidates for this task.
75: - These are the first candidates, so explore different reward shaping approaches
76: - IMPORTANT: The task requires running fast WHILE staying stable - ensure your rewards balance both:
77:   * Forward velocity reward (for speed)
78:   * Stability/balance rewards (for maintaining upright posture, preventing falls)
79:   * Control smoothness (for energy efficiency)
80: - Do NOT over-prioritize speed at the expense of stability"""
81:         feedback_block = ""
82: 
83:     return f"""Return exactly {K} reward candidates.
84: 
85: {improvement_instruction}
86: 
87: CRITICAL FORMAT RULES:
88: - Output MUST be plain Python ONLY (no markdown, no backticks, no commentary).
89: - Each candidate MUST start with: def compute_reward(
90: - Separate candidates using EXACT delimiter line:
91: {CANDIDATE_DELIM}
92: - No imports.
93: - Only use: jnp, jax, math.
94: - compute_reward must return: (total_reward, reward_terms_dict)
95: - reward_terms_dict must be a dict[str, jnp.ndarray] for each term.
96: - CRITICAL: Every compute_reward function MUST end with: return total_reward, reward_terms
97: - NEVER return None or forget the return statement - this will cause validation to fail.
98: 
99: TASK SPEC:
100: {json.dumps(task_spec, indent=2)}
101: 
102: ENV CODE:
103: {env_code}
104: 
105: BEST REWARD SO FAR (may be empty - if empty, this is the first iteration):
106: {best_reward_code if best_reward_code else "(No previous best reward - generate initial candidates)"}
107: {feedback_block}
108: 
109: EXAMPLE OUTPUT SHAPE (for 2 candidates):
110: def compute_reward(obs, action, next_obs, info):
111:     obs = jnp.asarray(obs)
112:     next_obs = jnp.asarray(next_obs)
113:     action = jnp.asarray(action)
114:     
115:     # Compute reward components
116:     v_x = next_obs[..., 8]  # forward velocity
117:     total = v_x  # total reward
118:     terms = {{"velocity": v_x}}  # reward terms dict
119:     
120:     # CRITICAL: Always return a tuple
121:     return total, terms
122: {CANDIDATE_DELIM}
123: def compute_reward(obs, action, next_obs, info):
124:     obs = jnp.asarray(obs)
125:     next_obs = jnp.asarray(next_obs)
126:     action = jnp.asarray(action)
127:     
128:     # Compute reward components
129:     v_x = next_obs[..., 8]
130:     ctrl_cost = -0.1 * jnp.sum(action ** 2)
131:     total = v_x + ctrl_cost
132:     terms = {{"velocity": v_x, "ctrl": ctrl_cost}}
133:     
134:     # CRITICAL: Always return a tuple
135:     return total, terms
136: """
137: 
138: 
139: class RewardDesignerOpenAIAgent(BaseAgent):
140:     _model: str = PrivateAttr()
141: 
142:     def __init__(self, model="gpt-4o-mini", **kwargs):
143:         super().__init__(name="RewardDesignerOpenAIAgent", **kwargs)
144:         self._model = model
145: 
146:     async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
147:         iteration = ctx.session.state.get("iteration", 1)
148:         best_reward_code = ctx.session.state.get("best_reward_code", "")
149:         reflection = ctx.session.state.get("reflection", "")
150:         K = ctx.session.state["K"]
151:         
152:         logger.info(f"[RewardDesignerOpenAIAgent] Starting reward design for iteration {iteration}")
153:         logger.info(f"[RewardDesignerOpenAIAgent] Inputs:")
154:         logger.info(f"  - K (candidates to generate): {K}")
155:         
156:         # Log task specification
157:         task_spec = ctx.session.state["task_spec"]
158:         logger.info(f"  - task_spec:")
159:         logger.info(f"      task_name: {task_spec.get('task_name', 'N/A')}")
160:         logger.info(f"      objective: {task_spec.get('objective', 'N/A')}")
161:         logger.info(f"      success_metric: {task_spec.get('success_metric', 'N/A')}")
162:         if 'constraints' in task_spec:
163:             logger.info(f"      constraints: {len(task_spec['constraints'])} constraint(s)")
164:             for i, constraint in enumerate(task_spec['constraints'], 1):
165:                 logger.info(f"        {i}. {constraint}")
166:         if 'evaluation' in task_spec:
167:             logger.info(f"      evaluation: {task_spec['evaluation']}")
168:         
169:         # Log environment code
170:         env_code = ctx.session.state["env_code"]
171:         logger.info(f"  - env_code length: {len(env_code)} chars")
172:         env_code_preview_lines = env_code.split('\n')[:10]
173:         logger.info(f"  - env_code preview (first 10 lines):")
174:         for i, line in enumerate(env_code_preview_lines, 1):
175:             logger.info(f"      {i}: {line[:100]}...")
176:         
177:         logger.info(f"  - best_reward_code length: {len(best_reward_code)} chars")
178:         logger.info(f"  - reflection length: {len(reflection)} chars")
179:         
180:         if best_reward_code:
181:             # Log first few lines of best reward code
182:             first_lines = best_reward_code.split('\n')[:5]
183:             logger.info(f"  - best_reward_code preview (first 5 lines):")
184:             for i, line in enumerate(first_lines, 1):
185:                 logger.info(f"      {i}: {line[:80]}...")
186:         else:
187:             logger.info("  - best_reward_code: EMPTY (this is the first iteration or no previous best candidate)")
188:         
189:         if reflection:
190:             logger.info(f"  - reflection length: {len(reflection)} chars")
191:             logger.info("  - Complete reflection:")
192:             logger.info("    " + "=" * 76)
193:             # Log the complete reflection with indentation for readability
194:             for line in reflection.split('\n'):
195:                 logger.info(f"    {line}")
196:             logger.info("    " + "=" * 76)
197:         else:
198:             logger.info("  - reflection: EMPTY (no previous reflection available)")
199:         
200:         candidate_results = None
201:         # Only include "query with feedback" after we have results (i.e., from iteration 2 onward).
202:         if iteration > 1:
203:             candidate_results = ctx.session.state.get("candidate_results", None)
204: 
205:         prompt = _designer_prompt(
206:             ctx.session.state["task_spec"],
207:             ctx.session.state["env_code"],
208:             best_reward_code,
209:             reflection,
210:             K,
211:             candidate_results=candidate_results,
212:         )
213: 
214:         from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
215:         
216:         @retry(
217:             stop=stop_after_attempt(3),
218:             wait=wait_exponential(multiplier=1, min=2, max=10),
219:             retry=retry_if_exception_type((Exception,)),  # Retry on any exception
220:             reraise=True
221:         )
222:         def call_llm():
223:             return client.chat.completions.create(
224:                 model=self._model,
225:                 messages=[
226:                     {"role": "system", "content": DESIGNER_SYSTEM},
227:                     {"role": "user", "content": prompt},
228:                 ],
229:                 temperature=0.4,
230:             )
231:         
232:         try:
233:             resp = call_llm()
234:             generated_text = resp.choices[0].message.content
235:             ctx.session.state["reward_candidates_text"] = generated_text
236:             
237:             # Count how many candidates were generated
238:             candidate_count = generated_text.count(CANDIDATE_DELIM) + 1
239:             logger.info(f"[RewardDesignerOpenAIAgent] Generated {candidate_count} reward candidate(s) (expected {K})")
240:             logger.debug(f"[RewardDesignerOpenAIAgent] Generated text length: {len(generated_text)} chars")
241:         except Exception as e:
242:             logger.error(f"[RewardDesignerOpenAIAgent] Failed to get LLM response after retries: {e}")
243:             raise ValueError(f"LLM API call failed: {e}")
244:         yield Event(author=self.name, content=None)
245: 
246: 
247: class RewardReflectorOpenAIAgent(BaseAgent):
248:     _model: str = PrivateAttr()
249: 
250:     def __init__(self, model="gpt-4o-mini", **kwargs):
251:         super().__init__(name="RewardReflectorOpenAIAgent", **kwargs)
252:         self._model = model
253: 
254:     async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
255:         iteration = ctx.session.state.get("iteration", 1)
256:         task_spec = ctx.session.state["task_spec"]
257:         candidate_results = ctx.session.state.get("candidate_results", "")
258:         best_candidate_index = ctx.session.state.get("best_candidate_index", 0)
259:         
260:         # Validate required state
261:         if not candidate_results:
262:             logger.warning("[RewardReflectorOpenAIAgent] No candidate_results found. This may be the first iteration.")
263:             # For first iteration, we might not have results yet - skip reflection
264:             ctx.session.state["reflection"] = "No candidate results available for reflection (first iteration)."
265:             yield Event(author=self.name, content=None)
266:             return
267:         
268:         logger.info(f"[RewardReflectorOpenAIAgent] Starting reflection for iteration {iteration}")
269:         logger.info(f"[RewardReflectorOpenAIAgent] Best candidate index: {best_candidate_index}")
270:         logger.debug(f"[RewardReflectorOpenAIAgent] Candidate results length: {len(candidate_results)} chars")
271: 
272:         prompt = f"""Analyze the candidate reward functions and provide detailed feedback for improvement.
273: 
274: TASK SPECIFICATION:
275: {json.dumps(task_spec, indent=2)}
276: 
277: CANDIDATE RESULTS (JSON):
278: {candidate_results}
279: 
280: BEST CANDIDATE INDEX: {best_candidate_index}
281: 
282: IMPORTANT: The candidate_results contains results for ALL candidates from this iteration.
283: - Candidate at index {best_candidate_index} is the BEST performing one (selected for next iteration)
284: - The other candidate(s) performed WORSE and will NOT be used as a base for next iteration
285: - Your analysis should help the designer understand what to preserve (from best) and what to avoid (from worse)
286: 
287: ANALYSIS INSTRUCTIONS:
288: For EACH candidate (both best and worse), analyze the following behavioral metrics from train_metrics:
289: 1. Forward Velocity (eval/episode_x_velocity): 
290:    - Positive = moving forward (good), Negative = moving backward (bad)
291:    - Higher absolute value = faster movement
292:    - Compare velocities across candidates
293:    - WARNING: Very high velocity may indicate instability or falling - check stability metrics
294: 
295: 2. Stability and Balance (CRITICAL):
296:    - Check if the policy maintains upright posture throughout the episode
297:    - Look for signs of falling: sudden drops in height, loss of balance, episode termination
298:    - Analyze body orientation/angles - should remain stable and balanced
299:    - If velocity increases but stability decreases, this is a RED FLAG - reward may be over-prioritizing speed
300:    - The task requires "staying stable" - speed without stability is a failure
301: 
302: 3. Distance Traveled (eval/episode_x_position):
303:    - Final x_position indicates how far the cheetah traveled
304:    - Positive = forward progress, Negative = backward movement
305:    - Higher absolute value = better performance
306:    - If distance is high but episode ends early (falling), stability is compromised
307: 
308: 4. Control Smoothness (eval/episode_reward_ctrl):
309:    - More negative = higher control penalty (jerky/inefficient actions)
310:    - Less negative = smoother, more efficient control
311:    - Compare control penalties across candidates
312:    - Jerky actions may indicate instability or over-aggressive speed pursuit
313: 
314: 5. Running Reward Component (eval/episode_reward_run):
315:    - Component of reward related to forward motion
316:    - Positive = reward for running, Negative = penalty
317:    - Analyze if this component is working as intended
318:    - If this is too high relative to stability terms, it may cause instability
319: 
320: 6. Episode Length / Termination:
321:    - Check if episodes complete the full horizon or terminate early
322:    - Early termination often indicates falling or instability
323:    - Compare episode lengths across candidates
324: 
325: 7. Overall Performance (score/avg_return):
326:    - Compare final scores across all candidates
327:    - Identify what makes the best candidate successful
328:    - Consider: Is high score due to speed OR stability? Both are required.
329: 
330: 8. Reward Code Analysis:
331:    - Examine the actual reward function code
332:    - Identify which reward terms are contributing positively/negatively
333:    - Check for numerical stability issues
334:    - Verify reward shaping aligns with task objectives
335:    - CRITICAL: Check if reward has stability/balance terms (upright posture, height maintenance, orientation)
336:    - If reward only emphasizes velocity without stability terms, this will cause falling
337: 
338: Based on this analysis, provide a structured analysis:
339: 
340: For the BEST candidate (index {best_candidate_index}):
341: - what_worked: Specific aspects that led to good performance (e.g., "forward velocity reward term was effective", "control penalty weight was well-balanced")
342: - strengths: Key strengths to preserve and build upon
343: 
344: For the WORSE candidate(s):
345: - what_failed: Specific issues that caused poor performance (e.g., "control penalty too high causing freezing", "negative velocity indicates backward movement", "reward shaping was insufficient", "policy falls at end due to instability", "over-prioritized speed without stability")
346: - weaknesses: Key weaknesses to avoid in future iterations
347: 
348: Overall recommendations:
349: - diagnosis: Overall assessment comparing best vs worse candidates
350:   - Pay special attention to speed vs stability tradeoff
351:   - If best candidate has high velocity but falls/becomes unstable, this is a critical issue
352:   - The task requires BOTH speed AND stability - one without the other is insufficient
353: - recommended_edits: Concrete suggestions for improving the BEST reward function:
354:   - If stability is an issue: "add stability bonus for maintaining upright posture", "penalize large body orientation angles", "reward maintaining body height", "add balance term based on center of mass"
355:   - If speed-stability tradeoff: "reduce forward velocity reward weight and increase stability reward weight", "add penalty for falling or losing balance", "ensure stability terms are weighted appropriately relative to velocity"
356:   - Examples: "reduce control penalty weight from 0.1 to 0.05", "add stability bonus: reward = 0.5 * velocity + 0.3 * stability - 0.1 * control_cost", "increase forward velocity reward scaling"
357: - prompt_seed: Key insights to guide next reward generation, emphasizing:
358:   * What to preserve from the best candidate
359:   * What to avoid based on the worse candidate's failures
360:   * How to improve the best candidate further
361:   * CRITICAL: If stability issues are detected, emphasize the need for stability/balance reward terms
362:   * Balance speed and stability - the task requires "staying stable" while running fast
363: 
364: CRITICAL: Make it clear that the designer should ONLY use the best candidate's reward code as a base, and use the worse candidate's results only as learning (what NOT to do).
365: 
366: Return ONLY valid JSON (no markdown, no code blocks) with these fields.
367: """
368: 
369:         from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
370:         
371:         @retry(
372:             stop=stop_after_attempt(3),
373:             wait=wait_exponential(multiplier=1, min=2, max=10),
374:             retry=retry_if_exception_type((Exception,)),
375:             reraise=True
376:         )
377:         def call_llm():
378:             return client.chat.completions.create(
379:                 model=self._model,
380:                 messages=[{"role": "user", "content": prompt}],
381:                 temperature=0.2,
382:             )
383:         
384:         try:
385:             resp = call_llm()
386:             reflection_text = resp.choices[0].message.content
387:             ctx.session.state["reflection"] = reflection_text
388:             logger.info(f"[RewardReflectorOpenAIAgent] Generated reflection (length: {len(reflection_text)} chars)")
389:             logger.info("=" * 80)
390:             logger.info("[RewardReflectorOpenAIAgent] COMPLETE REFLECTION:")
391:             logger.info("=" * 80)
392:             # Log the complete reflection, splitting by lines for better readability
393:             for line in reflection_text.split('\n'):
394:                 logger.info(line)
395:             logger.info("=" * 80)
396:         except Exception as e:
397:             logger.error(f"[RewardReflectorOpenAIAgent] Failed to get LLM response after retries: {e}")
398:             # Don't fail the whole loop if reflection fails - just use empty reflection
399:             ctx.session.state["reflection"] = f"Reflection generation failed: {e}"
400:         yield Event(author=self.name, content=None)

(End of file - total 400 lines)
</content>
```

---

## Assistant (Plan · glm-5 · 78.0s)

_Thinking:_

The user wants a detailed, step-by-step explanation of the `llm_agents.py` file. This file contains two agent classes:
1. `RewardDesignerOpenAIAgent` - Generates reward function candidates using LLM
2. `RewardReflectorOpenAIAgent` - Analyzes results and provides reflection/feedback

Let me provide a comprehensive breakdown ofthis file.

## Overview

`llm_agents.py` implements **two LLM-powered agents** that form the intelligence core of the Eureka-like reward evolution system:
1. **RewardDesignerOpenAIAgent** - Generates reward function candidates
2. **RewardReflectorOpenAIAgent** - Analyzes results and provides improvement guidance

---

## Step-by-Step Breakdown

### 1. **Imports & Global Setup (Lines 1-12)**

```python
import os
import json
from openai import OpenAI
from pydantic import PrivateAttr
from loguru import logger

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from typing import AsyncGenerator

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
```

| Import | Purpose |
|--------|---------|
| `OpenAI` | OpenAI API client for LLM calls |
| `PrivateAttr` | Pydantic private attributes (not serialized) |
| `BaseAgent`, `InvocationContext`, `Event` | ADK agent framework |
| `client = OpenAI(...)` | Global API client initialized once |

---

### 2. **Constants & Prompt Templates (Lines 14-16)**

```python
CANDIDATE_DELIM = "### CANDIDATE ###"
DESIGNER_SYSTEM = "You are a precise reward-function code generator for JAX/Brax environments."
```

- **`CANDIDATE_DELIM`** - Separator between multiple reward function candidates in LLM output
- **`DESIGNER_SYSTEM`** - System prompt for the designer LLM

---

### 3. **Helper Function: `_designer_prompt` (Lines 17-136)**

Builds the complete prompt for the Reward Designer LLM.

#### Step 3.1: Determine Improvement vs. Initial Generation (Lines 24-81)

```python
if best_reward_code:
    improvement_instruction = f"""IMPORTANT: You MUST generate {K} IMPROVED versions..."""
    feedback_block = f"""
    QUERY WITH FEEDBACK (from the last iteration):
    ...
    """
else:
    improvement_instruction = f"""Generate {K} initial reward candidates..."""
    feedback_block = ""
```

**Two modes:**

| Mode | Condition | Behavior |
|------|-----------|----------|
| **Initial Generation** (iteration 1) | `best_reward_code` is empty | Generate novel candidates from scratch |
| **Iterative Improvement** | `best_reward_code` exists | Generate improved versions based on best + feedback |

#### Step 3.2: Feedback Block Structure (Lines 31-72)

For iterative mode, includes:

1. **Policy Results JSON** - All candidate evaluation metrics
2. **Reflection** - LLM analysis + human feedback
3. **Critical Instructions** - How to use the feedback:
   - Only use BEST reward as base
   - Learn from worse candidate's failures
   - Follow `recommended_edits` and `prompt_seed` from reflection
   - Balance speed vs stability

#### Step 3.3: Complete Prompt Assembly (Lines 83-136)

Returns a formatted prompt containing:

| Section | Content |
|---------|---------|
| Instruction block | Improvement or initial generation directives |
| Format rules | Plain Python, no markdown, specific delimiter |
| Task spec | JSON task description |
| Environment code | Brax environment source |
| Best reward so far | Previous best candidate (if exists) |
| Query with feedback | Results + reflection (if iteration > 1) |
| Example output | Template showing correct format |

---

### 4. **Class: `RewardDesignerOpenAIAgent` (Lines 139-244)**

#### Step 4.1: Initialization (Lines 140-144)

```python
class RewardDesignerOpenAIAgent(BaseAgent):
    _model: str = PrivateAttr()

    def __init__(self, model="gpt-4o-mini", **kwargs):
        super().__init__(name="RewardDesignerOpenAIAgent", **kwargs)
        self._model = model
```

- `_model` is a private attribute (not serialized in state)
- Default model: `gpt-4o-mini`

#### Step 4.2: Main Execution Method (Lines 146-244)

```python
async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
```

**Step 4.2.1: Extract Session State (Lines 147-151)**
```python
iteration = ctx.session.state.get("iteration", 1)
best_reward_code = ctx.session.state.get("best_reward_code", "")
reflection = ctx.session.state.get("reflection", "")
K = ctx.session.state["K"]
```

| Key | Source | Default |
|-----|--------|---------|
| `iteration` | IncrementIterationAgent | 1 |
| `best_reward_code` | SelectorAgent | "" |
| `reflection` | RewardReflectorOpenAIAgent | "" |
| `K` | config (SetupAgent) | required |

**Step 4.2.2: Detailed Logging (Lines 152-198)**

Logs all inputs for debugging:
- Task specification (name, objective, constraints)
- Environment code (first 10 lines)
- Best reward code preview (first 5 lines)
- Complete reflection text

**Step 4.2.3: Get Candidate Results for Iteration > 1 (Lines 200-203)**
```python
candidate_results = None
if iteration > 1:
    candidate_results = ctx.session.state.get("candidate_results", None)
```

Only includes feedback from iteration 2 onward.

**Step 4.2.4: Build Prompt (Lines 205-212)**
```python
prompt = _designer_prompt(
    ctx.session.state["task_spec"],
    ctx.session.state["env_code"],
    best_reward_code,
    reflection,
    K,
    candidate_results=candidate_results,
)
```

**Step 4.2.5: LLM Call with Retry (Lines 214-230)**
```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((Exception,)),
    reraise=True
)
def call_llm():
    return client.chat.completions.create(
        model=self._model,
        messages=[
            {"role": "system", "content": DESIGNER_SYSTEM},
            {"role": "user", "content": prompt},
        ],
        temperature=0.4,
    )
```

**Retry policy:**
- Max 3 attempts
- Exponential backoff: 2s → 4s → 10s max
- Temperature 0.4 for balanced creativity

**Step 4.2.6: Store Result (Lines 232-243)**
```python
resp = call_llm()
generated_text = resp.choices[0].message.content
ctx.session.state["reward_candidates_text"] = generated_text

candidate_count = generated_text.count(CANDIDATE_DELIM) + 1
logger.info(f"[RewardDesignerOpenAIAgent] Generated {candidate_count} reward candidate(s)")
```

- Stores raw LLM response in `reward_candidates_text`
- Counts candidates by delimiter occurrences

---

### 5. **Class: `RewardReflectorOpenAIAgent` (Lines 247-400)**

This agent analyzes evaluation results and provides structured feedback.

#### Step 5.1: Initialization (Lines 248-252)

```python
class RewardReflectorOpenAIAgent(BaseAgent):
    _model: str = PrivateAttr()

    def __init__(self, model="gpt-4o-mini", **kwargs):
        super().__init__(name="RewardReflectorOpenAIAgent", **kwargs)
        self._model = model
```

#### Step 5.2: Main Execution (Lines 254-400)

**Step 5.2.1: Extract State & Validate (Lines 255-266)**
```python
iteration = ctx.session.state.get("iteration", 1)
task_spec = ctx.session.state["task_spec"]
candidate_results = ctx.session.state.get("candidate_results", "")
best_candidate_index = ctx.session.state.get("best_candidate_index", 0)

if not candidate_results:
    logger.warning("[RewardReflectorOpenAIAgent] No candidate_results found...")
    ctx.session.state["reflection"] = "No candidate results available for reflection (first iteration)."
    yield Event(author=self.name, content=None)
    return
```

- Skips reflection on first iteration (no results yet)
- Returns early with placeholder reflection

**Step 5.2.2: Build Reflection Prompt (Lines 272-367)**

The prompt instructs the LLM to analyze:

| Metric | Analysis Focus |
|--------|----------------|
| **Forward Velocity** | Direction, magnitude, stability correlation |
| **Stability/Balance** | Upright posture, falling signs, speed-stability tradeoff |
| **Distance Traveled** | Progress vs episode length |
| **Control Smoothness** | Energy efficiency, action quality |
| **Running Reward** | Forward motion reward component |
| **Episode Length** | Early termination (falling) |
| **Overall Score** | best vs worse candidate comparisons |
| **Reward Code** | Term analysis, numerical stability |

**Expected Output Structure:**
```json
{
  "what_worked": ["..."],
  "strengths": ["..."],
  "what_failed": ["..."],
  "weaknesses": ["..."],
  "diagnosis": "...",
  "recommended_edits": ["..."],
  "prompt_seed": "..."
}
```

**Step 5.2.3: LLM Call with Retry (Lines 369-382)**
```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((Exception,)),
    reraise=True
)
def call_llm():
    return client.chat.completions.create(
        model=self._model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,  # Lower for more deterministic analysis
    )
```

**Lower temperature (0.2)** for more consistent analysis output.

**Step 5.2.4: Store & Log Reflection (Lines 384-399)**
```python
reflection_text = resp.choices[0].message.content
ctx.session.state["reflection"] = reflection_text

# Log complete reflection
logger.info("=" * 80)
logger.info("[RewardReflectorOpenAIAgent] COMPLETE REFLECTION:")
logger.info("=" * 80)
for line in reflection_text.split('\n'):
    logger.info(line)
```

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Session State                                │
├─────────────────────────────────────────────────────────────────────┤
│ Inputs for RewardDesignerOpenAIAgent:                                │
│   - iteration, K, task_spec, env_code                                │
│   - best_reward_code (from SelectorAgent)                           │
│   - reflection (from RewardReflectorOpenAIAgent - prev iteration)   │
│   - candidate_results (from CandidateEvaluatorAgent - prev iter)   │
├─────────────────────────────────────────────────────────────────────┤
│ Outputs:                                                             │
│   - reward_candidates_text → parsed by CandidateEvaluatorAgent      │
│   - reflection → used by next iteration's RewardDesignerOpenAIAgent │
└─────────────────────────────────────────────────────────────────────┘

Iteration Flow:
┌──────────────────┐
│ SetupAgent       │ → K, task_spec, env_code
└────────┬─────────┘
         ▼
┌──────────────────────────────────────────────────────────────────────┐
│                          LoopAgent                                    │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │ RewardDesignerOpenAIAgent                                        │  │
│  │   - Generates K candidates using LLM                            │  │
│  │   - Uses reflection + best_reward_code from PREVIOUS iteration  │  │
│  │   - Outputs: reward_candidates_text                              │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                          ↓                                            │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │ CandidateEvaluatorAgent                                          │  │
│  │   - Parses candidates, trains policies, evaluates               │  │
│  │   - Outputs: candidate_results (JSON)                            │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                          ↓                                            │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │ SelectorAgent                                                    │  │
│  │   - Picks best candidate by score                                │  │
│  │   - Outputs: best_reward_code, best_candidate_index              │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                          ↓                                            │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │ RewardReflectorOpenAIAgent                                       │  │
│  │   - Analyzes ALL candidates using LLM                            │  │
│  │   - Compares best vs worse                                       │  │
│  │   - Outputs: reflection (JSON with recommendations)               │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                          ↓                                            │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │ HumanReflectionAgent (optional)                                  │  │
│  │   - Human reviews, adds feedback                                 │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                          ↓                                            │
│  ... ExitCheckerAgent, IncrementIterationAgent ...                   │
│                          ↓                                            │
│  [NEXT ITERATION: RewardDesigner uses reflection from ↑]             │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Key Design Patterns

| Pattern | Implementation |
|---------|----------------|
| **Retry with Exponential Backoff** | `tenacity` decorator for LLM API resilience |
| **Temperature Control** | Designer (0.4) for creativity, Reflector (0.2) for consistency |
| **State Isolation** | Private model attribute, stateless agent logic |
| **Defensive Defaults** | `.get()` with defaults for optional state keys |
| **Comprehensive Logging** | INFO for key events, DEBUG for details, structured multi-line output |

---

