# reward_loop.py detailed explanation

**Session ID:** ses_2faa55e7affeUewAfvOsL6wdd6
**Created:** 3/19/2026, 5:08:38 PM
**Updated:** 3/20/2026, 4:16:11 PM

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

## User

Explain in details and step by step about @eureka_loop\agents\evaluator_agent.py 

---

## Assistant (Plan · glm-5 · 106.4s)

_Thinking:_

The user wants a detailed, step-by-step explanation of the `evaluator_agent.py` file. This is a comprehensive agent that handles the evaluation of reward function candidates. Let me provide a thorough breakdown.

## Overview

`evaluator_agent.py` implements **CandidateEvaluatorAgent** - the execution engine that trains and evaluates RL policies for each reward function candidate generated by the LLM. This is the computationally intensive core of the Eureka-like system.

---

## Step-by-Step Breakdown

### 1. **Imports (Lines 1-15)**

```python
from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from typing import AsyncGenerator
import json
import re
from pathlib import Path
from pydantic import PrivateAttr

from loguru import logger

from ..tools.reward_sandbox import compile_reward
from ..tools.rl_runner import train_policy, evaluate_policy, save_policy_rollout_html
from ..tools.scoring import score_candidate
from ..tools.artifacts import candidate_dir, save_text, save_json, append_leaderboard, save_policy_params
```

| Import | Purpose |
|--------|---------|
| `BaseAgent`, `InvocationContext`, `Event` | ADK agent framework |
| `compile_reward` | Validates & compiles reward function code |
| `train_policy`, `evaluate_policy`, `save_policy_rollout_html` | RL training/evaluation pipeline |
| `score_candidate` | Computes aggregate score from metrics |
| `artifacts` | File I/O utilities for outputs |

---

### 2. **Class Definition & Initialization (Lines 17-22)**

```python
class CandidateEvaluatorAgent(BaseAgent):
    _outdir: Path = PrivateAttr()
    _leaderboard_path: Path = PrivateAttr()

    def __init__(self, **kwargs):
        super().__init__(name="CandidateEvaluatorAgent", **kwargs)
```

- `_outdir` - Base output directory for artifacts
- `_leaderboard_path` - Path to shared leaderboard CSV
- Both are `PrivateAttr` (not serialized, instance-specific)

---

### 3. **Main Execution: `_run_async_impl` (Lines 24-281)**

#### Step 3.1: Extract Configuration (Lines 25-32)

```python
iteration = ctx.session.state["iteration"]
env_name = ctx.session.state["env_name"]
train_steps = ctx.session.state["train_steps"]
seed = ctx.session.state["seed"]
K = ctx.session.state["K"]

self._outdir = Path(ctx.session.state["outdir"])
self._leaderboard_path = Path(ctx.session.state["leaderboard_path"])

text = ctx.session.state["reward_candidates_text"]
```

| Key | Source | Purpose |
|-----|--------|---------|
| `iteration` | IncrementIterationAgent | Current loop iteration |
| `env_name` | SetupAgent | Brax environment name |
| `train_steps` | config | Number of training steps |
| `seed` | config | Random seed base |
| `K` | config | Number of candidates |
| `reward_candidates_text` | RewardDesignerOpenAIAgent | Raw LLM output |

---

#### Step 3.2: Parse LLM Output (Lines 36-63)

**Step 3.2.1: Clean Markdown (Lines 36-43)**
```python
# Remove ```python ... ``` blocks
text = re.sub(r'```python\s*\n(.*?)\n```', r'\1', text, flags=re.DOTALL)
# Remove ``` ... ``` blocks (generic)
text = re.sub(r'```\s*\n(.*?)\n```', r'\1', text, flags=re.DOTALL)
# Remove inline code backticks
text = text.replace('`', '')
```

LLMs often wrap code in markdown backticks - this strips them.

**Step 3.2.2: Split by Delimiter (Lines 44-61)**
```python
parts = text.split("### CANDIDATE ###")

candidates = []
for p in parts:
    p = p.strip()
    if "def compute_reward" in p:
        # Extract function boundaries
        func_match = re.search(r'def compute_reward.*?(?=\ndef [a-zA-Z_]|\Z)', p, re.DOTALL)
        if func_match:
            candidates.append(func_match.group(0).strip())
        else:
            candidates.append(p)
```

**Parsing logic:**
1. Split text by `### CANDIDATE ###` delimiter
2. For each section, locate `def compute_reward`
3. Extract from function start to next `def` or end of string
4. Truncate to K candidates

**Step 3.2.3: Limit to K Candidates (Line 63)**
```python
candidates = candidates[:K]
```

---

#### Step 3.3: Handle No Candidates Case (Lines 67-78)

```python
if not candidates:
    iterdir = self._outdir / f"iteration_{iteration:03d}"
    iterdir.mkdir(parents=True, exist_ok=True)
    (iterdir / "raw_llm_output.txt").write_text(text)
    ctx.session.state["candidate_results"] = "[]"
    ctx.session.state["llm_output_error"] = "No valid reward candidates parsed..."
    yield Event(author=self.name, content=None)
    return
```

**Error handling:**
- Creates iteration directory
- Saves raw LLM output for debugging
- Sets empty results + error message
- Returns early (no evaluation)

---

#### Step 3.4: Candidate Evaluation Loop (Lines 81-186)

For each candidate (1 to K):

**Step 3.4.1: Setup Output Directory (Lines 83-86)**
```python
cdir = candidate_dir(self._outdir, iteration, i)
save_text(cdir / "reward.py", code)
logger.info(f"[CandidateEvaluatorAgent] Evaluating candidate {i}/{len(candidates)}")
```

Always saves the code, even if evaluation fails later.

**Step 3.4.2: Compile Reward Function (Lines 88-90)**
```python
reward_fn = compile_reward(code)
logger.debug(f"[CandidateEvaluatorAgent] Candidate {i}: Reward function compiled successfully")
```

`compile_reward` validates:
- No forbidden imports
- `compute_reward` function exists
- Returns `(scalar, dict)` tuple
- No `None` returns

