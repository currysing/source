from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from typing import AsyncGenerator
from google.adk.tools.tool_context import ToolContext   # Mechanism to signal loop termination
from .exit_tool import exit_loop    # Helper function that sets escalate=True
from loguru import logger

class ExitCheckerAgent(BaseAgent):
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        best_return = ctx.session.state.get("best_return", None)

        # Early exit if no best_return:
        # First iteration might not have results yet
        # Or SelectorAgent failed to set best_return
        # Returns without action - loop continues
        if best_return is None:
            logger.info(f"[ExitCheckerAgent] No best return found. Continuing loop.")
            yield Event(author=self.name, content=None)
            return

        # return_threshold: 2500	Target performance to reach
        threshold = ctx.session.state["return_threshold"]
        # plateau_delta: 100	Minimum improvement to avoid counting as a plateau
        delta = ctx.session.state["plateau_delta"]
        # plateau_patience: 2	Number of iterations to wait for improvement before exiting
        patience = ctx.session.state["plateau_patience"]

        prev = ctx.session.state.get("prev_best_return", None)

        # Track Plateau Progress:
        # improvement >= delta	-> Made progress	        -> Reset plateau_count = 0
        # improvement < delta	-> No meaningful progress	-> Increment plateau_count += 1
        # prev is None	        -> First iteration	        -> Skip plateau check
        if prev is not None:
            improvement = best_return - prev
            if improvement < delta:
                ctx.session.state["plateau_count"] = ctx.session.state.get("plateau_count", 0) + 1
            else:
                ctx.session.state["plateau_count"] = 0
# Example:
# Iteration 1: best_return = 2000, prev = None     → plateau_count = 0
# Iteration 2: best_return = 2100, prev = 2000     → improvement = 100 >= delta → plateau_count = 0
# Iteration 3: best_return = 2150, prev = 2100     → improvement = 50 < delta   → plateau_count = 1
# Iteration 4: best_return = 2180, prev = 2150     → improvement = 30 < delta   → plateau_count = 2 (exit!)

        ctx.session.state["prev_best_return"] = best_return
        plateau_count = ctx.session.state.get("plateau_count", 0)

        # Exit Decision Logic:
        # Exit if we've reached the threshold OR if we've plateaued after reaching a good performance
        # The original logic required both conditions, which seems too restrictive
        # New logic: exit if threshold reached OR if we've plateaued (with some minimum performance)
        should_exit = False
        exit_reason = ""
        
        if best_return >= threshold:
            if plateau_count >= patience:
                should_exit = True
                exit_reason = f"Reached threshold ({best_return:.2f} >= {threshold}) and plateaued ({plateau_count} >= {patience})"
            # Also exit immediately if we're well above threshold (no need to wait for plateau)
            elif best_return >= threshold * 1.1:  # 10% above threshold
                should_exit = True
                exit_reason = f"Significantly exceeded threshold ({best_return:.2f} >= {threshold * 1.1:.2f})"
        # Why “positive performance” check?
        # Prevents exiting when all candidates perform poorly (negative returns)
        # Forces loop to continue trying to find something valid
        elif plateau_count >= patience and best_return > 0:
            # Exit if we've plateaued and have positive performance (avoid exiting on negative plateaus)
            should_exit = True
            exit_reason = f"Performance plateaued ({plateau_count} >= {patience}) with return {best_return:.2f}"
        
        # Execute Exit
        if should_exit:
            logger.info(f"[ExitCheckerAgent] Exiting loop: {exit_reason}")
            # Create ToolContext with agent name
            tc = ToolContext(agent_name=self.name)
            # Call exit_loop(tc) (coming from exit_tool.py) → sets tc.actions.escalate = True
            exit_loop(tc)   
            # Yield Event with actions=tc.actions
            # LoopAgent sees escalate=True → stops looping
            yield Event(author=self.name, actions=tc.actions)   
            return

        yield Event(author=self.name, content=None)
