import streamlit as st
import time
import json
from datetime import datetime, date
from utils.auth import init_session_state, require_auth, check_api_response
from utils.api_client import api_client
from config import STREAMING_ENABLED, PROGRESS_UPDATE_INTERVAL

# Page configuration
st.set_page_config(
    page_title="Travel Planner - Travel Advisory Agent",
    page_icon="🤖",
    layout="wide"
)

# Initialize session state
init_session_state()

# Require authentication
require_auth()

st.title("🤖 Travel Planner Chatbot")
st.markdown("Chat with our AI travel agent to plan your perfect trip using natural language.")

# Initialize session state for chatbot
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "planning_active" not in st.session_state:
    st.session_state.planning_active = False
if "current_run_id" not in st.session_state:
    st.session_state.current_run_id = None
if "current_response" not in st.session_state:
    st.session_state.current_response = None


def display_chat_message(message, is_user=True):
    """Display a chat message with appropriate styling."""
    if is_user:
        with st.chat_message("user"):
            st.write(message)
    else:
        with st.chat_message("assistant"):
            st.write(message)

def display_structured_response(response_data):
    """Display a structured JSON response in a user-friendly format."""
    if not response_data:
        return
    
    # Display the main answer
    if "answer_markdown" in response_data:
        st.markdown("### 📝 Travel Plan")
        st.markdown(response_data["answer_markdown"])
    
    # Display itinerary
    if "itinerary" in response_data and response_data["itinerary"]:
        st.markdown("### 📅 Daily Itinerary")
        itinerary = response_data["itinerary"]
        
        # Show total cost if available
        if "total_cost_usd" in itinerary:
            col1, col2, col3 = st.columns(3)
            with col1:
                # Display cost with proper currency
                currency = itinerary.get('currency', 'USD')
                cost = itinerary['total_cost_usd']
                if currency == 'USD':
                    st.metric("Total Estimated Cost", f"${cost:,.2f}")
                else:
                    st.metric("Total Estimated Cost", f"{currency} {cost:,.2f}")
            with col2:
                st.metric("Duration", f"{itinerary.get('duration_days', 0)} days")
            with col3:
                st.metric("Destination", itinerary.get('destination', 'Unknown'))
        
        # Display each day
        for i, day in enumerate(itinerary.get("days", []), 1):
            with st.expander(f"📅 Day {i} - {day.get('date', 'TBD')}", expanded=True):
                for item in day.get("items", []):
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.markdown(f"**{item.get('start', '')} - {item.get('end', '')}**: {item.get('title', '')}")
                        st.markdown(f"📍 {item.get('location', '')}")
                        if item.get("notes"):
                            st.markdown(f"💡 {item['notes']}")
                    with col2:
                        if item.get("cost"):
                            st.metric("Cost", f"${item['cost']:.2f}")
    
    # Display citations in a more organized way
    if "citations" in response_data and response_data["citations"]:
        st.markdown("### 📚 Sources & References")
        for citation in response_data["citations"]:
            source_icon = "🔗" if citation.get("source") == "url" else "📄" if citation.get("source") == "file" else "🛠️"
            with st.container():
                st.markdown(f"{source_icon} **{citation.get('title', 'Unknown')}**")
                st.caption(f"Source: {citation.get('source', 'unknown')}")
                if citation.get("ref"):
                    st.caption(f"Reference: {citation['ref']}")
    
    # Display tools used in a more compact format
    if "tools_used" in response_data and response_data["tools_used"]:
        st.markdown("### 🛠️ Tools Used")
        tool_cols = st.columns(len(response_data["tools_used"]))
        for i, tool in enumerate(response_data["tools_used"]):
            with tool_cols[i]:
                st.metric(
                    tool.get('name', 'Unknown Tool'),
                    f"{tool.get('count', 0)} calls",
                    f"{tool.get('total_ms', 0)}ms"
                )
    
    # Display decisions in a more visually appealing way
    if "decisions" in response_data and response_data["decisions"]:
        st.markdown("### 🤔 Key Decisions")
        for decision in response_data["decisions"]:
            st.info(f"💡 {decision}")