**Step 3.4.3: Clear JAX Cache (Lines 94-106)**
```python
import jax
if hasattr(jax, 'clear_caches'):
    jax.clear_caches()
elif hasattr(jax.extend, 'backend') and hasattr(jax.extend.backend, 'clear_backends'):
    jax.extend.backend.clear_backends()
```

Memory management to prevent accumulation across candidates.

**Step 3.4.4: Train Policy (Lines 108-111)**
```python
make_inf, params, train_metrics, network_config = train_policy(
    env_name, reward_fn, seed + i, train_steps,
    episode_length=ctx.session.state["eval_horizon"]
)
```

Returns:
| Value | Description |
|-------|-------------|
| `make_inf` | Inference function factory |
| `params` | Trained policy parameters |
| `train_metrics` | Training statistics |
| `network_config` | Network architecture info |

**Step 3.4.5: Evaluate Policy (Lines 113-120)**
```python
eval_metrics = evaluate_policy(
    env_name, reward_fn, make_inf, params, seed + i,
    ctx.session.state["eval_episodes"],
    ctx.session.state["eval_horizon"]
)
score = score_candidate(eval_metrics)
```

- Runs policy for multiple episodes
- Computes average return and behavioral metrics
- Calls `score_candidate()` for aggregate score

**Step 3.4.6: Render HTML Visualization (Lines 123-141)**
```python
video_horizon = min(400, ctx.session.state["eval_horizon"])

try:
    save_policy_rollout_html(
        out_dir=cdir, env_name=env_name, reward_fn=reward_fn,
        make_inference_fn=make_inf, params=params,
        seed=seed + i, horizon=video_horizon,
    )
except Exception as render_err:
    logger.warning(f"[CandidateEvaluatorAgent] Candidate {i}: HTML viewer rendering failed...")
```

- Creates interactive 3D animation
- Non-critical failure (continues if rendering fails)

**Step 3.4.7: Save Artifacts (Lines 143-173)**
```python
save_json(cdir / "train_metrics.json", train_metrics)
save_json(cdir / "eval_metrics.json", eval_metrics)
save_json(cdir / "score.json", {"score": score})

save_json(cdir / "training_metadata.json", {
    "seed": seed + i,
    "train_steps": train_steps,
    "episode_length": ctx.session.state["eval_horizon"],
    "env_name": env_name,
    "network_config": network_config,
    "note": "To regenerate visualizations: Use recreate_inference_fn()..."
})

save_policy_params(cdir / "policy_params.pkl", params)
```

**Artifacts saved:**

| File | Content |
|------|---------|
| `reward.py` | Reward function source code |
| `train_metrics.json` | Training statistics |
| `eval_metrics.json` | Evaluation metrics |
| `score.json` | Aggregate score |
| `training_metadata.json` | Config for regeneration |
| `policy_params.pkl` | Trained policy parameters |
| `rollout.html` | Interactive visualization |

**Step 3.4.8: Update Leaderboard (Line 174)**
```python
append_leaderboard(self._leaderboard_path, iteration, i, score, eval_metrics["avg_return"], str(cdir))
```

**Step 3.4.9: Store Result (Lines 178-185)**
```python
results.append({
    "candidate": i,
    "score": score,
    "eval": eval_metrics,
    "train_metrics": train_metrics,
    "artifact_dir": str(cdir),
    "reward_code": code
})
```

---

#### Step 3.5: Error Handling for Each Candidate (Lines 187-214)

```python
except Exception as e:
    error_msg = str(e)
    error_type = type(e).__name__
    error_summary.append(f"Candidate {i}: {error_type}: {error_msg}")
    
    # Save detailed error information
    error_details = f"""Candidate {i} Evaluation Failed
    
Error Type: {error_type}
Error Message: {error_msg}

Reward Code:
{code}

Common Issues:
- Missing return statement...
- None values...
- Wrong return format...
- Syntax errors...
"""
    save_text(cdir / "error.txt", error_details)
    append_leaderboard(self._leaderboard_path, iteration, i, -999, -999, str(cdir))
```

