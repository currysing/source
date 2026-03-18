# AGENTS.md

This file provides guidance to agentic coding agents (like Claude, Cursor, or GitHub Copilot) working in this codebase.

## Project Overview

This is a **Eureka-like reward learning agent** that uses LLMs to iteratively design and improve reward functions for reinforcement learning tasks. Built with:

- **Google ADK** (Agent Development Kit) - Agent orchestration framework
- **JAX/Brax** - Differentiable physics and RL environments
- **OpenAI API** - LLM-based reward function generation

**Architecture:**
```
SequentialAgent (root)
├── SetupAgent - Validates config, initializes environment
└── LoopAgent (RewardEvolutionLoop)
    ├── RewardDesignerOpenAIAgent - Generates reward candidates
    ├── CandidateEvaluatorAgent - Trains and evaluates policies
    ├── SelectorAgent - Selects best candidate
    ├── RewardReflectorOpenAIAgent - Analyzes results, suggests improvements
    ├── HumanReflectionAgent - Optional human-in-the-loop feedback
    ├── ExitCheckerAgent - Checks termination criteria
    └── IncrementIterationAgent - Increments iteration counter
```

## Prerequisites

- Python 3.10+
- Required packages: `google-adk`, `brax`, `jax`, `openai`, `loguru`, `pydantic`, `tenacity`, `pyyaml`, `numpy`

Set environment variable:
```bash
export OPENAI_API_KEY="your-key-here"
```

## Build/Lint/Test Commands

```bash
# Syntax check (basic validation)
python -m py_compile agent.py
python -m py_compile eureka_loop/agents/*.py
python -m py_compile eureka_loop/tools/*.py

# Lint (recommended)
ruff check .

# Run the agent
adk run eureka_loop

# Tests (not yet configured)
# pytest -v
```

## Code Style Guidelines

### Imports
```python
# Order: standard library → third-party → local imports
import json
import os
from pathlib import Path

from loguru import logger
from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from typing import AsyncGenerator

from ..tools.artifacts import save_json, save_text
```

### Naming Conventions
- **Functions/Variables**: `snake_case` (e.g., `train_policy`, `best_reward_code`)
- **Classes**: `PascalCase` (e.g., `CandidateEvaluatorAgent`, `RewardWrapper`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `CANDIDATE_DELIM`, `FORBIDDEN_NAMES`)
- **Private attributes**: `_model`, `_outdir` (use Pydantic `PrivateAttr()`)

### Type Hints
Always include type hints on function signatures:
```python
def train_policy(env_name: str, reward_fn, seed: int, steps: int, episode_length: int = 1000):
    ...

def score_candidate(eval_metrics: dict) -> float:
    ...

async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
    ...
```

### Docstrings
Use triple-quoted docstrings for classes and complex functions:
```python
def compile_reward(code: str):
    """Compile and validate reward function.
    
    Args:
        code: Python code string containing compute_reward function
        
    Returns:
        Validated reward function
        
    Raises:
        ValueError: If code fails validation
    """
```

### Logging
Use `loguru.logger` throughout:
```python
from loguru import logger

logger.info(f"[AgentName] Starting process...")
logger.debug(f"[AgentName] Details: {value}")
logger.warning(f"[AgentName] Non-critical issue: {error}")
logger.error(f"[AgentName] Failed: {error}")
```

### Error Handling
Wrap risky operations in try-except with descriptive messages:
```python
try:
    result = risky_operation()
except FileNotFoundError as e:
    raise FileNotFoundError(f"Configuration file not found: {path}")
except yaml.YAMLError as e:
    raise ValueError(f"Failed to parse YAML file {path}: {e}")
except Exception as e:
    raise ValueError(f"Unexpected error: {e}")
```

## Agent Development Patterns

### Creating a New Agent
Subclass `BaseAgent` and implement `_run_async_impl`:
```python
from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from typing import AsyncGenerator
from loguru import logger

class MyNewAgent(BaseAgent):
    def __init__(self, **kwargs):
        super().__init__(name="MyNewAgent", **kwargs)

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        logger.info(f"[MyNewAgent] Starting...")
        
        # Access session state
        value = ctx.session.state.get("key", default_value)
        
        # Modify session state
        ctx.session.state["new_key"] = computed_value
        
        # Signal completion
        yield Event(author=self.name, content=None)
```

### Session State Keys
Common state keys passed between agents:
- `outdir`: Output directory path
- `env_name`: Brax environment name
- `task_spec`: Task specification dict
- `iteration`: Current iteration number
- `K`: Candidates per iteration
- `best_reward_code`: Selected reward code
- `candidate_results`: JSON string of evaluation results
- `reflection`: LLM reflection text

## Tool Development Patterns

### Reward Functions
Must define `compute_reward` with signature:
```python
def compute_reward(obs, action, next_obs, info):
    """Reward function for Brax environments.
    
    Args:
        obs: Current observation
        action: Action taken
        next_obs: Next observation
        info: Dict with 'metrics' key
        
    Returns:
        tuple: (total_reward: jnp.ndarray, reward_terms: dict[str, jnp.ndarray])
    """
    velocity = next_obs[..., 8]
    total = velocity
    terms = {"velocity": velocity}
    return total, terms
```

**Constraints:**
- No imports allowed
- Only use `jnp`, `jax`, `math`
- Must return `(scalar, dict)` tuple

### Validation
Use `reward_sandbox.compile_reward()` to validate:
```python
from ..tools.reward_sandbox import compile_reward

try:
    reward_fn = compile_reward(code)
except ValueError as e:
    logger.error(f"Reward validation failed: {e}")
```

## Configuration Files

YAML configuration in `configs/`:

```yaml
# loop_config.yaml
env_name: "halfcheetah"
iterations: 5
candidates_per_iteration: 2
train_steps: 200000
seed: 0
openai_model: "gpt-4o-mini"
return_threshold: 2500
plateau_delta: 100
plateau_patience: 2

# task_spec_*.yaml
task_name: "Task description"
objective: "What the agent should achieve"
success_metric: "How to measure success"
constraints:
  - "Constraint 1"
  - "Constraint 2"
evaluation:
  horizon: 1000
  episodes: 1
```

## File Organization

```
source/
├── agent.py                    # ADK entrypoint
├── AGENTS.md                   # This file
├── configs/
│   ├── loop_config.yaml
│   └── task_spec_*.yaml
└── eureka_loop/
    ├── __init__.py
    ├── agents/
    │   ├── setup_agent.py
    │   ├── reward_loop.py
    │   ├── llm_agents.py
    │   ├── evaluator_agent.py
    │   ├── selector_agent.py
    │   ├── exit_checker_agent.py
    │   ├── increment_iteration_agent.py
    │   └── human_reflection_agent.py
    └── tools/
        ├── scoring.py
        ├── rl_runner.py
        ├── reward_sandbox.py
        ├── artifacts.py
        ├── brax_env.py
        └── regenerate_visualization.py
```

## Output Artifacts

Generated files saved to `outputs/run_YYYYMMDD_HHMMSS/`:
- `iteration_NNN/candidate_MM/reward.py` - Reward function code
- `iteration_NNN/candidate_MM/rollout.html` - Interactive visualization
- `iteration_NNN/candidate_MM/train_metrics.json` - Training metrics
- `iteration_NNN/candidate_MM/eval_metrics.json` - Evaluation metrics
- `leaderboard.csv` - Score tracking across iterations