from typing import Literal
from langgraph.graph import StateGraph, END, START
# from langgraph.checkpoint.sqlite import SqliteSaver
from app.agent.state import AgentState, ConstraintType
from app.agent.nodes import IntentConstraintExtractor
from app.agent.planner import Planner
from app.agent.router import Router
from app.agent.tool_executor import ToolExecutor
from app.agent.verifier import Verifier
from app.agent.repair import RepairReplan
from app.agent.synthesizer import Synthesizer
from app.agent.responder import Responder


def _is_repair_needed(state: AgentState) -> Literal["repair", "continue"]:
    """Determines if repair is needed based on violations."""
    if state["violations"]:
        return "repair"
    return "continue"


def _should_synthesize(state: AgentState) -> Literal["synthesize", "plan"]:
    """Determines if synthesis can happen or if more planning/execution is needed."""
    plan = state["plan"]
    
    # If there are still pending steps, we need to continue planning/executing
    if any(step.status == "pending" or step.status == "running" for step in plan):
        return "plan"
    
    # If all steps are processed (completed or failed) and no violations, then synthesize
    if all(step.status in ["completed", "failed"] for step in plan) and not state["violations"]:
        return "synthesize"
    
    # Otherwise, go back to planning (e.g., if repair happened and new steps need to be planned)
    return "plan"


class TravelAgentGraph:
    """Defines the LangGraph for the travel advisory agent."""
    
    def __init__(self):
        # self.memory = SqliteSaver.from_conn_string(":memory:")
        self.memory = None # Use in-memory for now
        self.graph = StateGraph(AgentState)
        
        # Define nodes
        self.graph.add_node("extract_constraints", IntentConstraintExtractor())
        self.graph.add_node("plan", Planner())
        self.graph.add_node("route_tools", Router())
        self.graph.add_node("execute_tools", ToolExecutor())
        self.graph.add_node("verify", Verifier())
        self.graph.add_node("repair", RepairReplan())
        self.graph.add_node("synthesize", Synthesizer())
        self.graph.add_node("respond", Responder())
        
        # Define edges
        self.graph.add_edge(START, "extract_constraints")
        self.graph.add_edge("extract_constraints", "plan")
        self.graph.add_edge("plan", "route_tools")
        self.graph.add_edge("route_tools", "execute_tools")
        self.graph.add_edge("execute_tools", "verify")
        
        # Conditional edge from verify
        self.graph.add_conditional_edges(
            "verify",
            _is_repair_needed,
            {
                "repair": "repair",
                "continue": "synthesis_decision" # If no repair, go to synthesis decision
            }
        )
        
        # Conditional edge from repair
        self.graph.add_edge("repair", "plan") # After repair, re-plan
        
        # Add a node for the synthesis decision
        self.graph.add_node("synthesis_decision", _should_synthesize)
        
        # Conditional edge from synthesis_decision
        self.graph.add_conditional_edges(
            "synthesis_decision",
            lambda x: "synthesize" if x.get("should_synthesize", False) else "plan",
            {
                "synthesize": "synthesize",
                "plan": "plan"
            }
        )
        
        self.graph.add_edge("synthesize", "respond")
        self.graph.add_edge("respond", END)
        
        self.app = self.graph.compile()

    def get_app(self):
        return self.app