**Error handling:**
- Logs error type and message
- Saves detailed error file with context
- Records -999 score in leaderboard
- Continues to next candidate (doesn't fail the whole loop)

---

#### Step 3.6: Post-Loop Summary (Lines 216-221)

```python
if not results and error_summary:
    ctx.session.state["evaluation_errors"] = "\n".join(error_summary)
    logger.error(f"[CandidateEvaluatorAgent] All {len(candidates)} candidates failed!")
elif results:
    logger.info(f"[CandidateEvaluatorAgent] Successfully evaluated {len(results)}/{len(candidates)} candidates")
```

---

#### Step 3.7: JSON Serialization Helper (Lines 223-276)**

```python
def convert_to_json_serializable(obj):
    """Recursively convert objects to JSON-serializable format."""
    import numpy as np
    
    # Handle None and basic types
    if obj is None or isinstance(obj, (int, float, str, bool)):
        return obj
    
    # Try to convert array-like objects (JAX arrays, numpy arrays)
    try:
        if hasattr(obj, 'shape') or hasattr(obj, '__array__'):
            np_array = np.asarray(obj)
            if np_array.size == 1:
                return float(np_array.item()) if np.issubdtype(np_array.dtype, np.floating) else int(np_array.item())
            else:
                return np_array.tolist()
    except (TypeError, ValueError, AttributeError):
        pass
    
    # Handle collections - recursively convert
    if isinstance(obj, dict):
        return {k: convert_to_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [convert_to_json_serializable(item) for item in obj]
    
    # Fallback to string representation
    return str(obj)
```

**Why needed:**
- JAX returns `DeviceArray` / `Array` objects
- NumPy returns `ndarray` scalars
- JSON can't serialize these natively

**Conversion logic:**

| Input Type | Output |
|------------|--------|
| Python primitives | Pass through |
| JAX Array (scalar) | `int` or `float` |
| JAX/NumPy Array (multi) | Python `list` |
| Dict | Recursively convert values |
| List/Tuple | Recursively convert items |
| Unknown | `str()` representation |

---

#### Step 3.8: Store Results (Lines 278-281)

```python
serializable_results = convert_to_json_serializable(results)
ctx.session.state["candidate_results"] = json.dumps(serializable_results, indent=2)
yield Event(author=self.name, content=None)
```

- Converts all JAX/NumPy arrays to JSON-safe types
- Stores as JSON string in session state
- Signals completion via `Event`

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Input Session State                               │
├─────────────────────────────────────────────────────────────────────────┤
│ reward_candidates_text: "def compute_reward(...)" (raw LLM output)       │
│ iteration: 1, K: 2, env_name: "halfcheetah", train_steps: 200000        │
│ seed: 0, eval_episodes: 1, eval_horizon: 1000                            │
│ outdir: "outputs/run_20240115_143052"                                    │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     CandidateEvaluatorAgent                              │
│  ┌─────────────────────────────────────────────────────────────────┐     │
│  │ 1. Parse LLM Output                                             │     │
│  │    - Strip markdown backticks                                   │     │
│  │    - Split by "### CANDIDATE ###"                               │     │
│  │    - Extract compute_reward functions                           │     │
│  └─────────────────────────────────────────────────────────────────┘     │
│                              │                                          │
│                              ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────┐     │
│  │ 2. For Each Candidate (K):                                      │     │
│  │    ┌───────────────────────────────────────────────────────────┐ │     │
│  │    │ a. Save reward.py                                        │ │     │
│  │    │ b. compile_reward(code) → validate                       │ │     │
│  │    │ c. train_policy() → params, train_metrics, network_config │ │     │
│  │    │ d. evaluate_policy() → eval_metrics                      │ │     │
│  │    │ e. score_candidate() → score                             │ │     │
│  │    │ f. save_policy_rollout_html() → rollback.html             │ │     │
│  │    │ g. Save JSON artifacts                                    │ │     │
│  │    │ h. append_leaderboard()                                   │ │     │
│  │    └───────────────────────────────────────────────────────────┘ │     │
│  └─────────────────────────────────────────────────────────────────┘     │
│                              │                                          │
│                              ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────┐     │
│  │ 3. Convert to JSON-serializable (handle JAX/NumPy arrays)       │     │
│  └─────────────────────────────────────────────────────────────────┘     │
│                              │                                          │
│                              ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────┐     │
│  │ 4. Store candidate_results in session state                      │     │
│  └─────────────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       Output Session State                               │
├─────────────────────────────────────────────────────────────────────────┤
│ candidate_results: '[                                                    │
│   {"candidate": 1, "score": 125.5, "eval": {...}, "reward_code": "..."}, │
│   {"candidate": 2, "score": 98.2, "eval": {...}, "reward_code": "..."}   │
│ ]'                                                                       │
│ (or "evaluation_errors" if all failed)                                  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Output Artifacts Structure

```
outputs/run_YYYYMMDD_HHMMSS/
├── iteration_001/
│   ├── candidate_001/
│   │   ├── reward.py              # Reward function source
│   │   ├── train_metrics.json     # Training statistics
│   │   ├── eval_metrics.json      # Evaluation metrics
│   │   ├── score.json             # Aggregate score
│   │   ├── training_metadata.json # Config for regeneration
│   │   ├── policy_params.pkl      # Trained parameters
│   │   ├── rollout.html           # Interactive 3D visualization
│   │   └── error.txt              # (if failed)
│   └── candidate_002/
│       └── ...
├── iteration_002/
│   └── ...
└── leaderboard.csv                 # Score tracking across iterations
```

---

## Key Design Patterns

| Pattern | Implementation |
|---------|----------------|
| **Graceful Degradation** | Individual candidate failure doesn't break the loop |
| **Defensive Parsing** | Multiple regex patterns to extract functions |
| **Memory Management** | JAX cache clearing between candidates |
| **Type Conversion** | Recursive serializer for JAX/NumPy arrays |
| **Comprehensive Artifacts** | All intermediate results saved for debugging |
| **Leaderboard Persistence** | CSV for cross-iteration tracking |

---

## User

Can you tell me what is "Brax environment name"

---

## Assistant (Plan · glm-5 · 7.4s)

_Thinking:_

The user is asking about "Brax environment name" which I saw referenced in the evaluator_agent.py file. This refers to the Brax physics/RL library. Let me explain what this is.

Brax is a differentiable physics engine and reinforcement learning library developed by Google Research. The "environment name" refers to specific RL tasks/environments available in Brax, similar to how OpenAI Gym has environments like "CartPole-v1" or "HalfCheetah-v4".

Let me search for more context in the codebase to give a completeanswer.

**Brax** is a Google Research library for differentiable physics simulation and reinforcement learning. The "environment name" refers to specific RL tasks (and the current config shows `"halfcheetah"`).

Let me check what environments are available in yoursetup:

**Tool: grep**

**Input:**
```json
{
  "pattern": "halfcheetah|ant|humanoid|hopper|walker|fetch|ur5e|reacher|pusher",
  "path": "C:\\Projects\\AgenticSystemDesign\\source\\configs"
}
```

**Output:**
```
Found 1 matches
C:\Projects\AgenticSystemDesign\source\configs\loop_config.yaml:
  Line 1: env_name: "halfcheetah"
```

**Tool: read**

**Input:**
```json
{
  "filePath": "C:\\Projects\\AgenticSystemDesign\\source\\configs\\loop_config.yaml"
}
```

**Output:**
```
<path>C:\Projects\AgenticSystemDesign\source\configs\loop_config.yaml</path>
<type>file</type>
<content>1: env_name: "halfcheetah"
2: iterations: 5
3: candidates_per_iteration: 2
4: train_steps: 200000
5: seed: 0
6: 
7: llm_provider: "openai"
8: 
9: # Early-exit criteria (threshold + plateau)
10: return_threshold: 2500
11: plateau_delta: 100
12: plateau_patience: 2
13: 
14: # Note: Rollout visualizations are saved as interactive HTML viewers (rollout.html)
15: # The HTML viewer provides an interactive 3D animation that can be played, paused,
16: # scrubbed, and rotated - no MP4 needed!

(End of file - total 16 lines)
</content>
```

