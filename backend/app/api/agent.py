from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
import asyncio
import json

from app.core.database import get_db
from app.models.organization import Organization
from app.auth.middleware import get_current_user, CurrentUser
from app.agent.graph import TravelAgentGraph
from app.agent.state import AgentState, Constraint, BudgetCounter, Citation
from app.tools.rag import RAGTool
from app.core.config import settings
try:
    print("=== Importing travel_ai_service ===")
    from app.services.ai_service import travel_ai_service
    print(f"✅ Successfully imported travel_ai_service: {travel_ai_service is not None}")
    if travel_ai_service:
        print(f"Service status - LangGraph: {travel_ai_service.langgraph_app is not None}")
        print(f"Service status - OpenAI: {travel_ai_service.llm is not None}")
        print(f"Service status - Agent: {travel_ai_service.agent is not None}")
    else:
        print("⚠️ travel_ai_service is None")
except ImportError as e:
    print(f"❌ Warning: Could not import travel_ai_service: {e}")
    import traceback
    print(f"Import traceback: {traceback.format_exc()}")
    travel_ai_service = None
import openai

router = APIRouter(prefix="/agent", tags=["agent"])


class AgentRunRequest(BaseModel):
    message: str = Field(..., description="User message for the agent")
    constraints: Optional[Dict[str, Any]] = Field(None, description="Planning constraints")


class AgentRunResponse(BaseModel):
    run_id: str
    status: str
    message: str


class AgentRunStatus(BaseModel):
    run_id: str
    status: str
    progress: int
    current_step: Optional[str] = None
    completed: bool = False
    results: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class AgentStreamUpdate(BaseModel):
    type: str  # "node_start", "tool_call", "decision", "completion", "error"
    node: Optional[str] = None
    tool_name: Optional[str] = None
    decision: Optional[str] = None
    results: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# In-memory storage for agent runs (in production, use Redis or database)
agent_runs: Dict[str, Dict[str, Any]] = {}


@router.post("/run", response_model=AgentRunResponse)
async def start_agent_run(
    request: AgentRunRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """Start a new agent run for travel planning."""
    try:
        # Generate unique run ID
        run_id = str(uuid.uuid4())
        
        # Initialize agent state
        initial_state = {
            "messages": [{"role": "user", "content": request.message}],
            "constraints": request.constraints or [],
            "plan": None,
            "working_set": {},
            "citations": [],
            "tool_calls": [],
            "violations": [],
            "budget_counters": {"total": 0, "flights": 0, "lodging": 0, "activities": 0, "transport": 0, "food": 0, "currency": "USD"},
            "done": False,
            "trace_id": run_id,
            "user_id": current_user.user_id,
            "org_id": current_user.org_id,
            "current_step": "constraint_extraction",
            "progress_events": [],
            "error": None,
            "retry_count": 0,
            "final_itinerary": None,
            "final_markdown": None
        }
        
        # Store run in memory
        agent_runs[run_id] = {
            "run_id": run_id,
            "status": "running",
            "progress": 0,
            "current_step": "Initializing...",
            "completed": False,
            "results": None,
            "error": None,
            "state": initial_state,
            "user_id": current_user.user_id,
            "org_id": current_user.org_id,
            "created_at": datetime.utcnow()
        }
        
        # Start the agent run asynchronously
        asyncio.create_task(run_agent_async(run_id, initial_state, current_user.org_id))
        
        return AgentRunResponse(
            run_id=run_id,
            status="started",
            message="Agent run started successfully"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error starting agent run: {str(e)}"
        )


@router.get("/run/{run_id}/status", response_model=AgentRunStatus)
async def get_agent_run_status(
    run_id: str,
    current_user: CurrentUser = Depends(get_current_user)
):
    """Get the status of an agent run."""
    if run_id not in agent_runs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent run not found"
        )
    
    run_data = agent_runs[run_id]
    
    # Check if user has access to this run
    if run_data["user_id"] != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this agent run"
        )
    
    return AgentRunStatus(
        run_id=run_id,
        status=run_data["status"],
        progress=run_data["progress"],
        current_step=run_data["current_step"],
        completed=run_data["completed"],
        results=run_data["results"],
        error=run_data["error"]
    )


