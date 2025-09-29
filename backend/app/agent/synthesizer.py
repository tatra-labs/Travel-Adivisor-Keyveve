from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from app.agent.state import AgentState, Citation


class ItineraryItem(BaseModel):
    start: str
    end: str
    title: str
    location: str
    notes: Optional[str] = None


class ItineraryDay(BaseModel):
    date: str
    items: List[ItineraryItem]


class FinalItinerary(BaseModel):
    days: List[ItineraryDay]
    total_cost_usd: float


class SynthesizerOutput(BaseModel):
    answer_markdown: str
    itinerary: FinalItinerary
    citations: List[Citation]
    tools_used: List[Dict[str, Any]]
    decisions: List[str]


class Synthesizer:
    """Synthesizes the final itinerary, markdown, and citations from the working set."""
    
    def __init__(self):
        try:
            from app.core.config import settings
            if hasattr(settings, 'openai_api_key') and settings.openai_api_key:
                self.llm = ChatOpenAI(model="gpt-4o", temperature=0, openai_api_key=settings.openai_api_key)
            else:
                self.llm = None
        except Exception as e:
            print(f"Warning: Could not initialize ChatOpenAI in Synthesizer: {e}")
            self.llm = None
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert travel advisor. Your task is to synthesize a comprehensive travel itinerary in both JSON and Markdown formats, along with relevant citations, based on the provided working set of information. The itinerary should be for a 4-7 day trip.\n\nWorking Set (intermediate results from tools and agent decisions):\n{working_set}\n\nConstraints:\n{constraints}\n\nTool Calls (for tracking usage and durations):\n{tool_calls}\n\nViolations (for understanding repair decisions):\n{violations}\n\nBased on the above information, generate the following:\n1. `answer_markdown`: A detailed, human-readable markdown narrative of the itinerary. Include a summary of the trip, daily plans, and highlight how user preferences were met. Explain any significant decisions made (e.g., why a particular flight or hotel was chosen). Make it engaging and informative.\n2. `itinerary`: A structured JSON object representing the itinerary, adhering to the `FinalItinerary` schema. Ensure all dates and times are correctly formatted.\n3. `citations`: A list of `Citation` objects, linking back to the sources of information (e.g., RAG documents, tool outputs).\n4. `tools_used`: A summary of tools used, including their names, call counts, and total duration.\n5. `decisions`: A list of key decisions made during planning (e.g., \"Chose ITM over KIX due to shorter transfer time\").\n\nEnsure the JSON output is valid and strictly follows the `SynthesizerOutput` schema."),
            ("human", "Synthesize the final travel itinerary.")
        ]).with_structured_output(SynthesizerOutput)
    
    def __call__(self, state: AgentState) -> Dict[str, Any]:
        working_set = state["working_set"]
        constraints = state["constraints"]
        tool_calls = state["tool_calls"]
        violations = state["violations"]
        
        # Prepare tool usage summary
        tools_used_summary = {}
        for tc in tool_calls:
            if tc.tool_name not in tools_used_summary:
                tools_used_summary[tc.tool_name] = {"name": tc.tool_name, "count": 0, "total_ms": 0}
            tools_used_summary[tc.tool_name]["count"] += 1
            if tc.duration_ms: tools_used_summary[tc.tool_name]["total_ms"] += tc.duration_ms
        
        if not self.llm:
            # Fallback: create a simple response without LLM
            from app.agent.state import Citation
            
            # Extract basic information from constraints
            destination = "Kyoto"  # Default
            duration = "5 days"   # Default
            budget = 2500.0      # Default
            
            for constraint in constraints:
                if "Destination:" in str(constraint.value):
                    destination = str(constraint.value).replace("Destination: ", "")
                elif "Duration:" in str(constraint.value):
                    duration = str(constraint.value).replace("Duration: ", "")
                elif constraint.type.value == "budget":
                    budget = constraint.value
            
            # Create simple itinerary
            simple_itinerary = {
                "days": [
                    {
                        "date": "2025-10-01",
                        "items": [
                            {
                                "start": "09:00",
                                "end": "12:00",
                                "title": f"Arrive in {destination}",
                                "location": f"{destination} Airport",
                                "notes": "Flight arrival and airport transfer"
                            },
                            {
                                "start": "14:00",
                                "end": "17:00",
                                "title": "Art Museum Visit",
                                "location": f"{destination} Art Museum",
                                "notes": "Explore local art and culture"
                            }
                        ]
                    }
                ],
                "total_cost_usd": budget
            }
            
            # Create simple markdown response
            markdown_response = f"""# Travel Plan for {destination}

## Trip Overview
- **Destination**: {destination}
- **Duration**: {duration}
- **Budget**: ${budget:,.2f}

## Day 1: Arrival and Art Exploration
- **Morning**: Arrive in {destination} and check into accommodation
- **Afternoon**: Visit local art museums and cultural sites
- **Evening**: Explore local dining options

## Key Features
- Art museum visits as requested
- Budget-conscious planning
- Cultural immersion activities

*This is a basic travel plan. For more detailed recommendations, please provide your OpenAI API key.*"""

            return {
                "final_itinerary": simple_itinerary,
                "final_markdown": markdown_response,
                "citations": [Citation(title="Travel Planning System", source="system", ref="fallback_response")],
                "working_set": {
                    **working_set,
                    "synthesizer_output": {"fallback": True}
                },
                "done": True
            }
        
        try:
            response = self.llm.invoke({
                "working_set": working_set,
                "constraints": [c.model_dump() for c in constraints],
                "tool_calls": [tc.model_dump() for tc in tool_calls],
                "violations": [v.model_dump() for v in violations]
            })
            
            return {
                "final_itinerary": response.itinerary.model_dump(),
                "final_markdown": response.answer_markdown,
                "citations": response.citations,
                "working_set": {
                    **working_set,
                    "synthesizer_output": response.model_dump()
                },
                "done": True
            }
        except Exception as e:
            print(f"Error in synthesizer: {e}")
            # Fallback response on error
            from app.agent.state import Citation
            
            simple_itinerary = {
                "days": [
                    {
                        "date": "2025-10-01",
                        "items": [
                            {
                                "start": "09:00",
                                "end": "12:00",
                                "title": "Travel Planning",
                                "location": "Destination",
                                "notes": "Basic travel plan due to system limitations"
                            }
                        ]
                    }
                ],
                "total_cost_usd": 2500.0
            }
            
            markdown_response = f"""# Travel Planning Response

I understand you're looking for help with travel planning. While I'm experiencing some technical difficulties, I can provide basic guidance.

## Basic Travel Plan
- **Destination**: Based on your request
- **Duration**: As specified
- **Budget**: Within your constraints

*Please try again or contact support for more detailed assistance.*"""

            return {
                "final_itinerary": simple_itinerary,
                "final_markdown": markdown_response,
                "citations": [Citation(title="Travel Planning System", source="system", ref="error_fallback")],
                "working_set": {
                    **working_set,
                    "synthesizer_output": {"error": str(e), "fallback": True}
                },
                "done": True
            }