---

## Assistant (Plan · glm-5 · 2.1s)

_Thinking:_

Now let me check the brax_env.py tool to see how environments are used and what'savailable.

**Tool: read**

**Input:**
```json
{
  "filePath": "C:\\Projects\\AgenticSystemDesign\\source\\eureka_loop\\tools\\brax_env.py"
}
```

**Output:**
```
<path>C:\Projects\AgenticSystemDesign\source\eureka_loop\tools\brax_env.py</path>
<type>file</type>
<content>1: import inspect
2: from brax.envs import create
3: 
4: def get_env_and_source(env_name: str):
5:     env = create(env_name)
6:     mod = inspect.getmodule(env.__class__)
7:     env_source = inspect.getsource(mod)
8:     return env, env_source, mod.__name__

(End of file - total 8 lines)
</content>
```

---

## Assistant (Plan · glm-5 · 32.8s)

_Thinking:_

Now I have a good understanding. Let me provide a comprehensive answer about Brax environments.

## Brax Environment Name

**Brax** is a differentiable physics engine and RL library by Google Research. The "environment name" identifies specific RL tasks.

### What is a Brax Environment?

A Brax environment is a physics-based simulation where an RL agent learns to control a simulated body/robot. Each environment has:

| Component | Description |
|-----------|-------------|
| **Observation space** | What the agent "sees" (joint angles, velocities, positions) |
| **Action space** | What the agent can control (joint torques) |
| **Reward signal** | Feedback for learning (default, replaced by your custom reward) |
| **Physics model** | Body structure, joints, contacts |

### Your Current Configuration

```yaml
# configs/loop_config.yaml
env_name: "halfcheetah"
```

### Common Brax Environments

| Environment Name | Description | Body Type |
|------------------|-------------|-----------|
| `halfcheetah` | 6-legged runner, move forward | Planar cheetah |
| `ant` | 4-legged quadruped, move forward | 3D ant |
| `humanoid` | Bipedal humanoid, walk/run | 3D humanoid |
| `hopper` | One-legged hopper, hop forward | Planar hopper |
| `walker2d` | 2-legged walker, walk forward | Planar walker |
| `fetch` | Robot arm reach/manipulate | 3D manipulator |
| `ur5e` | UR5e robot arm | 3D manipulator |
| `reacher` | 2-link arm reach target | Planar arm |
| `pusher` | Push object to target | 3D manipulator |

### How It Works in YourSystem

```
┌─────────────────────────────────────────────────────────────┐
│ config: env_name: "halfcheetah"                            │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ SetupAgent: Loads env_code (source) via brax_env.py        │
│   env, env_source, mod_name = get_env_and_source("halfcheetah")│
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ RewardDesignerOpenAIAgent: Receives env_code as context    │
│   - LLM sees environment structure to design rewards        │
│   - Understands observation dimensions, body parts          │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ CandidateEvaluatorAgent:                                   │
│   train_policy(env_name, reward_fn, ...)                   │
│   evaluate_policy(env_name, reward_fn, ...)                 │
└─────────────────────────────────────────────────────────────┘
```

### Why Eureka Needs Environment Info

The LLM uses `env_code` (the Brax environment source) to understand:

1. **Observation indices** - e.g., `obs[..., 8]` is forward velocity in halfcheetah
2. **Body structure** - which joints exist, their limits
3. **Action dimensions** - how many control inputs
4. **Physics properties** - mass, geometry, contacts

This allows the LLM to generate reward functions that use the correct observation indices for velocity, position, angles, etc.

---

## User

Explain in details and step by step about @eureka_loop\agents\increment_iteration_agent.py 

---

## Assistant (Plan · glm-5 · 60.6s)

_Thinking:_

The user wants a detailed explanation of `increment_iteration_agent.py`. This is a simple agent that increments the iteration counter. Let me provide a comprehensive step-by-step breakdown.

## Overview

`increment_iteration_agent.py` implements **IncrementIterationAgent** - the final agent in the loop that increments the iteration counter. It's a simple but critical component that enables the iterative improvement cycle.

---

## Step-by-Step Breakdown

### 1. **Imports (Lines 1-5)**

```python
from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from typing import AsyncGenerator
from loguru import logger
```

| Import | Purpose |
|--------|---------|
| `BaseAgent` | Parent class for ADK agents |
| `InvocationContext` | Session state access |
| `Event` | Completion signal |
| `AsyncGenerator` | Return type annotation |
| `logger` | Structured logging |

---

### 2. **Class Definition (Line 7)**

```python
class IncrementIterationAgent(BaseAgent):
```

- Minimal agent - no configuration or state needed
- No `__init__` override required (uses default)

---

### 3. **Main Execution: `_run_async_impl` (Lines 8-24)**

#### Step 3.1: Read Current Iteration (Line 9)

```python
old_iteration = ctx.session.state.get("iteration", 1)
```

- Gets current iteration from session state
- Defaults to `1` if not set (first iteration)

#### Step 3.2: Increment and Store (Lines 10-11)

```python
new_iteration = old_iteration + 1
ctx.session.state["iteration"] = new_iteration
```

- Adds 1 to current iteration
- Stores updated value back to session state

#### Step 3.3: Retrieve Persistent State (Lines 13-16)

```python
best_reward_code = ctx.session.state.get("best_reward_code", "")
reflection = ctx.session.state.get("reflection", "")
best_return = ctx.session.state.get("best_return", None)
```

These values **persist across iterations** and are used by the next iteration's `RewardDesignerOpenAIAgent`:

| Key | Purpose in Next Iteration |
|-----|--------------------------|
| `best_reward_code` | Base for generating improved candidates |
| `reflection` | LLM analysis + improvement suggestions |
| `best_return` | Used by `ExitCheckerAgent` for termination |

