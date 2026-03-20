import yaml
from google.adk.agents import LoopAgent
from .llm_agents import RewardDesignerOpenAIAgent, RewardReflectorOpenAIAgent
from .evaluator_agent import CandidateEvaluatorAgent
from .selector_agent import SelectorAgent
from .human_reflection_agent import HumanReflectionAgent
from .increment_iteration_agent import IncrementIterationAgent
from .exit_checker_agent import ExitCheckerAgent

def _load_yaml(path):
    with open(path, "r") as f:
        return yaml.safe_load(f)

def build_reward_loop():
    # Reads settings like iterations, openai_model, training parameters.
    loop_cfg = _load_yaml("configs/loop_config.yaml")   
    model = loop_cfg.get("openai_model", "gpt-4o-mini")

    return LoopAgent(   # Create LoopAgent with the specified sub-agents and configuration.
        name="RewardEvolutionLoop",
        sub_agents=[
            # Agent that designs reward functions based on the current state of the loop and feedback.
            RewardDesignerOpenAIAgent(model=model), 
            # Agent that evaluates the candidate reward functions designed by the RewardDesignerAgent.
            CandidateEvaluatorAgent(), 
            # Agent that selects the best reward function based on the evaluations from the CandidateEvaluatorAgent.
            SelectorAgent(name="SelectorAgent"), 
            # Agent that reflects on the selected reward function and provides feedback for improvement.
            RewardReflectorOpenAIAgent(model=model),    
            # Human-in-the-loop after LLM reflection
            HumanReflectionAgent(name="HumanReflectionAgent"),  
            # Agent that checks if the loop should exit based on certain criteria, 
            # such as convergence or performance thresholds.
            ExitCheckerAgent(name="ExitCheckerAgent"),  
            # Agent that increments the iteration count. 
            # This is important for tracking how many iterations the loop has gone through 
            # and can be used for logging or exit conditions.
            IncrementIterationAgent(name="IncrementIterationAgent"), 
        ],
        max_iterations=loop_cfg["iterations"]
    )
