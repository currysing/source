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

class CandidateEvaluatorAgent(BaseAgent):
    _outdir: Path = PrivateAttr()   # Directory where candidate artifacts (code, metrics, visualizations) will be saved
    _leaderboard_path: Path = PrivateAttr() # Path to the central leaderboard CSV file where candidate scores will be appended

    def __init__(self, **kwargs):
        super().__init__(name="CandidateEvaluatorAgent", **kwargs)

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        iteration = ctx.session.state["iteration"]
        # Brax environment name (e.g. "ant", "humanoid", "halfcheetah")
        env_name = ctx.session.state["env_name"]
        train_steps = ctx.session.state["train_steps"]
        # Random seed base for reproducibility (each candidate will use seed + candidate_index to ensure different seeds)
        seed = ctx.session.state["seed"]
        # Number of candidates to evaluate (top-K from LLM output)
        K = ctx.session.state["K"]

        self._outdir = Path(ctx.session.state["outdir"])
        self._leaderboard_path = Path(ctx.session.state["leaderboard_path"])

        # Raw LLM output containing reward candidates is expected to be in the session state under "reward_candidates_text"
        text = ctx.session.state["reward_candidates_text"]
        
        # LLMs often wrap code in markdown backticks - this strips them out to extract clean code for parsing. 
        # We look for both ```python and generic ``` blocks, as well as inline backticks.
        # Remove markdown code blocks if present. 
        # First look for ```python blocks, then generic ``` blocks, then inline backticks.
        text = re.sub(r'```python\s*\n(.*?)\n```', r'\1', text, flags=re.DOTALL)
        # Remove ``` ... ``` blocks (generic)
        text = re.sub(r'```\s*\n(.*?)\n```', r'\1', text, flags=re.DOTALL)
        # Remove inline code backticks
        text = text.replace('`', '')    
        
        # Split text by ### CANDIDATE ### delimiter to separate different reward candidates.
        parts = text.split("### CANDIDATE ###")
        
        # Extract candidates - look for function definitions
        candidates = []
        for p in parts:
            p = p.strip()
            # For each section, locate def compute_reward and extract the entire function definition.
            if "def compute_reward" in p:
                # Extract just the function if there's extra text
                # Try to find the function boundaries (end of function or next def)
                # Match from "def compute_reward" to end of function (next def or end of string)
                func_match = re.search(r'def compute_reward.*?(?=\ndef [a-zA-Z_]|\Z)', p, re.DOTALL)
                if func_match:
                    candidates.append(func_match.group(0).strip())
                else:
                    # If no clear boundary, take the whole part
                    candidates.append(p)
        
        # Truncate to K candidates if there are more than K candidates in the LLM output. 
        # This ensures we only evaluate the top-K candidates as intended.
        candidates = candidates[:K]

        logger.info(f"[CandidateEvaluatorAgent] Parsed {len(candidates)} candidates from LLM output (expected {K})")
        
        # Handle No Candidates Case
        if not candidates:
            iterdir = self._outdir / f"iteration_{iteration:03d}"
            # Creates iteration directory
            iterdir.mkdir(parents=True, exist_ok=True)
            # Saves raw LLM output for debugging
            (iterdir / "raw_llm_output.txt").write_text(text)
            # Store empty results and error message in session state for reflector analysis
            ctx.session.state["candidate_results"] = "[]"
            ctx.session.state["llm_output_error"] = (
                "No valid reward candidates parsed. "
                "Expected delimiter '### CANDIDATE ###' and function 'compute_reward'. "
                f"Saved raw output to: {iterdir / 'raw_llm_output.txt'}"
            )
            yield Event(author=self.name, content=None)
            # Returns early (no evaluation) since there are no candidates to evaluate.
            return

        results = []
        error_summary = []
        # For each candidate (1 to K):
        for i, code in enumerate(candidates, start=1):
            cdir = candidate_dir(self._outdir, iteration, i)
            save_text(cdir / "reward.py", code)  # Always saves the code, even if evaluation fails later.
            logger.info(f"[CandidateEvaluatorAgent] Evaluating candidate {i}/{len(candidates)}")

            try:
                # Compile the reward function code to ensure it's valid and can be executed. 
                # This will catch syntax errors and other issues early.
                # Returns (scalar, dict) tuple as expected by the training and evaluation functions.
                # No None returns - reward function must return valid values for training to proceed.
                reward_fn = compile_reward(code)
                logger.debug(f"[CandidateEvaluatorAgent] Candidate {i}: Reward function compiled and validated successfully")
                
                logger.info(f"[CandidateEvaluatorAgent] Candidate {i}: Training policy (this may take a while)...")
                
                # Memory management to prevent accumulation across candidates
                # Clear JAX cache before training to prevent memory buildup
                # Note: JAX manages memory automatically, but clearing caches can help
                try:
                    import jax
                    # Try different methods depending on JAX version
                    if hasattr(jax, 'clear_caches'):
                        jax.clear_caches()
                    elif hasattr(jax.extend, 'backend') and hasattr(jax.extend.backend, 'clear_backends'):
                        jax.extend.backend.clear_backends()
                    # If neither exists, JAX will manage memory automatically
                except Exception as cache_error:
                    # Cache clearing is optional - JAX manages memory automatically
                    logger.debug(f"[CandidateEvaluatorAgent] Could not clear JAX cache (non-critical): {cache_error}")
                
                # Train policy with the reward function (this may take a while)
                make_inf, params, train_metrics, network_config = train_policy(
                    env_name, reward_fn, seed + i, train_steps,
                    episode_length=ctx.session.state["eval_horizon"]
                )
                # make_inf	Inference function factory that creates an inference function given policy parameters.
                # params	Trained policy parameters (JAX arrays, not JSON-serializable)
                # train_metrics	  Dict of training metrics (Training statistics such as episode returns, loss values, etc.)
                # network_config  Network configuration (observation_size, action_size)
                
                logger.info(f"[CandidateEvaluatorAgent] Candidate {i}: Evaluating policy...")

                # Evaluate policy on trained parameters (no retraining)
                # Evaluation metrics include average return, reward terms, 
                # and other statistics collected during evaluation episodes.
                # Evaluation uses the same reward function and environment, 
                # but runs separate episodes to assess performance.
                # Auto-detect device: use GPU if available for faster inference, 
                # but will fall back to CPU if GPU is not available or if memory constraints require it.
                eval_metrics = evaluate_policy(
                    env_name, reward_fn, make_inf, params, seed + i,
                    ctx.session.state["eval_episodes"],
                    ctx.session.state["eval_horizon"]
                    # use_cpu=None (default) will auto-detect: GPU if available, else CPU
                )
                score = score_candidate(eval_metrics)

                # Render and save interactive HTML viewer for this candidate (post-eval)
                # HTML viewer provides interactive 3D animation (play, pause, scrub, rotate)
                # Uses same device as params (GPU) to avoid device mismatch errors
                video_horizon = min(400, ctx.session.state["eval_horizon"])
                
                try:
                    logger.info(f"[CandidateEvaluatorAgent] Candidate {i}: Rendering interactive HTML viewer...")
                    save_policy_rollout_html(
                        out_dir=cdir,
                        env_name=env_name,
                        reward_fn=reward_fn,
                        make_inference_fn=make_inf,
                        params=params,
                        seed=seed + i,
                        horizon=video_horizon,
                    )
                    logger.info(f"[CandidateEvaluatorAgent] Candidate {i}: Saved interactive HTML viewer (rollout.html)")
                except Exception as render_err:
                    logger.warning(f"[CandidateEvaluatorAgent] Candidate {i}: HTML viewer rendering failed (non-critical): {render_err}. Continuing...")

                save_json(cdir / "train_metrics.json", train_metrics)
                save_json(cdir / "eval_metrics.json", eval_metrics)
                save_json(cdir / "score.json", {"score": score})
                
                # Save metadata needed to regenerate visualizations later
                # This includes training config AND network architecture so we can recreate the inference function
                save_json(cdir / "training_metadata.json", {
                    "seed": seed + i,
                    "train_steps": train_steps,
                    "episode_length": ctx.session.state["eval_horizon"],
                    "env_name": env_name,
                    "network_config": network_config,  # Critical: observation_size, action_size
                    "note": (
                        "To regenerate visualizations: Use recreate_inference_fn() with saved params and network_config. "
                        "This avoids retraining and dimension mismatches."
                    )
                })
                
                # Save trained policy parameters (inference fn is not serialized)
                # If saving fails, log warning but don't fail the candidate evaluation
                try:
                    save_policy_params(cdir / "policy_params.pkl", params)
                    logger.debug(f"[CandidateEvaluatorAgent] Candidate {i}: Policy parameters saved")
                except Exception as save_error:
                    logger.warning(
                        f"[CandidateEvaluatorAgent] Candidate {i}: Failed to save policy parameters: {save_error}. "
                        f"Evaluation succeeded but params not saved."
                    )
                    # Save error to a separate file for debugging
                    save_text(cdir / "policy_save_error.txt", str(save_error))

                # Update Leaderboard
                # Append to leaderboard with iteration, candidate index, score, average return, 
                # and path to candidate directory for traceability.
                append_leaderboard(self._leaderboard_path, iteration, i, score, eval_metrics["avg_return"], str(cdir))

                logger.info(f"[CandidateEvaluatorAgent] Candidate {i}: Success! Score={score:.2f}, Avg Return={eval_metrics['avg_return']:.2f}")

                results.append({
                    "candidate": i,
                    "score": score,
                    "eval": eval_metrics,
                    "train_metrics": train_metrics,  # Add behavioral metrics for reflector analysis
                    "artifact_dir": str(cdir),
                    "reward_code": code
                })

            # Error Handling for Each Candidate
            except Exception as e:
                error_msg = str(e)
                error_type = type(e).__name__
                error_summary.append(f"Candidate {i}: {error_type}: {error_msg}")
                logger.error(f"[CandidateEvaluatorAgent] Candidate {i}: Failed with {error_type}: {error_msg}")
                
                # Save detailed error information
                error_details = f"""Candidate {i} Evaluation Failed

Error Type: {error_type}
Error Message: {error_msg}

Reward Code:
{code}

Common Issues:
- Missing return statement: Ensure 'return total_reward, reward_terms' at end of function
- None values: Check that all variables are computed before returning
- Wrong return format: Must return (scalar_jax_array, dict_of_arrays)
- Syntax errors: Check for unclosed parentheses, brackets, or quotes
"""
                save_text(cdir / "error.txt", error_details)
                
                # Also save a validation_error.txt if it's a validation error
                if "validation" in error_msg.lower() or "must return" in error_msg.lower():
                    save_text(cdir / "validation_error.txt", error_msg)
                
                # Records -999 score in leaderboard for failed candidates to ensure they are ranked at the bottom, 
                # along with error details in the candidate directory for debugging.
                append_leaderboard(self._leaderboard_path, iteration, i, -999, -999, str(cdir))

        # Store error summary if all candidates failed
        if not results and error_summary:
            ctx.session.state["evaluation_errors"] = "\n".join(error_summary)
            logger.error(f"[CandidateEvaluatorAgent] All {len(candidates)} candidates failed evaluation!")
        elif results:
            logger.info(f"[CandidateEvaluatorAgent] Successfully evaluated {len(results)}/{len(candidates)} candidates")
        
        # JSON Serialization Helper 
        # Converts complex objects (JAX arrays, numpy arrays) to JSON-serializable formats (lists, scalars) recursively.
        # Recursively convert JAX arrays, numpy arrays, and other non-serializable objects to JSON-serializable format
        # JAX returns DeviceArray / Array objects which are not JSON-serializable, 
        # so we convert them to lists or scalars as appropriate.
        # NumPy returns ndarray scalars and arrays which also need conversion.
        # Python primitives -> Pass through
        # JAX Array (scalar) ->	int or float
        # JAX/NumPy Array (multi) -> Python list
        # Dict -> Recursively convert values
        # List/Tuple -> Recursively convert items
        # Unknown -> str() representation
        def convert_to_json_serializable(obj):
            """Recursively convert objects to JSON-serializable format."""
            import numpy as np
            
            # Handle None and basic types
            if obj is None or isinstance(obj, (int, float, str, bool)):
                return obj
            
            # Try to convert array-like objects (JAX arrays, numpy arrays) to numpy first
            try:
                # Check if it's array-like (has shape or __array__ method)
                if hasattr(obj, 'shape') or hasattr(obj, '__array__'):
                    np_array = np.asarray(obj)
                    if np_array.size == 1:
                        # Scalar - return as single value
                        return float(np_array.item()) if np.issubdtype(np_array.dtype, np.floating) else int(np_array.item())
                    else:
                        # Multi-element array - return as list
                        return np_array.tolist()
            except (TypeError, ValueError, AttributeError):
                pass
            
            # Handle numpy scalar types
            if isinstance(obj, (np.integer, np.floating)):
                return float(obj) if isinstance(obj, np.floating) else int(obj)
            elif isinstance(obj, np.ndarray):
                if obj.size == 1:
                    return float(obj.item()) if np.issubdtype(obj.dtype, np.floating) else int(obj.item())
                else:
                    return obj.tolist()
            elif isinstance(obj, np.bool_):
                return bool(obj)
            
            # Handle collections - recursively convert
            if isinstance(obj, dict):
                return {k: convert_to_json_serializable(v) for k, v in obj.items()}
            elif isinstance(obj, (list, tuple)):
                return [convert_to_json_serializable(item) for item in obj]
            
            # Check if it's a JAX array by module name (fallback)
            try:
                if hasattr(type(obj), '__module__') and type(obj).__module__.startswith('jax'):
                    np_array = np.asarray(obj)
                    if np_array.size == 1:
                        return float(np_array.item()) if np.issubdtype(np_array.dtype, np.floating) else int(np_array.item())
                    else:
                        return np_array.tolist()
            except (TypeError, ValueError, AttributeError):
                pass
            
            # If we can't convert it, return as string representation (fallback)
            logger.warning(f"[CandidateEvaluatorAgent] Could not convert {type(obj)} to JSON-serializable format, using string representation")
            return str(obj)
        
        # Store Results:
        # Convert the entire results structure before JSON serialization
        # Converts all JAX/NumPy arrays to JSON-safe types
        # Stores as JSON string in session state
        # Signals completion via Event
        serializable_results = convert_to_json_serializable(results)
        ctx.session.state["candidate_results"] = json.dumps(serializable_results, indent=2)
        yield Event(author=self.name, content=None)