#### Step 3.4: Log State Transition (Lines 18-22)

```python
logger.info(f"[IncrementIterationAgent] Incrementing iteration: {old_iteration} -> {new_iteration}")
logger.info(f"[IncrementIterationAgent] State for next iteration:")
logger.info(f"  - best_reward_code: {'SET' if best_reward_code else 'EMPTY'} ({len(best_reward_code)} chars)")
logger.info(f"  - reflection: {'SET' if reflection else 'EMPTY'} ({len(reflection)} chars)")
logger.info(f"  - best_return: {best_return}")
```

**Why log here?**
- Confirms state is correctly preserved
- Helps debug if next iteration receives wrong data
- Shows char counts to detect empty/truncated values

#### Step 3.5: Signal Completion (Line 24)

```python
yield Event(author=self.name, content=None)
```

Yields control back to `LoopAgent` for next iteration or exit.

---

## Position in Loop Agent Order

From `reward_loop.py`:

```python
LoopAgent(
    name="RewardEvolutionLoop",
    sub_agents=[
        RewardDesignerOpenAIAgent(model=model),      # 1. Generate candidates
        CandidateEvaluatorAgent(),                     # 2. Train & evaluate
        SelectorAgent(name="SelectorAgent"),          # 3. Pick best
        RewardReflectorOpenAIAgent(model=model),      # 4. Analyze & reflect
        HumanReflectionAgent(name="HumanReflectionAgent"),  # 5. Human feedback
        ExitCheckerAgent(name="ExitCheckerAgent"),    # 6. Check termination
        IncrementIterationAgent(name="..."),          # 7. Increment counter
    ],
    max_iterations=loop_cfg["iterations"]
)
```

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                 Session State (Before Increment)                     │
├─────────────────────────────────────────────────────────────────────┤
│ iteration: 1                                                         │
│ best_reward_code: "def compute_reward(obs, action, ...)"            │
│ reflection: "{ \"what_worked\": [...], \"recommended_edits\": ... }" │
│ best_return: 2345.67                                                 │
│ candidate_results: "[{...}, {...}]"                                  │
│ best_candidate_index: 0                                               │
└────────────────────────────────────┬────────────────────────────────┘
                                     │
                                     ▼
                      ┌──────────────────────────┐
                      │  IncrementIterationAgent  │
                      │                           │
                      │  1. Read iteration: 1     │
                      │  2. Increment to: 2       │
                      │  3. Store: iteration = 2  │
                      │  4. Log persistent state │
                      │  5. Return Event         │
                      └──────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────┐
│                 Session State (After Increment)                       │
├─────────────────────────────────────────────────────────────────────┤
│ iteration: 2  ← CHANGED                                              │
│ best_reward_code: "def compute_reward(obs, action, ...)"  ← PRESERVED│
│ reflection: "{ ... }"  ← PRESERVED                                  │
│ best_return: 2345.67  ← PRESERVED                                    │
│ candidate_results: "[...]"  ← Will be overwritten next iteration    │
│ best_candidate_index: 0  ← Will be overwritten next iteration        │
└─────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
              [LoopAgent checks: iteration <= max_iterations?]
                                     │
                                     ▼
                      [Next iteration: RewardDesignerOpenAIAgent]
                      Uses: iteration=2, best_reward_code, reflection
```

---

## Iteration Timeline

```
Iteration 1:  SetupAgent → LoopAgent starts
              └─ RewardDesigner → generates initial candidates (no best_reward_code)
              └─ Evaluator → trains policies
              └─ Selector → picks first best
              └─ Reflector → creates first reflection
              └─ HumanReflection → (optional)
              └─ ExitChecker → checks threshold
              └─ IncrementIteration → iteration becomes 2

Iteration 2:  LoopAgent continues
              └─ RewardDesigner → uses best_reward_code + reflection from iteration 1
              └─ Evaluator → trains policies
              └─ Selector → updates best
              └─ Reflector → updates reflection
              └─ HumanReflection → (optional)
              └─ ExitChecker → checks threshold
              └─ IncrementIteration → iteration becomes 3

...continues until max_iterations or exit condition...
```

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Position: Last in loop** | All other agents must complete before incrementing |
| **Default iteration = 1** | Graceful handling of missing initialization |
| **Log persistent state** | Debug visibility for state continuity bugs |
| **No __init__ needed** | Stateless agent - uses only session state |
| **No validation** | Assumes ExitChecker already decided to continue |

---

## User

Explain in details and step by step about @eureka_loop\agents\exit_checker_agent.py 

---

## Assistant (Plan · glm-5 · 9.1s)

_Thinking:_

The user wants a detailed explanation of `exit_checker_agent.py`. This agent is responsible for checking termination criteria to decide whether to continue the evolution loop or exit. Let me provide a comprehensive step-by-step breakdown.

I also notice there's a missing import for `logger` - that's a bug I should mention. Let me read the exit_tool.py to understand how the exit mechanismworks.

Let me also check the exit tool to give acomplete picture:

**Tool: read**

**Input:**
```json
{
  "filePath": "C:\\Projects\\AgenticSystemDesign\\source\\eureka_loop\\agents\\exit_tool.py"
}
```

**Output:**
```
<path>C:\Projects\AgenticSystemDesign\source\eureka_loop\agents\exit_tool.py</path>
<type>file</type>
<content>1: from google.adk.tools.tool_context import ToolContext
2: 
3: def exit_loop(tool_context: ToolContext):
4:     """Call to stop the LoopAgent when criteria is met."""
5:     print(f"[Tool Call] exit_loop triggered by {tool_context.agent_name}")
6:     tool_context.actions.escalate = True
7:     return {}