@router.get("/run/{run_id}/stream")
async def stream_agent_run(
    run_id: str,
    current_user: CurrentUser = Depends(get_current_user)
):
    """Stream updates from an agent run."""
    if run_id not in agent_runs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent run not found"
        )
    
    run_data = agent_runs[run_id]
    
    # Check if user has access to this run
    if run_data["user_id"] != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this agent run"
        )
    
    # For now, return a simple streaming response
    # In a real implementation, you'd use Server-Sent Events (SSE)
    return {"message": "Streaming not fully implemented yet", "run_id": run_id}


async def run_agent_async(run_id: str, initial_state: AgentState, org_id: int):
    """Run the agent asynchronously."""
    user_query = ""  # Initialize user_query to avoid UnboundLocalError
    try:
        # Update status
        agent_runs[run_id]["status"] = "running"
        agent_runs[run_id]["current_step"] = "Processing your travel request..."
        agent_runs[run_id]["progress"] = 20
        
        # Get user query - AgentState is a TypedDict (dictionary)
        if isinstance(initial_state, dict) and 'messages' in initial_state and initial_state['messages']:
            user_query = initial_state['messages'][0]["content"]
        else:
            user_query = "Travel planning request"
        
        # Update status
        agent_runs[run_id]["current_step"] = "Searching knowledge base and planning..."
        agent_runs[run_id]["progress"] = 50
        
        # Use the new AI service to process the query
        print(f"=== Processing query in run_agent_async ===")
        print(f"travel_ai_service available: {travel_ai_service is not None}")
        if travel_ai_service:
            print("✅ travel_ai_service is available, processing query...")
            from app.core.database import SessionLocal
            db = SessionLocal()
            try:
                results = travel_ai_service.process_travel_query(db, org_id, user_query)
                print(f"✅ Query processed successfully, results type: {type(results)}")
                print(f"Results keys: {list(results.keys()) if isinstance(results, dict) else 'Not a dict'}")
            finally:
                db.close()
        else:
            print("⚠️ travel_ai_service is not available, using fallback response")
            # Fallback to simple response if AI service is not available
            results = {
                "answer_markdown": f"# Travel Planning Response\n\nI'm currently setting up my travel planning capabilities. Please try again in a moment.\n\nYour query: \"{user_query}\"",
                "itinerary": None,
                "citations": [],
                "tools_used": [],
                "decisions": ["AI service not available - using fallback response"]
            }
        
        # Update final status
        agent_runs[run_id]["status"] = "completed"
        agent_runs[run_id]["current_step"] = "Completed"
        agent_runs[run_id]["progress"] = 100
        agent_runs[run_id]["completed"] = True
        agent_runs[run_id]["results"] = results
        
    except Exception as e:
        # Update error status
        agent_runs[run_id]["status"] = "error"
        agent_runs[run_id]["error"] = str(e)
        agent_runs[run_id]["completed"] = True
        # Provide fallback results even on error
        agent_runs[run_id]["results"] = {
            "answer_markdown": f"# Travel Planning Response\n\nI apologize, but I encountered an error while processing your request: \"{user_query}\"\n\nPlease try again or rephrase your question.",
            "itinerary": None,
            "citations": [],
            "tools_used": [],
            "decisions": ["Error occurred during processing"]
        }


