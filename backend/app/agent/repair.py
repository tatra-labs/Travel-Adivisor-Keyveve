from typing import List, Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from app.agent.state import AgentState, Violation, PlanStep, ConstraintType
from app.tools.registry import tool_registry
from pydantic import BaseModel, Field


class RepairSuggestion(BaseModel):
    step_id: str = Field(..., description="ID of the plan step to modify or remove.")
    action: str = Field(..., description="Action to take: \"modify\", \"remove\", or \"add\".")
    new_args: Optional[Dict[str, Any]] = Field(None, description="New arguments for the tool call if action is \"modify\".")
    new_step: Optional[PlanStep] = Field(None, description="New plan step if action is \"add\".")
    reasoning: str = Field(..., description="Reasoning for the suggested repair.")


class RepairPlanOutput(BaseModel):
    suggestions: List[RepairSuggestion] = Field(..., description="List of suggested repairs to the plan.")
    overall_reasoning: str = Field(..., description="Overall reasoning for the repair strategy.")


class RepairReplan:
    """Repairs the plan based on identified violations."""
    
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0)
        self.tool_schemas = tool_registry.get_tool_schemas()
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert travel planner tasked with repairing an itinerary plan. You have identified violations and need to suggest specific changes to the existing plan steps to resolve them. Your goal is to make the minimum necessary changes to satisfy all constraints.\n\nAvailable tools and their schemas:\n{tool_schemas}\n\nCurrent plan:\n{current_plan}\n\nIdentified violations:\n{violations}\n\nCurrent working set (intermediate results):\n{working_set}\n\nSuggest repairs as a list of RepairSuggestion objects. Each suggestion must include the `step_id` of the plan step to modify/remove, the `action` (modify, remove, add), `new_args` (if modifying), `new_step` (if adding), and `reasoning`. If adding a new step, provide a complete PlanStep object. When modifying, only provide the arguments that need to change.\n\nExample RepairSuggestion (modify):\n{{\"step_id\": \"flights_step_1\", \"action\": \"modify\", \"new_args\": {{\"budget\": 1000}}, \"reasoning\": \"Reduce flight budget to meet overall budget constraint.\"}}\n\nExample RepairSuggestion (add):\n{{\"step_id\": \"new_event_step\", \"action\": \"add\", \"new_step\": {{\"id\": \"new_event_step\", \"tool_name\": \"events\", \"args\": {{\"destination\": \"Kyoto\", \"date\": \"2025-10-05\", \"category\": \"indoor\"}}, \"dependencies\": [\"lodging_step_1\"]}}, \"reasoning\": \"Add an indoor activity for a rainy day.\"}}\n\nPrioritize addressing critical violations first. If a violation suggests a specific fix, try to incorporate it. If a step needs to be re-executed, ensure its status is reset to \"pending\".\n\nReturn a JSON object with a \"suggestions\" key containing the list of RepairSuggestion objects and an \"overall_reasoning\" key explaining your repair strategy."),
            ("human", "Repair the travel plan.")
        ]).with_structured_output(RepairPlanOutput)
    
    def __call__(self, state: AgentState) -> Dict[str, Any]:
        plan: List[PlanStep] = state["plan"]
        violations: List[Violation] = state["violations"]
        working_set: Dict[str, Any] = state["working_set"]
        
        if not violations:
            return state # No violations to repair
        
        # Convert plan and violations to LLM-friendly format
        formatted_plan = [p.model_dump() for p in plan]
        formatted_violations = [v.model_dump() for v in violations]
        
        response = self.llm.invoke({
            "tool_schemas": self.tool_schemas,
            "current_plan": formatted_plan,
            "violations": formatted_violations,
            "working_set": working_set
        })
        
        updated_plan = list(plan) # Create a mutable copy
        
        for suggestion in response.suggestions:
            if suggestion.action == "modify":
                for i, step in enumerate(updated_plan):
                    if step.id == suggestion.step_id:
                        if suggestion.new_args:
                            step.args.update(suggestion.new_args)
                        step.status = "pending" # Mark for re-execution
                        break
            elif suggestion.action == "remove":
                updated_plan = [step for step in updated_plan if step.id != suggestion.step_id]
            elif suggestion.action == "add":
                if suggestion.new_step:
                    updated_plan.append(PlanStep(**suggestion.new_step.model_dump()))
        
        # Clear violations after attempting repair
        state["violations"] = []
        
        return {
            "plan": updated_plan,
            "violations": [], # Clear violations after repair attempt
            "working_set": {
                **working_set,
                "repair_reasoning": response.overall_reasoning
            }
        }