(End of file - total 7 lines)
</content>
```

---

## Assistant (Plan · glm-5 · 139.3s)

_Thinking:_

Now I have a complete picture. The exit mechanism uses `ToolContext.actions.escalate = True` to signal the LoopAgent to stop. Let me provide a comprehensive explanation.

## Overview

`exit_checker_agent.py` implements **ExitCheckerAgent** - the termination criteria evaluator for the reward evolution loop. It decides whether to continue evolving reward functions or exit early based on performance metrics.

---

## Step-by-Step Breakdown

### 1. **Imports (Lines 1-6)**

```python
from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from typing import AsyncGenerator
from google.adk.tools.tool_context import ToolContext
from .exit_tool import exit_loop
```

| Import | Purpose |
|--------|---------|
| `BaseAgent`, `InvocationContext`, `Event` | ADK agent framework |
| `ToolContext` | Mechanism to signal loop termination |
| `exit_loop` | Helper function that sets `escalate=True` |

---

### 2. **Class Definition (Line 8)**

```python
class ExitCheckerAgent(BaseAgent):
```

---

### 3. **Main Execution: `_run_async_impl` (Lines 9-57)**

#### Step 3.1: Get Best Return Value (Lines 10-13)

```python
best_return = ctx.session.state.get("best_return", None)
if best_return is None:
    yield Event(author=self.name, content=None)
    return
```

**Early exit if no best_return:**
- First iteration might not have results yet
- Or `SelectorAgent` failed to set `best_return`
- Returns without action - loop continues

---

#### Step 3.2: Load Configuration Parameters (Lines 15-17)

```python
threshold = ctx.session.state["return_threshold"]
delta = ctx.session.state["plateau_delta"]
patience = ctx.session.state["plateau_patience"]
```

| Parameter | From Config | Purpose |
|-----------|-------------|---------|
| `return_threshold` | `return_threshold: 2500` | Target performance to reach |
| `plateau_delta` | `plateau_delta: 100` | Minimum improvement to count as progress |
| `plateau_patience` | `plateau_patience: 2` | Max consecutive non-improvements before exit |

From your `configs/loop_config.yaml`:
```yaml
return_threshold: 2500
plateau_delta: 100
plateau_patience: 2
```

---

#### Step 3.3: Track Plateau Progress (Lines 19-28)

```python
prev = ctx.session.state.get("prev_best_return", None)

if prev is not None:
    improvement = best_return - prev
    if improvement < delta:
        ctx.session.state["plateau_count"] = ctx.session.state.get("plateau_count", 0) + 1
    else:
        ctx.session.state["plateau_count"] = 0

ctx.session.state["prev_best_return"] = best_return
plateau_count = ctx.session.state.get("plateau_count", 0)
```

**Plateau detection logic:**

| Scenario | Improvement | Action |
|----------|-------------|--------|
| `improvement >= delta` | Made progress | Reset `plateau_count = 0` |
| `improvement < delta` | No meaningful progress | Increment `plateau_count += 1` |
| `prev is None` | First iteration | Skip plateau check |

**Example:**
```
Iteration 1: best_return = 2000, prev = None     → plateau_count = 0
Iteration 2: best_return = 2100, prev = 2000     → improvement = 100 >= delta → plateau_count = 0
Iteration 3: best_return = 2150, prev = 2100     → improvement = 50 < delta   → plateau_count = 1
Iteration 4: best_return = 2180, prev = 2150     → improvement = 30 < delta   → plateau_count = 2 (exit!)
```

---

#### Step 3.4: Exit Decision Logic (Lines 31-48)

```python
should_exit = False
exit_reason = ""

if best_return >= threshold:
    if plateau_count >= patience:
        should_exit = True
        exit_reason = f"Reached threshold ({best_return:.2f} >= {threshold}) and plateaued..."
    elif best_return >= threshold * 1.1:  # 10% above threshold
        should_exit = True
        exit_reason = f"Significantly exceeded threshold ({best_return:.2f} >= {threshold * 1.1:.2f})"

elif plateau_count >= patience and best_return > 0:
    should_exit = True
    exit_reason = f"Performance plateaued ({plateau_count} >= {patience}) with return {best_return:.2f}"
```

**Exit Conditions (3 cases):**

| Condition | Threshold? | Plateaued? | Exit? | Reason |
|-----------|------------|------------|-------|--------|
| Threshold reached + plateaued | Yes | Yes (≥patience) | ✅ | Good performance, no more progress |
| Significantly exceeded threshold | Yes (≥1.1x) | No | ✅ | Strong performance, early exit |
| Plateaued with positive performance | No | Yes (≥patience) | ✅ | Stuck but positive, stop wasting resources |
| Below threshold, improving | No | No | ❌ | Continue searching |
| Below threshold, negative return | No | Yes | ❌ | Don't exit on bad performance |

**Why "positive performance" check?**
```python
elif plateau_count >= patience and best_return > 0:
```
- Prevents exiting when all candidates perform poorly (negative returns)
- Forces loop to continue trying to find something valid

---

#### Step 3.5: Execute Exit (Lines 50-55)

```python
if should_exit:
    logger.info(f"[ExitCheckerAgent] Exiting loop: {exit_reason}")
    tc = ToolContext(agent_name=self.name)
    exit_loop(tc)
    yield Event(author=self.name, actions=tc.actions)
    return

yield Event(author=self.name, content=None)
```

**Exit mechanism:**

```python
# exit_tool.py
def exit_loop(tool_context: ToolContext):
    tool_context.actions.escalate = True  # Signal to LoopAgent
    return {}