def parse_natural_language_query(message: str) -> Dict[str, Any]:
    """Parse natural language query to extract travel planning constraints."""
    import re
    from datetime import datetime, timedelta
    
    constraints = {}
    message_lower = message.lower()
    
    # Extract destination
    destination_patterns = [
        r'(?:to|in|visit|travel to)\s+([a-zA-Z\s]+?)(?:\s|,|$|under|\$|next|prefer|avoid)',
        r'([a-zA-Z\s]+?)\s+(?:trip|visit|travel)',
        r'(?:plan|trip to)\s+([a-zA-Z\s]+?)(?:\s|,|$|under|\$|next|prefer|avoid)'
    ]
    
    for pattern in destination_patterns:
        match = re.search(pattern, message_lower)
        if match:
            destination = match.group(1).strip()
            # Clean up common words
            destination = re.sub(r'\b(?:a|an|the|for|with|and|or|but)\b', '', destination).strip()
            if len(destination) > 2:  # Avoid very short matches
                constraints["destination"] = destination.title()
                break
    
    # Extract duration
    duration_patterns = [
        r'(\d+)\s*(?:day|days)',
        r'(\d+)\s*(?:night|nights)',
        r'(\d+)\s*(?:week|weeks)'
    ]
    
    for pattern in duration_patterns:
        match = re.search(pattern, message_lower)
        if match:
            duration = int(match.group(1))
            if 'week' in pattern:
                duration *= 7  # Convert weeks to days
            constraints["duration_days"] = duration
            break
    
    # Extract budget
    budget_patterns = [
        r'\$(\d+(?:,\d{3})*(?:\.\d{2})?)',
        r'under\s*\$(\d+(?:,\d{3})*(?:\.\d{2})?)',
        r'budget\s*of\s*\$(\d+(?:,\d{3})*(?:\.\d{2})?)',
        r'(\d+(?:,\d{3})*(?:\.\d{2})?)\s*dollars?'
    ]
    
    for pattern in budget_patterns:
        match = re.search(pattern, message_lower)
        if match:
            budget_str = match.group(1).replace(',', '')
            constraints["budget_usd"] = float(budget_str)
            break
    
    # Extract interests/preferences
    interests = []
    interest_keywords = {
        'museums': ['museum', 'museums', 'art museum', 'art museums'],
        'art galleries': ['art gallery', 'art galleries', 'gallery', 'galleries'],
        'historical sites': ['historical', 'history', 'historic', 'heritage'],
        'nature': ['nature', 'outdoor', 'hiking', 'parks', 'natural'],
        'food & dining': ['food', 'dining', 'restaurant', 'cuisine', 'eat'],
        'shopping': ['shopping', 'shop', 'market', 'mall'],
        'nightlife': ['nightlife', 'night life', 'bars', 'clubs'],
        'adventure sports': ['adventure', 'sports', 'extreme', 'thrilling'],
        'beaches': ['beach', 'beaches', 'coastal', 'seaside'],
        'architecture': ['architecture', 'buildings', 'monuments', 'landmarks']
    }
    
    for interest, keywords in interest_keywords.items():
        if any(keyword in message_lower for keyword in keywords):
            interests.append(interest)
    
    if interests:
        constraints["interests"] = interests
    
    # Extract travel style
    if any(word in message_lower for word in ['budget', 'cheap', 'affordable']):
        constraints["travel_style"] = "Budget"
    elif any(word in message_lower for word in ['luxury', 'expensive', 'high-end']):
        constraints["travel_style"] = "Luxury"
    elif any(word in message_lower for word in ['backpacking', 'backpack']):
        constraints["travel_style"] = "Backpacking"
    else:
        constraints["travel_style"] = "Mid-range"
    
    # Extract group type
    if any(word in message_lower for word in ['family', 'kids', 'children', 'toddler']):
        constraints["group_type"] = "Family with kids"
    elif any(word in message_lower for word in ['couple', 'romantic']):
        constraints["group_type"] = "Couple"
    elif any(word in message_lower for word in ['friends', 'group']):
        constraints["group_type"] = "Friends"
    elif any(word in message_lower for word in ['business', 'work']):
        constraints["group_type"] = "Business"
    else:
        constraints["group_type"] = "Solo"
    
    # Extract special requirements
    special_requirements = []
    if any(word in message_lower for word in ['vegetarian', 'vegan']):
        special_requirements.append("Vegetarian food options")
    if any(word in message_lower for word in ['wheelchair', 'accessible', 'disability']):
        special_requirements.append("Wheelchair accessible")
    if any(word in message_lower for word in ['avoid overnight', 'no overnight', 'daytime flights']):
        constraints["avoid_overnight_flights"] = True
    if any(word in message_lower for word in ['kid-friendly', 'toddler-friendly', 'family-friendly']):
        constraints["kid_friendly"] = True
    
    if special_requirements:
        constraints["special_requirements"] = special_requirements
    
    # Extract departure airport
    airport_pattern = r'(?:from|departure|departing from)\s+([A-Z]{3})'
    match = re.search(airport_pattern, message_lower)
    if match:
        constraints["departure_airport"] = match.group(1).upper()
    
    # Extract time references
    if 'next month' in message_lower:
        next_month = datetime.now() + timedelta(days=30)
        constraints["start_date"] = next_month.strftime("%Y-%m-%d")
    elif 'next week' in message_lower:
        next_week = datetime.now() + timedelta(days=7)
        constraints["start_date"] = next_week.strftime("%Y-%m-%d")
    elif 'spring' in message_lower:
        # Default to March for spring
        spring_date = datetime(datetime.now().year, 3, 15)
        constraints["start_date"] = spring_date.strftime("%Y-%m-%d")
    elif 'summer' in message_lower:
        # Default to June for summer
        summer_date = datetime(datetime.now().year, 6, 15)
        constraints["start_date"] = summer_date.strftime("%Y-%m-%d")
    
    return constraints


