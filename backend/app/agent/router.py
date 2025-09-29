from typing import List, Dict, Any
from app.agent.state import AgentState, PlanStep


class Router:
    """Determines the next steps to execute based on the current plan and completed steps."""
    
    def __call__(self, state: AgentState) -> Dict[str, Any]:
        plan: List[PlanStep] = state["plan"]
        working_set: Dict[str, Any] = state["working_set"]
        
        executable_steps = []
        for step in plan:
            if step.status == "pending":
                # Check if all dependencies are met
                dependencies_met = True
                for dep_id in step.dependencies:
                    dep_step = next((s for s in plan if s.id == dep_id), None)
                    if not dep_step or dep_step.status != "completed":
                        dependencies_met = False
                        break
                
                if dependencies_met:
                    executable_steps.append(step)
        
        # For simplicity, let's execute all executable steps in parallel for now
        # In a more complex scenario, this would involve a more sophisticated scheduler
        # that might prioritize certain steps or limit parallel execution.
        
        # Update status of executable steps to 'running'
        for step in executable_steps:
            step.status = "running"
        
        return {
            "plan": plan,  # Update the plan with running steps
            "working_set": working_set, # Pass through working set
            "executable_steps": [step.model_dump() for step in executable_steps]
        }