```

| Step | Action |
|------|--------|
| 1 | Create `ToolContext` with agent name |
| 2 | Call `exit_loop(tc)` → sets `tc.actions.escalate = True` |
| 3 | Yield `Event` with `actions=tc.actions` |
| 4 | `LoopAgent` sees `escalate=True` → stops looping |

**Continue case:**
- Yield empty `Event` (no actions)
- `LoopAgent` continues to next agent

---

### 4. **Bug Note**

The file is **missing the logger import**:

```python
# Line 51 uses logger but it's not imported
# Should have:
from loguru import logger
```

This would cause a `NameError` at runtime when `should_exit` is `True`.

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Session State (Input)                            │
├─────────────────────────────────────────────────────────────────────┤
│ best_return: 2450.5        (from SelectorAgent)                     │
│ return_threshold: 2500     (from config)                            │
│ plateau_delta: 100          (from config)                            │
│ plateau_patience: 2         (from config)                            │
│ prev_best_return: 2200.0   (from previous iteration)                │
│ plateau_count: 1            (from previous iteration)                │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ▼
                  ┌──────────────────────────────┐
                  │      ExitCheckerAgent        │
                  │                              │
                  │  ┌────────────────────────┐  │
                  │  │ 1. Get best_return     │  │
                  │  │    (2450.5)            │  │
                  │  └────────────────────────┘  │
                  │              │               │
                  │              ▼               │
                  │  ┌────────────────────────┐  │
                  │  │ 2. Load config:       │  │
                  │  │    threshold=2500      │  │
                  │  │    delta=100            │  │
                  │  │    patience=2           │  │
                  │  └────────────────────────┘  │
                  │              │               │
                  │              ▼               │
                  │  ┌────────────────────────┐  │
                  │  │ 3. Calculate plateau: │  │
                  │  │    improvement = 250   │  │
                  │  │    (2450.5 - 2200.0)    │  │
                  │  │    250 >= 100 → good   │  │
                  │  │    plateau_count = 0   │  │
                  │  └────────────────────────┘  │
                  │              │               │
                  │              ▼               │
                  │  ┌────────────────────────┐  │
                  │  │ 4. Check exit conditions│ │
                  │  │    best_return < 2500?  │ │
                  │  │    No plateau?          │ │
                  │  │    should_exit = FALSE │ │
                  │  └────────────────────────┘  │
                  │              │               │
                  │              ▼               │
                  │  ┌────────────────────────┐  │
                  │  │ 5. Update state:       │  │
                  │  │    prev_best_return    │  │
                  │  │    = 2450.5            │  │
                  │  │    plateau_count = 0   │  │
                  │  └────────────────────────┘  │
                  └──────────────┬───────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Session State (Output)                           │
├─────────────────────────────────────────────────────────────────────┤
│ prev_best_return: 2450.5   (updated)                               │
│ plateau_count: 0            (updated)                               │
│ (No escalate signal → loop continues)                               │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Exit Scenarios Example

### Scenario A: Threshold Reached + Plateaued
```
Config: threshold=2500, patience=2

Iter 1: best_return = 2400 → plateau_count = 0
Iter 2: best_return = 2500 → improvement = 100 >= delta → plateau_count = 0
Iter 3: best_return = 2520 → improvement = 20 < delta → plateau_count = 1
Iter 4: best_return = 2530 → improvement = 10 < delta → plateau_count = 2

Check: best_return (2530) >= threshold (2500) AND plateau_count (2) >= patience (2)
Result: EXIT - "Reached threshold and plateaued"
```

### Scenario B: Significantly Exceeded Threshold
```
Config: threshold=2500, patience=2

Iter 1: best_return = 2000 → plateau_count = 0
Iter 2: best_return = 2800 → improvement = 800

Check: best_return (2800) >= threshold * 1.1 (2750)
Result: EXIT - "Significantly exceeded threshold"
```

### Scenario C: Plateaued Below Threshold (Positive)
```
Config: threshold=2500, patience=2, best_return > 0 required

Iter 1: best_return = 1500 → plateau_count = 0
Iter 2: best_return = 1550 → improvement = 50 < delta → plateau_count = 1
Iter 3: best_return = 1580 → improvement = 30 < delta → plateau_count = 2

Check: plateau_count (2) >= patience (2) AND best_return (1580) > 0
Result: EXIT - "Performance plateaued with return 1580"
```

### Scenario D: Negative Performance (Don't Exit)
```
Config: threshold=2500, patience=2

Iter 1: best_return = -500 → plateau_count = 0
Iter 2: best_return = -600 → improvement = -100 < delta → plateau_count = 1
Iter 3: best_return = -700 → improvement = -100 < delta → plateau_count = 2

Check: plateau_count (2) >= patience (2) BUT best_return (-700) <= 0
Result: CONTINUE - Don't exit on negative performance
```

---

## Position in Loop Agent Order

```
Iteration N:
┌─────────────────────────────────────────────────────────────────┐
│ RewardDesignerOpenAIAgent     → Generate candidates            │
│ CandidateEvaluatorAgent       → Train & evaluate               │
│ SelectorAgent                 → Pick best                       │
│ RewardReflectorOpenAIAgent    → Analyze & reflect               │
│ HumanReflectionAgent          → Human feedback (optional)      │
│ ExitCheckerAgent              → Check termination ────────────┐│
│ IncrementIterationAgent       → Increment counter  ◄─────────┘│
└─────────────────────────────────────────────────────────────────┘
        │
        ▼
[If escalate=True] → Exit loop
[If escalate=False] → Continue to IncrementIterationAgent → Next iteration
```

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Three exit conditions** | Balance between early stopping and thorough search |
| **10% buffer for early exit** | Don't waste iterations if already well above threshold |
| **Positive return requirement** | Don't exit on broken/negative reward functions |
| **Reset plateau on improvement** | Only count consecutive non-improvements |
| **ToolContext for exit signal** | ADK pattern for loop control via `escalate` flag |

---

## User

What do I get from ToolContext(agent_name=self.name)?

---

## Assistant (Plan · glm-5 · 7.6s)

_Thinking:_

The user is asking about what `ToolContext(agent_name=self.name)` provides. Let me search for more information about ToolContext in the Google ADK framework to give a completeanswer.

**Tool: grep**

**Input:**
```json
{
  "pattern": "ToolContext",
  "path": "C:\\Projects\\AgenticSystemDesign\\source"
}
```

**Output:**
```
Found 13 matches
C:\Projects\AgenticSystemDesign\source\eureka_loop\agents\exit_checker_agent.py:
  Line 5: from google.adk.tools.tool_context import ToolContext   # Mechanism to signal loop termination
  Line 76:             tc = ToolContext(agent_name=self.name)