def generate_knowledge_base_response(user_query: str, rag_results: List, initial_state: AgentState) -> Dict[str, Any]:
    """Generate response using knowledge base information."""
    # Extract destination from query
    destination = extract_destination_from_query(user_query)
    
    # Build response from knowledge base results
    knowledge_content = "\n\n".join([result.content_snippet for result in rag_results])
    
    # Create citations from RAG results
    citations = []
    for result in rag_results:
        citations.append({
            "title": result.title,
            "source": result.source_type,
            "ref": f"knowledge_item_{result.knowledge_item_id}"
        })
    
    # Generate markdown response
    answer_markdown = f"""# Travel Information for {destination or 'Your Destination'}

Based on our knowledge base, here's what I found:

{knowledge_content}

## Key Information
- **Source**: Knowledge Base
- **Relevance**: High (based on semantic search)
- **Last Updated**: Recent

## Next Steps
If you'd like me to create a detailed itinerary based on this information, please let me know your specific requirements like:
- Duration of stay
- Budget constraints
- Specific interests or activities
- Travel dates"""
    
    return {
        "answer_markdown": answer_markdown,
        "itinerary": None,  # No structured itinerary from knowledge base alone
        "citations": citations,
        "tools_used": [{
            "name": "RAGTool",
            "count": 1,
            "total_ms": 500
        }],
        "decisions": [
            f"Found relevant information in knowledge base for {destination or 'your query'}",
            "Used semantic search to retrieve most relevant content",
            "Presented information from trusted sources"
        ]
    }

async def generate_openai_response(user_query: str, initial_state: AgentState) -> Dict[str, Any]:
    """Generate response using OpenAI GPT-4o."""
    if not settings.openai_api_key:
        return generate_fallback_response(user_query, "OpenAI API key not configured")
    
    try:
        # Initialize OpenAI client
        client = openai.OpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_api_base
        )
        
        # Create a prompt for travel planning
        system_prompt = """You are a helpful travel planning assistant. When users ask about travel planning, provide helpful and accurate information. 

If you can help with travel planning, provide a structured response. If the query is not about travel or you cannot help, politely explain that you're a travel planning assistant and suggest how you can help.

Always be kind, polite, and helpful. If you don't have specific information about a destination, suggest general travel planning tips or ask for more details."""
        
        # Make API call to OpenAI
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_query}
            ],
            max_tokens=1000,
            temperature=0.7
        )
        
        ai_response = response.choices[0].message.content
        
        # Check if this is a travel planning query
        if is_travel_planning_query(user_query):
            # Try to extract constraints and create a basic itinerary
            constraints = parse_natural_language_query(user_query)
            itinerary = create_basic_itinerary(constraints)
            
            return {
                "answer_markdown": f"""# AI Travel Assistant Response

{ai_response}

## Travel Planning Information
Based on your query, I've identified the following details:
- **Destination**: {constraints.get('destination', 'Not specified')}
- **Duration**: {constraints.get('duration_days', 'Not specified')} days
- **Budget**: ${constraints.get('budget_usd', 'Not specified')}
- **Interests**: {', '.join(constraints.get('interests', [])) if constraints.get('interests') else 'Not specified'}

## Next Steps
For a detailed itinerary with specific recommendations, I'd need access to real-time data about flights, accommodations, and local attractions. The knowledge base doesn't contain specific information about this destination, but I can provide general travel advice.""",
                "itinerary": itinerary,
                "citations": [{
                    "title": "AI Travel Assistant",
                    "source": "tool",
                    "ref": "OpenAI GPT-4o"
                }],
                "tools_used": [{
                    "name": "OpenAI GPT-4o",
                    "count": 1,
                    "total_ms": 2000
                }],
                "decisions": [
                    "Used AI assistant for general travel advice",
                    "No specific knowledge base information found",
                    "Provided helpful guidance based on query analysis"
                ]
            }
        else:
            # Not a travel planning query
            return {
                "answer_markdown": f"""# AI Assistant Response

{ai_response}

## Note
I'm a travel planning assistant, so I'm most helpful with questions about:
- Travel planning and itineraries
- Destination recommendations
- Budget planning for trips
- Travel tips and advice

If you have travel-related questions, I'd be happy to help!""",
                "itinerary": None,
                "citations": [{
                    "title": "AI Assistant",
                    "source": "tool",
                    "ref": "OpenAI GPT-4o"
                }],
                "tools_used": [{
                    "name": "OpenAI GPT-4o",
                    "count": 1,
                    "total_ms": 2000
                }],
                "decisions": [
                    "Query not specifically about travel planning",
                    "Provided helpful general response",
                    "Suggested travel-related assistance"
                ]
            }
            
    except Exception as e:
        print(f"OpenAI API error: {e}")
        return generate_fallback_response(user_query, str(e))

