from typing import List, Dict, Any
from app.agent.state import AgentState, ToolCall, PlanStep
from app.tools.registry import tool_registry
import asyncio
import time


class ToolExecutor:
    """Executes tool calls and updates the agent state with results."""
    
    async def __call__(self, state: AgentState) -> Dict[str, Any]:
        plan: List[PlanStep] = state["plan"]
        working_set: Dict[str, Any] = state["working_set"]
        tool_calls: List[ToolCall] = state["tool_calls"]
        
        # Get steps that are marked as 'running' by the router
        steps_to_execute = [step for step in plan if step.status == "running"]
        
        if not steps_to_execute:
            return {}
        
        # Execute tools in parallel
        results = await asyncio.gather(*[
            self._execute_single_tool(step, state["retry_count"])
            for step in steps_to_execute
        ])
        
        for step, tool_output in zip(steps_to_execute, results):
            # Update tool_calls history
            new_tool_call = ToolCall(
                tool_name=step.tool_name,
                args=step.args,
                result=tool_output.data,
                duration_ms=tool_output.duration_ms,
                error=tool_output.error
            )
            tool_calls.append(new_tool_call)
            
            # Update plan step status
            if tool_output.success:
                step.status = "completed"
                # Add tool output to working set
                working_set[f"{step.tool_name}_{step.id}_output"] = tool_output.data
            else:
                step.status = "failed"
                # Optionally, add error to working set
                working_set[f"{step.tool_name}_{step.id}_error"] = tool_output.error
        
        return {
            "plan": plan,
            "tool_calls": tool_calls,
            "working_set": working_set
        }
    
    async def _execute_single_tool(self, step: PlanStep, retry_count: int) -> Any:
        """Execute a single tool with retries and caching."""
        tool = tool_registry.get_tool(step.tool_name)
        
        # Max retries for tool execution is 1 as per requirements (1 with jitter)
        # The BaseTool class already handles retries, so we just pass max_retries=1
        tool_output = await tool.execute(step.args, max_retries=1)
        
        return tool_output