def show_chatbot_interface():
    """Show the main chatbot interface."""
    # Show welcome message if no chat history
    if not st.session_state.chat_history:
        with st.chat_message("assistant"):
            st.write("👋 Hi! I'm your AI travel planning assistant. I can help you create personalized itineraries based on your preferences, budget, and constraints.")
            # st.write("**Try asking me something like:**")
            # st.write("• 'Plan 5 days in Kyoto next month under $2,500, prefer art museums'")
            # st.write("• 'Family trip to Tokyo with toddler-friendly activities'")
            # st.write("• 'Compare KIX vs ITM for Kyoto trip'")
            # st.write("• 'Make it $300 cheaper while keeping 2 museum days'")
    
    # Display chat history
    for i, message in enumerate(st.session_state.chat_history):
        display_chat_message(message["content"], message["is_user"])
        if not message["is_user"] and message.get("response_data"):
            display_structured_response(message["response_data"])
            
            # Add refinement buttons for assistant responses
            if message.get("response_data") and "itinerary" in message["response_data"]:
                st.markdown("**Want to refine this plan?**")
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button(f"💰 Make it cheaper", key=f"cheaper_{i}"):
                        refinement_prompt = "Make this itinerary cheaper while keeping the main activities"
                        handle_refinement_request(refinement_prompt)
                with col2:
                    if st.button(f"🎨 Add more culture", key=f"culture_{i}"):
                        refinement_prompt = "Add more cultural activities and museums to this itinerary"
                        handle_refinement_request(refinement_prompt)
                with col3:
                    if st.button(f"🍽️ Focus on food", key=f"food_{i}"):
                        refinement_prompt = "Add more food experiences and local cuisine to this itinerary"
                        handle_refinement_request(refinement_prompt)
    
    # Chat input
    if prompt := st.chat_input("Ask me to plan your trip! (e.g., 'Plan 5 days in Kyoto next month under $2,500, prefer art museums')"):
        handle_user_input(prompt)

def handle_user_input(prompt: str):
    """Handle user input and start agent run."""
    # Add user message to chat history
    st.session_state.chat_history.append({
        "content": prompt,
        "is_user": True,
        "timestamp": datetime.now()
    })
    
    # Start agent run
    with st.spinner("🤖 Planning your trip..."):
        response = api_client.start_agent_run(prompt)
    
    if check_api_response(response):
        st.session_state.current_run_id = response["data"]["run_id"]
        st.session_state.planning_active = True
        st.rerun()
    else:
        st.error("❌ Failed to start travel planning. Please try again.")

def handle_refinement_request(refinement_prompt: str):
    """Handle refinement requests by adding context from previous response."""
    if not st.session_state.chat_history:
        return
    
    # Find the last assistant response
    last_assistant_response = None
    for message in reversed(st.session_state.chat_history):
        if not message["is_user"] and message.get("response_data"):
            last_assistant_response = message
            break
    
    if last_assistant_response:
        # Extract destination from previous response
        response_data = last_assistant_response.get("response_data", {})
        itinerary = response_data.get("itinerary", {})
        destination = itinerary.get("destination", "")
        
        # Create a refined prompt with context including destination
        if destination:
            context = f"Based on the previous {destination} itinerary, {refinement_prompt.lower()}"
        else:
            context = f"Based on the previous itinerary, {refinement_prompt.lower()}"
        
        # Add refinement message to chat history
        st.session_state.chat_history.append({
            "content": context,
            "is_user": True,
            "timestamp": datetime.now(),
            "is_refinement": True
        })
        
        # Start agent run with refinement
        with st.spinner("🤖 Refining your itinerary..."):
            response = api_client.start_agent_run(context)
        
        if check_api_response(response):
            st.session_state.current_run_id = response["data"]["run_id"]
            st.session_state.planning_active = True
            st.rerun()
        else:
            st.error("❌ Failed to refine itinerary. Please try again.")