def generate_fallback_response(user_query: str, error: str = None) -> Dict[str, Any]:
    """Generate a fallback response when OpenAI is not available."""
    return {
        "answer_markdown": f"""# Travel Planning Assistant

I apologize, but I'm currently unable to process your request: "{user_query}"

{f"Error: {error}" if error else ""}

## How I Can Help
I'm a travel planning assistant that can help with:
- Creating travel itineraries
- Finding information from our knowledge base
- Providing travel tips and recommendations
- Budget planning for trips

## Available Information
I can search through our knowledge base for travel guides and information. If you have specific travel questions, please try rephrasing your query or ask about:
- Specific destinations
- Travel planning for particular dates
- Budget considerations
- Activity preferences

Would you like to try a different travel-related question?""",
        "itinerary": None,
        "citations": [],
        "tools_used": [],
        "decisions": [
            "Unable to process request with current tools",
            "Provided fallback response with helpful suggestions"
        ]
    }

def is_travel_planning_query(query: str) -> bool:
    """Check if the query is about travel planning."""
    travel_keywords = [
        'plan', 'trip', 'travel', 'visit', 'destination', 'itinerary',
        'vacation', 'holiday', 'journey', 'flight', 'hotel', 'accommodation',
        'budget', 'cost', 'days', 'weeks', 'museums', 'activities'
    ]
    query_lower = query.lower()
    return any(keyword in query_lower for keyword in travel_keywords)

def extract_destination_from_query(query: str) -> str:
    """Extract destination from query."""
    constraints = parse_natural_language_query(query)
    return constraints.get("destination", "Unknown")

def create_basic_itinerary(constraints: Dict[str, Any]) -> Dict[str, Any]:
    """Create a basic itinerary structure from constraints."""
    destination = constraints.get("destination", "Unknown Destination")
    duration = constraints.get("duration_days", 3)
    budget = constraints.get("budget_usd", 1000)
    
    # Create basic daily structure
    days = []
    for i in range(duration):
        days.append({
            "date": f"Day {i+1}",
            "items": [
                {
                    "start": "09:00",
                    "end": "12:00",
                    "title": f"Morning Activity",
                    "location": f"{destination}",
                    "notes": "Explore local attractions",
                    "cost": budget * 0.1 / duration
                },
                {
                    "start": "14:00",
                    "end": "17:00",
                    "title": f"Afternoon Activity",
                    "location": f"{destination}",
                    "notes": "Cultural or recreational activity",
                    "cost": budget * 0.15 / duration
                },
                {
                    "start": "19:00",
                    "end": "21:00",
                    "title": f"Dinner",
                    "location": f"{destination}",
                    "notes": "Local cuisine experience",
                    "cost": budget * 0.2 / duration
                }
            ]
        })
    
    return {
        "destination": destination,
        "duration_days": duration,
        "total_cost_usd": budget * 0.8,  # 80% of budget
        "days": days
    }

