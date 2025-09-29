from typing import List, Dict, Any
from app.agent.state import AgentState


class Responder:
    """Assembles the final response payload and handles streaming progress events."""
    
    def __call__(self, state: AgentState) -> Dict[str, Any]:
        # This node primarily prepares the final output and can be used to emit
        # streaming events to the UI. For now, it just passes through the final
        # state, which will be consumed by the API endpoint.
        
        # In a real streaming scenario, this node would yield events.
        # For example:
        # yield {"type": "progress", "node": "responder", "status": "assembling_results"}
        # yield {"type": "final_payload", "payload": state["final_itinerary"]}
        
        return {
            "final_itinerary": state["final_itinerary"],
            "final_markdown": state["final_markdown"],
            "citations": state["citations"],
            "tools_used": state["working_set"].get("synthesizer_output", {}).get("tools_used", []),
            "decisions": state["working_set"].get("synthesizer_output", {}).get("decisions", []),
            "budget_counters": state["budget_counters"],
            "violations": state["violations"],
            "done": True
        }