def show_planning_progress():
    """Show the planning progress with streaming updates."""
    # Display chat history first
    for message in st.session_state.chat_history:
        display_chat_message(message["content"], message["is_user"])
        if not message["is_user"] and message.get("response_data"):
            display_structured_response(message["response_data"])
    
    # Show progress indicator
    with st.chat_message("assistant"):
        progress_bar = st.progress(0)
        status_text = st.empty()
        details_text = st.empty()
        
        # Poll for status updates
        response = api_client.get_agent_run_status(st.session_state.current_run_id)
        
        if check_api_response(response):
            status = response["data"]
            
            if status.get("completed"):
                progress_bar.progress(100)
                status_text.text("✅ Planning completed!")
                details_text.text("")
                
                # Add assistant response to chat history
                results = status.get("results", {})
                response_message = "Here's your travel plan!"
                
                # Customize message based on response type (only if results is not None)
                if results and isinstance(results, dict):
                    if results.get("citations") and any(c.get("source") == "file" for c in results["citations"]):
                        response_message = "I found relevant information in our knowledge base!"
                    elif results.get("tools_used") and any(t.get("name") == "Knowledge Base Search" for t in results["tools_used"]):
                        response_message = "I've searched our knowledge base and created a travel plan!"
                    elif results.get("tools_used") and any(t.get("name") == "OpenAI GPT-4o" for t in results["tools_used"]):
                        response_message = "I've used AI assistance to help with your request!"
                
                st.session_state.chat_history.append({
                    "content": response_message,
                    "is_user": False,
                    "timestamp": datetime.now(),
                    "response_data": results
                })
                
                st.session_state.planning_active = False
                st.session_state.current_run_id = None
                st.rerun()
            else:
                # Update progress
                progress = min(status.get("progress", 0), 90)
                progress_bar.progress(progress)
                status_text.text(f"Processing: {status.get('current_step', 'Unknown')}")
                
                # Show additional details based on current step
                current_step = status.get('current_step', '')
                if 'knowledge base' in current_step.lower():
                    details_text.text("🔍 Searching our travel guides and information...")
                elif 'ai assistant' in current_step.lower():
                    details_text.text("🤖 Getting AI assistance for your request...")
                elif 'processing' in current_step.lower() or 'travel request' in current_step.lower():
                    details_text.text("⚙️ Analyzing your travel request...")
                elif 'planning' in current_step.lower():
                    details_text.text("🗺️ Creating your travel plan...")
                else:
                    details_text.text("")
                
                # Auto-refresh to continue polling
                time.sleep(2)
                st.rerun()
        else:
            st.error("❌ Error checking planning status")
            st.session_state.planning_active = False
            st.session_state.current_run_id = None
            st.rerun()


# Main content
if st.session_state.planning_active:
    show_planning_progress()
else:
    show_chatbot_interface()

# Sidebar with tips and examples
with st.sidebar:
    st.header("💡 Chat Examples")
    st.markdown("""
    **Try these natural language queries:**
    
    🏖️ **Basic Planning:**
    - "Plan 5 days in Kyoto next month under $2,500"
    - "I want to visit Paris for a week in spring"
    
    🎨 **With Preferences:**
    - "Plan 3 days in Rome, prefer art museums and avoid overnight flights"
    - "Family trip to Tokyo with toddler-friendly activities"
    
    ✈️ **With Constraints:**
    - "Compare KIX vs ITM for Kyoto trip"
    - "Make it $300 cheaper while keeping 2 museum days"
    
    🍽️ **Special Requirements:**
    - "Vegetarian food options in Barcelona"
    - "Wheelchair accessible activities in London"
    """)
    
    st.header("🤖 What I Can Do")
    st.markdown("""
    - **Search Knowledge Base** for travel guides and information
    - **Use AI Assistant** (GPT-4o) for general travel advice
    - **Parse natural language** queries and extract constraints
    - **Create basic itineraries** from your requirements
    - **Provide citations** and source information
    - **Handle refinements** and follow-up questions
    - **Show progress** and processing steps
    """)
    
    # Chat management
    if st.session_state.chat_history:
        st.header("💬 Chat History")
        if st.button("🗑️ Clear Chat"):
            st.session_state.chat_history = []
            st.rerun()
        
        st.markdown(f"**Messages:** {len(st.session_state.chat_history)}")
    
    # Show available destinations
    if not st.session_state.planning_active:
        st.header("🗺️ Available Destinations")
        destinations_response = api_client.get_available_destinations()
        if destinations_response.get("success"):
            destinations = destinations_response["data"]
            if destinations:
                for dest in destinations[:5]:  # Show first 5
                    source_icon = "📚" if dest.get("source") == "Knowledge Base" else "📍"
                    st.markdown(f"{source_icon} **{dest['name']}**")
                    if dest.get("description"):
                        st.caption(dest["description"])
            else:
                st.info("No destinations available. Add some in the Destinations or Knowledge Base pages.")

# Footer
st.markdown("---")
st.markdown("🤖 **Powered by AI**: Our travel agent uses advanced AI to create personalized itineraries based on your preferences and real-time data.")

