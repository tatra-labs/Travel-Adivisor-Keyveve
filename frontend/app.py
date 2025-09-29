import streamlit as st
from utils.auth import init_session_state, require_auth, logout, get_current_user, is_admin
from utils.api_client import api_client
from config import PAGE_TITLE, PAGE_ICON, LAYOUT

# Page configuration
st.set_page_config(
    page_title=PAGE_TITLE,
    page_icon=PAGE_ICON,
    layout=LAYOUT,
    initial_sidebar_state="expanded"
)

# Initialize session state
init_session_state()

# Navigation system (compatible with all Streamlit versions)
def navigate_to_page(page_name):
    """Navigate to a page - provides instructions for older Streamlit versions"""
    try:
        # Try the modern approach first (Streamlit 1.28+)
        if hasattr(st, 'switch_page'):
            if page_name == "travel_planner":
                st.switch_page("pages/3_🤖_Travel_Planner.py")
            elif page_name == "destinations":
                st.switch_page("pages/1_🏖️_Destinations.py")
            elif page_name == "knowledge_base":
                st.switch_page("pages/2_📚_Knowledge_Base.py")
        else:
            # Fallback for older Streamlit versions
            page_display_name = page_name.replace('_', ' ').title()
            st.success(f"✅ Ready to navigate to {page_display_name}!")
            st.info(f"📝 **Instructions**: Please use the sidebar navigation menu or manually navigate to the {page_display_name} page.")
            
            # Show the file path for manual navigation
            if page_name == "travel_planner":
                st.code("pages/3_🤖_Travel_Planner.py")
            elif page_name == "destinations":
                st.code("pages/1_🏖️_Destinations.py")
            elif page_name == "knowledge_base":
                st.code("pages/2_📚_Knowledge_Base.py")
    except Exception as e:
        # If switch_page fails, show helpful message
        page_display_name = page_name.replace('_', ' ').title()
        st.warning(f"⚠️ Navigation to {page_display_name} failed.")
        st.info("Please use the sidebar navigation menu to access different pages.")

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 2rem 0;
        background: linear-gradient(90deg, #1f77b4, #ff7f0e);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-size: 3rem;
        font-weight: bold;
        margin-bottom: 2rem;
    }
    
    .feature-card {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 4px solid #1f77b4;
        margin: 1rem 0;
    }
    
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        text-align: center;
    }
    
    .sidebar-user-info {
        background: #e8f4f8;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    if st.session_state.authenticated:
        user_info = get_current_user()
        if user_info:
            st.markdown(f"""
            <div class="sidebar-user-info">
                <h4>👤 Welcome!</h4>
                <p><strong>{user_info.get('email', 'User')}</strong></p>
                <p>Role: {user_info.get('role', 'MEMBER')}</p>
                <p>Org: {user_info.get('organization', {}).get('name', 'Unknown')}</p>
            </div>
            """, unsafe_allow_html=True)
        
        if st.button("🚪 Logout", use_container_width=True):
            logout()
            st.rerun()
        
        st.markdown("---")
        
        # Navigation menu
        # st.header("🧭 Navigation")
        # st.info("Use the sidebar to navigate between pages")
        
        # if st.button("🏖️ Destinations", use_container_width=True):
        #     navigate_to_page("destinations")
        
        # if st.button("📚 Knowledge Base", use_container_width=True):
        #     navigate_to_page("knowledge_base")
        
        # if st.button("🤖 Travel Planner", use_container_width=True):
        #     navigate_to_page("travel_planner")
        
        st.markdown("---")
        
        # Quick stats
        st.header("📊 Quick Stats")
        
        # Get API health
        health_response = api_client.get_health()
        if health_response.get("success"):
            health_data = health_response["data"]
            st.success("🟢 API Online")
            
            if "stats" in health_data:
                stats = health_data["stats"]
                st.metric("Database", "✅ Connected" if stats.get("database") else "❌ Error")
                st.metric("Embeddings", "✅ Ready" if stats.get("embeddings") else "❌ Error")
        else:
            st.error("🔴 API Offline")
    
    else:
        st.header("🔐 Authentication Required")
        st.info("Please log in to access the travel planning features.")

# Main content
if st.session_state.authenticated:
    # Main dashboard
    st.markdown('<h1 class="main-header">✈️ Travel Advisory Agent</h1>', unsafe_allow_html=True)
    
    st.markdown("""
    Welcome to your AI-powered travel planning assistant! Use the navigation menu to explore different features:
    """)
    
    # Navigation help for older Streamlit versions
    if not hasattr(st, 'switch_page'):
        st.info("💡 **Navigation Tip**: Use the sidebar menu to navigate between pages, or click the quick action buttons below for guided navigation.")
    
    # Feature overview
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="feature-card">
            <h3>🏖️ Destinations</h3>
            <p>Manage your favorite travel destinations and view planning history.</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="feature-card">
            <h3>📚 Knowledge Base</h3>
            <p>Upload travel guides and documents to enhance AI recommendations.</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="feature-card">
            <h3>🤖 Travel Planner</h3>
            <p>Create personalized itineraries with our AI travel agent.</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Recent activity section
    st.subheader("📈 Recent Activity")
    
    # Placeholder for recent activity - in a real app, this would fetch from the API
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        <div class="metric-card">
            <h3>5</h3>
            <p>Destinations</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="metric-card">
            <h3>12</h3>
            <p>Documents</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="metric-card">
            <h3>3</h3>
            <p>Recent Plans</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown("""
        <div class="metric-card">
            <h3>98%</h3>
            <p>Success Rate</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Getting started section
    st.subheader("🚀 Getting Started")
    
    st.markdown("""
    **New to the Travel Advisory Agent?** Here's how to get started:
    
    1. **Add Destinations** 🏖️ - Start by adding your favorite destinations or places you want to visit
    2. **Upload Knowledge** 📚 - Upload travel guides, destination information, or personal notes
    3. **Plan Your Trip** 🤖 - Use the AI planner to create detailed itineraries
    4. **Refine & Export** 📄 - Review, modify, and export your travel plans
    
    The AI agent will use real-time data for flights, weather, events, and more to create the perfect itinerary for you!
    """)
    
    # # Quick actions
    # st.subheader("⚡ Quick Actions")
    
    # col1, col2, col3 = st.columns(3)
    
    # with col1:
    #     if st.button("🆕 Plan New Trip", type="primary", use_container_width=True):
    #         navigate_to_page("travel_planner")
    
    # with col2:
    #     if st.button("➕ Add Destination", use_container_width=True):
    #         navigate_to_page("destinations")
    
    # with col3:
    #     if st.button("📄 Upload Document", use_container_width=True):
    #         navigate_to_page("knowledge_base")

else:
    # Login page
    st.markdown('<h1 class="main-header">✈️ Travel Advisory Agent</h1>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.subheader("🔐 Login")
        
        with st.form("login_form"):
            email = st.text_input("Email", placeholder="Enter your email")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            
            col1, col2 = st.columns(2)
            with col1:
                login_btn = st.form_submit_button("Login", type="primary", use_container_width=True)
            with col2:
                demo_btn = st.form_submit_button("Demo Login", use_container_width=True)
            
            if login_btn:
                if email and password:
                    from utils.auth import login
                    if login(email, password):
                        st.success("Login successful!")
                        st.rerun()
                else:
                    st.error("Please enter both email and password.")
            
            if demo_btn:
                # Demo login with default credentials
                from utils.auth import login
                if login("admin@example.com", "admin123"):
                    st.success("Demo login successful!")
                    st.rerun()
                else:
                    st.error("Demo login failed. Please check if the backend is running.")
        
        st.markdown("---")
        st.info("💡 **Demo Credentials**: admin@example.com / admin123")
        
        # Features preview
        st.subheader("✨ Features")
        st.markdown("""
        - 🤖 **AI-Powered Planning**: Get personalized itineraries based on your preferences
        - 🌍 **Real-Time Data**: Access live flight prices, weather, and event information
        - 📚 **Knowledge Base**: Upload and search through travel documents
        - 🔄 **Streaming Updates**: Watch your itinerary being built in real-time
        - 🛡️ **Secure & Private**: Your data is protected with enterprise-grade security
        """)

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 1rem;">
    <p>Travel Advisory Agent v1.0 | Built with ❤️ using Streamlit and FastAPI</p>
</div>
""", unsafe_allow_html=True)