def generate_mock_results(state: AgentState) -> Dict[str, Any]:
    """Generate mock results in the structured JSON format."""
    destination = state.constraints.get("destination", "Unknown Destination")
    duration = state.constraints.get("duration_days", 5)
    budget = state.constraints.get("budget_usd", 2000)
    
    # Generate daily itinerary
    days = []
    for i in range(duration):
        day_date = datetime.now().strftime("%Y-%m-%d")
        day_items = [
            {
                "start": "09:00",
                "end": "10:30",
                "title": f"Morning Activity Day {i+1}",
                "location": f"{destination} City Center",
                "notes": "Great way to start your day",
                "cost": 25.00
            },
            {
                "start": "11:00",
                "end": "12:30",
                "title": f"Cultural Site Visit Day {i+1}",
                "location": f"{destination} Historic District",
                "notes": "Don't forget your camera",
                "cost": 15.00
            },
            {
                "start": "14:00",
                "end": "16:00",
                "title": f"Local Experience Day {i+1}",
                "location": f"{destination} Local Area",
                "notes": "Authentic local experience",
                "cost": 35.00
            },
            {
                "start": "18:00",
                "end": "20:00",
                "title": f"Dinner Day {i+1}",
                "location": f"{destination} Restaurant District",
                "notes": "Try the local specialties",
                "cost": 45.00
            }
        ]
        
        days.append({
            "date": day_date,
            "items": day_items
        })
    
    # Calculate total cost
    total_cost = budget * 0.9  # 90% of budget used
    
    return {
        "answer_markdown": f"""
# {duration}-Day Trip to {destination}

## Overview
This personalized itinerary for {destination} has been carefully crafted based on your preferences and budget of ${budget}. The plan includes a perfect mix of cultural experiences, local cuisine, and relaxation time.

## Highlights
- **Duration**: {duration} days
- **Budget**: ${budget} (Total estimated: ${total_cost:.2f})
- **Style**: {state.constraints.get('travel_style', 'Mid-range')}
- **Group**: {state.constraints.get('group_type', 'Solo')}

## Daily Breakdown
Each day includes a mix of cultural experiences, local cuisine, and relaxation time. The itinerary has been optimized for your interests and budget constraints.

## Budget Breakdown
- **Accommodation**: ${budget * 0.4:.2f}
- **Food**: ${budget * 0.3:.2f}
- **Activities**: ${budget * 0.2:.2f}
- **Transportation**: ${budget * 0.1:.2f}

## Tips
- Book accommodations in advance for better rates
- Try local transportation to save money
- Keep some budget for unexpected experiences
- Check weather forecasts before departure
        """,
        "itinerary": {
            "destination": destination,
            "duration_days": duration,
            "total_cost_usd": total_cost,
            "days": days
        },
        "citations": [
            {
                "title": f"{destination} Travel Guide",
                "source": "file",
                "ref": "knowledge_base_guide.pdf"
            },
            {
                "title": "Flight Search Results",
                "source": "tool",
                "ref": "FlightsTool API"
            },
            {
                "title": "Hotel Recommendations",
                "source": "tool",
                "ref": "LodgingTool API"
            },
            {
                "title": "Weather Forecast",
                "source": "tool",
                "ref": "WeatherTool API"
            }
        ],
        "tools_used": [
            {
                "name": "FlightsTool",
                "count": 3,
                "total_ms": 1250
            },
            {
                "name": "LodgingTool",
                "count": 2,
                "total_ms": 980
            },
            {
                "name": "WeatherTool",
                "count": 1,
                "total_ms": 450
            },
            {
                "name": "RAGTool",
                "count": 1,
                "total_ms": 750
            }
        ],
        "decisions": [
            f"Chose {destination} based on your preferences and budget",
            "Selected mid-range accommodations to stay within budget",
            "Prioritized cultural sites over shopping based on interests",
            "Avoided overnight flights as requested",
            "Included family-friendly activities for toddler"
        ]
    }
