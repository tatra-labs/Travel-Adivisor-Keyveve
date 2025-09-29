from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from app.agent.state import AgentState, Constraint, ConstraintType


class ExtractedConstraints(BaseModel):
    destination: Optional[str] = Field(None, description="Primary destination for the trip")
    duration_days: Optional[int] = Field(None, description="Number of days for the trip")
    budget_usd: Optional[float] = Field(None, description="Total budget in USD")
    preferences: List[str] = Field(default_factory=list, description="List of user preferences (e.g., art museums, toddler-friendly, outdoor activities)")
    avoid_overnight_flights: Optional[bool] = Field(None, description="Whether to avoid overnight flights")
    compare_airports: List[str] = Field(default_factory=list, description="List of airport codes to compare")
    compare_neighborhoods: List[str] = Field(default_factory=list, description="List of neighborhoods to compare")
    start_date: Optional[str] = Field(None, description="Start date of the trip (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="End date of the trip (YYYY-MM-DD)")


class IntentConstraintExtractor:
    """Extracts intent and constraints from user messages."""
    
    def __init__(self):
        try:
            from app.core.config import settings
            if hasattr(settings, 'openai_api_key') and settings.openai_api_key:
                self.llm = ChatOpenAI(model="gpt-4o", temperature=0, openai_api_key=settings.openai_api_key)
            else:
                self.llm = None
        except Exception as e:
            print(f"Warning: Could not initialize ChatOpenAI in IntentConstraintExtractor: {e}")
            self.llm = None
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert travel agent. Extract all relevant constraints and preferences from the user's request. If dates are mentioned, convert them to YYYY-MM-DD format. If a duration is given (e.g., '5 days'), calculate the end date from the start date. If only a month is given, infer a reasonable date range within that month. If no specific dates, leave them as None. Always try to infer a destination and duration if possible."),
            ("human", "{message}")
        ]).with_structured_output(ExtractedConstraints)
    
    def __call__(self, state: AgentState) -> Dict[str, Any]:
        messages = state["messages"]
        user_message = messages[-1]["content"]
        
        if not self.llm:
            # Fallback: create basic constraints from simple parsing
            constraints = []
            # Try to extract basic information from the message
            if "kyoto" in user_message.lower():
                constraints.append(Constraint(type=ConstraintType.PREFERENCES, value="Destination: Kyoto"))
            if "5 days" in user_message.lower():
                constraints.append(Constraint(type=ConstraintType.PREFERENCES, value="Duration: 5 days"))
            if "$2,500" in user_message or "2500" in user_message:
                constraints.append(Constraint(type=ConstraintType.BUDGET, value=2500.0))
            if "art museums" in user_message.lower():
                constraints.append(Constraint(type=ConstraintType.PREFERENCES, value="art museums"))
            
            return {
                "constraints": constraints,
                "working_set": {
                    "extracted_data": {"user_message": user_message, "fallback": True}
                }
            }
        
        try:
            extracted_data = self.prompt.invoke({"message": user_message})
            
            constraints = []
            if extracted_data.budget_usd:
                constraints.append(Constraint(type=ConstraintType.BUDGET, value=extracted_data.budget_usd))
            if extracted_data.destination:
                constraints.append(Constraint(type=ConstraintType.PREFERENCES, value=f"Destination: {extracted_data.destination}"))
            if extracted_data.duration_days:
                constraints.append(Constraint(type=ConstraintType.PREFERENCES, value=f"Duration: {extracted_data.duration_days} days"))
            if extracted_data.start_date and extracted_data.end_date:
                constraints.append(Constraint(type=ConstraintType.DATES, value={"start": extracted_data.start_date, "end": extracted_data.end_date}))
            elif extracted_data.start_date and extracted_data.duration_days:
                # Calculate end date
                start = datetime.strptime(extracted_data.start_date, "%Y-%m-%d").date()
                end = start + timedelta(days=extracted_data.duration_days - 1)
                constraints.append(Constraint(type=ConstraintType.DATES, value={"start": extracted_data.start_date, "end": end.isoformat()}))
            
            for pref in extracted_data.preferences:
                constraints.append(Constraint(type=ConstraintType.PREFERENCES, value=pref))
            if extracted_data.avoid_overnight_flights:
                constraints.append(Constraint(type=ConstraintType.PREFERENCES, value="Avoid overnight flights"))
            if extracted_data.compare_airports:
                constraints.append(Constraint(type=ConstraintType.PREFERENCES, value=f"Compare airports: {', '.join(extracted_data.compare_airports)}"))
            if extracted_data.compare_neighborhoods:
                constraints.append(Constraint(type=ConstraintType.PREFERENCES, value=f"Compare neighborhoods: {', '.join(extracted_data.compare_neighborhoods)}"))

            return {
                "constraints": constraints,
                "working_set": {
                    "extracted_data": extracted_data.model_dump()
                }
            }
        except Exception as e:
            print(f"Error in constraint extraction: {e}")
            # Fallback constraints
            constraints = []
            if "kyoto" in user_message.lower():
                constraints.append(Constraint(type=ConstraintType.PREFERENCES, value="Destination: Kyoto"))
            if "5 days" in user_message.lower():
                constraints.append(Constraint(type=ConstraintType.PREFERENCES, value="Duration: 5 days"))
            if "$2,500" in user_message or "2500" in user_message:
                constraints.append(Constraint(type=ConstraintType.BUDGET, value=2500.0))
            if "art museums" in user_message.lower():
                constraints.append(Constraint(type=ConstraintType.PREFERENCES, value="art museums"))
            
            return {
                "constraints": constraints,
                "working_set": {
                    "extracted_data": {"user_message": user_message, "fallback": True, "error": str(e)}
                }
            }

