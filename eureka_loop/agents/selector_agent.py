from google.adk.agents import BaseAgent # Parent class for all ADK agents
from google.adk.agents.invocation_context import InvocationContext  # Session state and context access
from google.adk.events import Event # Signal yield for async iteration
from typing import AsyncGenerator   # Type hint for async yield pattern
import json         # Parse candidate_results JSON string
import numpy as np  # np.argmax() for best score selection, np.isnan() for validation
from loguru import logger

class SelectorAgent(BaseAgent):     # Follows ADK agent pattern with _run_async_impl implementation
    # Receives InvocationContext with session state containing candidate_results from CandidateEvaluatorAgent
    # Parses candidate_results, selects best candidate based on score, 
    # and updates session state with best candidate info
    # Handles edge cases like missing candidate_results, empty results, 
    # invalid scores (NaN), and logs detailed information for debugging
    # Returns an async generator of Event objects to signal completion of selection process
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        logger.info("[SelectorAgent] Starting candidate selection...")
        
        # Check if candidate_results exists
        # This is a critical check to ensure that the previous agent (CandidateEvaluatorAgent) produced results as expected.
        if "candidate_results" not in ctx.session.state:
            raise ValueError("[SelectorAgent] 'candidate_results' not found in session state. CandidateEvaluatorAgent may not have run successfully.")
        
        try:
            results = json.loads(ctx.session.state["candidate_results"])
            logger.info(f"[SelectorAgent] Loaded {len(results)} candidate results")     # Logs number of candidates found
        except json.JSONDecodeError as e:   # logs partial content for debugging, raises descriptive error
            logger.error(f"[SelectorAgent] Failed to parse candidate_results as JSON: {e}")
            logger.error(f"[SelectorAgent] candidate_results content (first 500 chars): {ctx.session.state['candidate_results'][:500]}")
            raise ValueError(f"[SelectorAgent] Invalid JSON in candidate_results: {e}")

        # Handle Empty Results
        if not results:
            # Check for different error scenarios
            llm_error = ctx.session.state.get("llm_output_error", "")
            eval_errors = ctx.session.state.get("evaluation_errors", "")
            
            error_parts = []
            # Checks for upstream LLM parsing errors
            if llm_error:
                error_parts.append(f"LLM parsing error: {llm_error}")
            # Checks for evaluation failures
            if eval_errors:
                error_parts.append(f"Evaluation errors (all candidates failed):\n{eval_errors}")
            if not error_parts:
                error_parts.append("No candidate results were produced.")

            # Provides detailed error message combining all failure sources
            error_msg = "\n".join(error_parts)
            raise ValueError(f"[SelectorAgent] Empty candidate results. {error_msg}")

        # Extract scores, handling NaN and invalid values
        scores = []
        for i, r in enumerate(results):
            # Keep as float, log at debug level for detailed traceability, and handle missing score with -inf
            # This ensures that candidates with missing scores are not selected, 
            # and provides visibility into the scoring process for debugging.
            # Why -inf? Ensures invalid candidates can never be selected by argmax.
            score = r.get("score", -float('inf'))   

            # Convert NaN to -inf so they're not selected
            if isinstance(score, (int, float)) and not np.isnan(score):
                scores.append(float(score))
                logger.debug(f"[SelectorAgent] Candidate {i+1}: score={float(score):.2f}")
            else:
                scores.append(-float('inf'))
                logger.warning(f"[SelectorAgent] Candidate {i+1}: invalid score={score}, using -inf")
        
        # All scores invalid check: if all scores are -inf, it means all candidates had invalid or missing scores, 
        # which is a critical failure for selection. Logs error and raises exception to prevent silent failures.
        if not scores or all(s == -float('inf') for s in scores):
            logger.error(f"[SelectorAgent] All candidate scores are invalid. Scores: {scores}")
            raise ValueError(
                "[SelectorAgent] All candidate scores are invalid (NaN or missing). "
                "Cannot select best candidate."
            )
        
        # np.argmax() returns index of highest score candidate. 
        # int() converts numpy int to Python int for compatibility with session state and logging.
        best_idx = int(np.argmax(scores))   
        best = results[best_idx]
        logger.info(f"[SelectorAgent] Selected candidate {best_idx + 1} (0-indexed: {best_idx}) with score={scores[best_idx]:.2f}")

        # Validate Best Candidate has required keys before updating session state.
        # reward_code - The Python code for the reward function
        # eval.avg_return - The average return from evaluating the reward function, used for final selection
        if "reward_code" not in best:
            raise ValueError(f"[SelectorAgent] Best candidate {best_idx} missing 'reward_code' key")
        if "eval" not in best or "avg_return" not in best["eval"]:
            raise ValueError(f"[SelectorAgent] Best candidate {best_idx} missing 'eval.avg_return' key")

        # Index of selected candidate stored in session state for downstream agents 
        # to reference which candidate was selected.
        ctx.session.state["best_candidate_index"] = best_idx
        # Winning reward function code is stored in session state for use by 
        # downstream agents (e.g., RewardFunctionAgent) to execute the selected reward function.
        ctx.session.state["best_reward_code"] = best["reward_code"]
        # Full JSON of best candidate stored as string in session state for reference and debugging.
        ctx.session.state["best_candidate_summary"] = json.dumps(best, indent=2, default=str)
        # Average return from evaluation of best candidate stored as float in session state 
        # for tracking performance of selected reward function.
        ctx.session.state["best_return"] = float(best["eval"]["avg_return"])
        
        # Logs summary at INFO level
        logger.info(f"[SelectorAgent] Selection complete. Best return: {ctx.session.state['best_return']:.2f}")
        # Logs detailed JSON at DEBUG level (truncated to 200 chars)
        logger.debug(f"[SelectorAgent] Best candidate summary: {ctx.session.state['best_candidate_summary'][:200]}...")
        
        # Yields Event to signal completion to the LoopAgent that the selection process is done
        # and downstream agents can proceed with the selected candidate information in session state.
        yield Event(author=self.name, content=None)