C:\Projects\AgenticSystemDesign\source\session-ses_2faa.md:
  Line 2181: <content>1: from google.adk.tools.tool_context import ToolContext
  Line 2183: 3: def exit_loop(tool_context: ToolContext):
  Line 2199: Now I have a complete picture. The exit mechanism uses `ToolContext.actions.escalate = True` to signal the LoopAgent to stop. Let me provide a comprehensive explanation.
  Line 2216: from google.adk.tools.tool_context import ToolContext
  Line 2223: | `ToolContext` | Mechanism to signal loop termination |
  Line 2354:     tc = ToolContext(agent_name=self.name)
  Line 2366: def exit_loop(tool_context: ToolContext):
  Line 2373: | 1 | Create `ToolContext` with agent name |
  Line 2548: | **ToolContext for exit signal** | ADK pattern for loop control via `escalate` flag |

C:\Projects\AgenticSystemDesign\source\eureka_loop\agents\exit_tool.py:
  Line 1: from google.adk.tools.tool_context import ToolContext
  Line 3: def exit_loop(tool_context: ToolContext):
```

**Tool: glob**

**Input:**
```json
{
  "pattern": "**/*.py",
  "path": "C:\\Projects\\AgenticSystemDesign\\source"
}
```

**Output:**
```
C:\Projects\AgenticSystemDesign\source\eureka_loop\agents\exit_checker_agent.py
C:\Projects\AgenticSystemDesign\source\eureka_loop\agents\increment_iteration_agent.py
C:\Projects\AgenticSystemDesign\source\eureka_loop\agents\evaluator_agent.py
C:\Projects\AgenticSystemDesign\source\eureka_loop\agents\llm_agents.py
C:\Projects\AgenticSystemDesign\source\eureka_loop\agents\selector_agent.py
C:\Projects\AgenticSystemDesign\source\eureka_loop\agents\reward_loop.py
C:\Projects\AgenticSystemDesign\source\eureka_loop\agents\setup_agent.py
C:\Projects\AgenticSystemDesign\source\eureka_loop\tools\scoring.py
C:\Projects\AgenticSystemDesign\source\eureka_loop\tools\rl_runner.py
C:\Projects\AgenticSystemDesign\source\eureka_loop\tools\reward_sandbox.py
C:\Projects\AgenticSystemDesign\source\eureka_loop\tools\regenerate_visualization.py
C:\Projects\AgenticSystemDesign\source\eureka_loop\tools\brax_env.py
C:\Projects\AgenticSystemDesign\source\eureka_loop\tools\artifacts.py
C:\Projects\AgenticSystemDesign\source\eureka_loop\agents\human_reflection_agent.py
C:\Projects\AgenticSystemDesign\source\eureka_loop\agents\exit_tool.py
C:\Projects\AgenticSystemDesign\source\agent.py
```

---

## Assistant (Plan · glm-5 · 22.1s)

_Thinking:_

The user is asking about what `ToolContext(agent_name=self.name)` provides. Based on the code I've seen, `ToolContext` is part of the Google ADK (Agent Development Kit) framework. Let me explain what it provides based on the usagepatterns I've observed and the general ADK framework patterns.

From the code:
1. `ToolContext(agent_name=self.name)` - Creates a context with the agent's name
2. `tool_context.actions.escalate = True` - Sets an escalate flag
3. The Event is yielded with `actions=tc.actions`

The key insight is that `ToolContext` provides a mechanism to communicate control signals back to the framework (like LoopAgent) via the `actions` attribute.

## `ToolContext(agent_name=self.name)` Explanation

`ToolContext` is a Google ADK framework class that provides a mechanism for agents to **communicate control signals** back to the orchestrating framework.

---

### What You Get from ToolContext

```python
from google.adk.tools.tool_context import ToolContext

tc = ToolContext(agent_name=self.name)
```

| Attribute/Property | Purpose |
|---------------------|---------|
| `tc.agent_name` | Identifies which agent created this context |
| `tc.actions` | Container for control signals (like `escalate`) |
| `tc.actions.escalate` | Boolean flag to signal LoopAgent termination |

---

### How It Works in ExitCheckerAgent

```python
# exit_checker_agent.py
tc = ToolContext(agent_name=self.name)  # Creates context for "ExitCheckerAgent"
exit_loop(tc)                           # Sets tc.actions.escalate = True
yield Event(author=self.name, actions=tc.actions)  # Pass actions to framework
return

# exit_tool.py
def exit_loop(tool_context: ToolContext):
    tool_context.actions.escalate = True  # Signal to stop looping
    return {}
```

---

### Event Actions Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                     ExitCheckerAgent                                 │
│                                                                      │
│  Event(author="ExitCheckerAgent", actions=Actions(escalate=True))  │
└────────────────────────────────────┬────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          LoopAgent                                   │
│                                                                      │
│  if event.actions and event.actions.escalate:                       │
│      # Stop looping, exit early                                     │
│      break                                                          │
└─────────────────────────────────────────────────────────────────────┘
```

---

### Why Use ToolContext Instead of Session State?

| Approach | Can Signal Loop Exit? | Why? |
|----------|----------------------|------|
| Session state (`ctx.session.state["exit"] = True`) | ❌ No | Session state is for **data**, LoopAgent doesn't check it for control |
| `Event(actions=...)` | ✅ Yes | Actions are **control signals** that framework components recognize |
| `ToolContext.actions` | ✅ Yes | Cleaner API wrapper around actions |

---

### What `actions` Can Contain

The `Actions` object can include various control signals (based on ADK patterns):

| Action | Purpose |
|--------|---------|
| `escalate` | Signal loop/flow termination |
| Other ADK actions | State deltas, tool responses, etc. |

---

### Summary

`ToolContext(agent_name=self.name)` gives you:

1. **A container for control signals** (`actions`)
2. **Agent identity tracking** (for debugging/logging)
3. **Framework-compatible way** to communicate with LoopAgent

The key purpose is **signaling termination** to `LoopAgent` via `actions.escalate=True`. Without this, the loop would continue until `max_iterations` regardless of performance.

---

