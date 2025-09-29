from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from app.agent.state import AgentState, PlanStep
from app.tools.registry import tool_registry


class PlannerInput(BaseModel):
    constraints: List[Dict[str, Any]] = Field(..., description="List of extracted constraints and preferences")
    current_plan: List[Dict[str, Any]] = Field(default_factory=list, description="Current plan steps if any")
    working_set: Dict[str, Any] = Field(default_factory=dict, description="Current working set of intermediate results")


class PlannerOutput(BaseModel):
    plan: List[PlanStep] = Field(..., description="A list of plan steps, each specifying a tool call and its arguments.")
    reasoning: str = Field(..., description="Reasoning behind the generated plan.")


class Planner:
    """Generates a multi-step plan based on extracted constraints."""
    
    def __init__(self):
        try:
            from app.core.config import settings
            if hasattr(settings, 'openai_api_key') and settings.openai_api_key:
                self.llm = ChatOpenAI(model="gpt-4o", temperature=0, openai_api_key=settings.openai_api_key)
            else:
                self.llm = None
        except Exception as e:
            print(f"Warning: Could not initialize ChatOpenAI in Planner: {e}")
            self.llm = None
        
        try:
            self.tool_schemas = tool_registry.get_tool_schemas()
        except Exception as e:
            print(f"Warning: Could not get tool schemas: {e}")
            self.tool_schemas = {}
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert travel planner. Your goal is to create a detailed, multi-step itinerary plan based on user constraints and available tools. Each step should be a call to one of the provided tools. Consider dependencies between steps. For example, you need flight information before planning lodging, and lodging before planning local events. If comparing multiple options (e.g., airports, neighborhoods), plan parallel tool calls.\n\nAvailable tools and their schemas:\n{tool_schemas}\n\nCurrent constraints:\n{constraints}\n\nCurrent working set (intermediate results):\n{working_set}\n\nGenerate a plan as a list of PlanStep objects. Each PlanStep must include 'id', 'tool_name', 'args', and 'dependencies'. 'dependencies' should be a list of 'id's of other PlanSteps that must complete before this step can run. Estimate 'estimated_cost' and 'estimated_duration_ms' for each step if possible. If a plan already exists, refine it based on new information or simply return it if it's still valid.\n\nExample PlanStep:\n{{\"id\": \"step_1\", \"tool_name\": \"flights\", \"args\": {{\"origin\": \"LAX\", \"destination\": \"NRT\", \"departure_date\": \"2025-10-01\", \"return_date\": \"2025-10-08\", \"passengers\": 2}}, \"dependencies\": [], \"estimated_cost\": 1200.0, \"estimated_duration_ms\": 5000}}\n\nEnsure the plan is comprehensive for a 4-7 day itinerary, covering flights, lodging, events, and transit. Prioritize gathering core information first.\n\nReturn a JSON object with a 'plan' key containing the list of PlanStep objects and a 'reasoning' key explaining your plan."),
            ("human", "Generate a travel plan.")
        ]).with_structured_output(PlannerOutput)
    
    def __call__(self, state: AgentState) -> Dict[str, Any]:
        constraints = state["constraints"]
        current_plan = state["plan"]
        working_set = state["working_set"]
        
        if not self.llm:
            # Fallback: create a simple plan without LLM
            from app.agent.state import PlanStep
            simple_plan = [
                PlanStep(
                    id="rag_search",
                    tool_name="rag",
                    args={"query": "travel planning", "org_id": state.get("org_id", 1)},
                    dependencies=[],
                    estimated_cost=0,
                    estimated_duration_ms=2000
                )
            ]
            return {
                "plan": simple_plan,
                "working_set": {
                    **working_set,
                    "planner_reasoning": "Created simple fallback plan due to LLM unavailability"
                }
            }
        
        # Convert constraints to a more LLM-friendly format
        formatted_constraints = []
        for c in constraints:
            formatted_constraints.append({"type": c.type.value, "value": c.value, "is_hard": c.is_hard})

        # Convert current_plan to a more LLM-friendly format
        formatted_current_plan = [p.model_dump() for p in current_plan] if current_plan else []

        planner_input = PlannerInput(
            constraints=formatted_constraints,
            current_plan=formatted_current_plan,
            working_set=working_set
        )
        
        try:
            response = self.llm.invoke({
                "tool_schemas": self.tool_schemas,
                "constraints": planner_input.constraints,
                "current_plan": planner_input.current_plan,
                "working_set": planner_input.working_set
            })
            
            new_plan_steps = [PlanStep(**step.model_dump()) for step in response.plan]
            
            return {
                "plan": new_plan_steps,
                "working_set": {
                    **working_set,
                    "planner_reasoning": response.reasoning
                }
            }
        except Exception as e:
            print(f"Error in planner: {e}")
            # Fallback plan
            from app.agent.state import PlanStep
            simple_plan = [
                PlanStep(
                    id="rag_search",
                    tool_name="rag",
                    args={"query": "travel planning", "org_id": state.get("org_id", 1)},
                    dependencies=[],
                    estimated_cost=0,
                    estimated_duration_ms=2000
                )
            ]
            return {
                "plan": simple_plan,
                "working_set": {
                    **working_set,
                    "planner_reasoning": f"Created fallback plan due to error: {str(e)}"
                }
            }

