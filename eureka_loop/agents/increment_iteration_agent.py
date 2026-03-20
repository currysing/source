from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from typing import AsyncGenerator
from loguru import logger

# Minimal agent - no configuration or state needed
# No __init__ override required (uses default)
class IncrementIterationAgent(BaseAgent):
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        old_iteration = ctx.session.state.get("iteration", 1)
        new_iteration = old_iteration + 1
        ctx.session.state["iteration"] = new_iteration
        
        # Log state that should persist to next iteration
        best_reward_code = ctx.session.state.get("best_reward_code", "")
        reflection = ctx.session.state.get("reflection", "")
        # Used by ExitCheckerAgent for termination condition
        best_return = ctx.session.state.get("best_return", None)
        
        # Why log here?
        # Confirms state is correctly preserved
        # Helps debug if next iteration receives wrong data
        # Shows char counts to detect empty/truncated values
        logger.info(f"[IncrementIterationAgent] Incrementing iteration: {old_iteration} -> {new_iteration}")
        logger.info(f"[IncrementIterationAgent] State for next iteration:")
        logger.info(f"  - best_reward_code: {'SET' if best_reward_code else 'EMPTY'} ({len(best_reward_code)} chars)")
        logger.info(f"  - reflection: {'SET' if reflection else 'EMPTY'} ({len(reflection)} chars)")
        logger.info(f"  - best_return: {best_return}")
        
        # Yields control back to LoopAgent for next iteration or exit.
        yield Event(author=self.name, content=None)
