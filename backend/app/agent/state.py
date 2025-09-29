from typing import List, Dict, Any, Optional, TypedDict, Annotated
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class ConstraintType(str, Enum):
    BUDGET = "budget"
    DATES = "dates"
    AIRPORTS = "airports"
    PREFERENCES = "preferences"
    WEATHER = "weather"


class Constraint(BaseModel):
    type: ConstraintType
    value: Any
    is_hard: bool = True  # Hard constraints must be satisfied, soft constraints are preferences


class ToolCall(BaseModel):
    tool_name: str
    args: Dict[str, Any]
    result: Optional[Dict[str, Any]] = None
    duration_ms: Optional[int] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class Violation(BaseModel):
    constraint_type: ConstraintType
    description: str
    severity: str  # "critical", "warning", "info"
    suggested_fix: Optional[str] = None


class Citation(BaseModel):
    title: str
    source: str  # "url", "manual", "file", "tool"
    ref: str  # knowledge_id or tool_name#id
    content_snippet: Optional[str] = None


class BudgetCounter(BaseModel):
    flights: float = 0.0
    lodging: float = 0.0
    activities: float = 0.0
    transport: float = 0.0
    food: float = 0.0
    total: float = 0.0
    currency: str = "USD"


class PlanStep(BaseModel):
    id: str
    tool_name: str
    args: Dict[str, Any]
    dependencies: List[str] = []
    estimated_cost: Optional[float] = None
    estimated_duration_ms: Optional[int] = None
    status: str = "pending"  # "pending", "running", "completed", "failed"


class AgentState(TypedDict):
    # Core state
    messages: Annotated[List[Dict[str, Any]], "Chat messages"]
    constraints: Annotated[List[Constraint], "Extracted constraints"]
    plan: Annotated[List[PlanStep], "Multi-step execution plan"]
    working_set: Annotated[Dict[str, Any], "Intermediate results"]
    citations: Annotated[List[Citation], "Source citations"]
    tool_calls: Annotated[List[ToolCall], "Tool execution history"]
    violations: Annotated[List[Violation], "Constraint violations"]
    budget_counters: Annotated[BudgetCounter, "Budget tracking"]
    done: Annotated[bool, "Completion flag"]
    
    # Metadata
    trace_id: Annotated[str, "Unique trace identifier"]
    user_id: Annotated[Optional[int], "User ID"]
    org_id: Annotated[int, "Organization ID"]
    
    # Progress tracking
    current_step: Annotated[Optional[str], "Current step ID"]
    progress_events: Annotated[List[Dict[str, Any]], "Progress events for streaming"]
    
    # Error handling
    error: Annotated[Optional[str], "Error message if failed"]
    retry_count: Annotated[int, "Number of retries"]
    
    # Final output
    final_itinerary: Annotated[Optional[Dict[str, Any]], "Final itinerary JSON"]
    final_markdown: Annotated[Optional[str], "Final markdown explanation"]

