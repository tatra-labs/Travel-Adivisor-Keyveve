import streamlit as st
from typing import Optional, Dict, Any
from utils.api_client import api_client


def init_session_state():
    """Initialize session state variables."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "access_token" not in st.session_state:
        st.session_state.access_token = None
    if "refresh_token" not in st.session_state:
        st.session_state.refresh_token = None
    if "user_info" not in st.session_state:
        st.session_state.user_info = None


def login(email: str, password: str) -> bool:
    """Attempt to log in the user."""
    response = api_client.login(email, password)
    
    if response["success"]:
        data = response["data"]
        st.session_state.authenticated = True
        st.session_state.access_token = data["access_token"]
        st.session_state.refresh_token = data["refresh_token"]
        
        # Set token in API client
        api_client.set_auth_token(data["access_token"])
        
        # Get user info
        user_response = api_client.get_user_info()
        if user_response["success"]:
            st.session_state.user_info = user_response["data"]
        
        return True
    else:
        st.error(f"Login failed: {response['error']}")
        return False


def logout():
    """Log out the current user."""
    if st.session_state.refresh_token:
        api_client.logout(st.session_state.refresh_token)
    
    # Clear session state
    st.session_state.authenticated = False
    st.session_state.access_token = None
    st.session_state.refresh_token = None
    st.session_state.user_info = None
    
    # Clear API client token
    api_client.clear_auth_token()


def refresh_access_token() -> bool:
    """Refresh the access token using the refresh token."""
    if not st.session_state.refresh_token:
        return False
    
    response = api_client.refresh_token(st.session_state.refresh_token)
    
    if response["success"]:
        data = response["data"]
        st.session_state.access_token = data["access_token"]
        st.session_state.refresh_token = data["refresh_token"]
        
        # Update token in API client
        api_client.set_auth_token(data["access_token"])
        return True
    else:
        # Refresh failed, log out
        logout()
        return False


def require_auth():
    """Decorator-like function to require authentication."""
    if not st.session_state.authenticated:
        st.warning("Please log in to access this page.")
        show_login_form()
        st.stop()


def show_login_form():
    """Display the login form."""
    st.subheader("Login")
    
    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")
        
        if submit:
            if email and password:
                if login(email, password):
                    st.success("Login successful!")
                    st.rerun()
            else:
                st.error("Please enter both email and password.")


def get_current_user() -> Optional[Dict[str, Any]]:
    """Get the current user information."""
    return st.session_state.user_info


def is_admin() -> bool:
    """Check if the current user is an admin."""
    user_info = get_current_user()
    return user_info and user_info.get("role") == "ADMIN"


def check_api_response(response: Dict[str, Any]) -> bool:
    """Check API response and handle authentication errors."""
    if not response["success"]:
        if response.get("status_code") == 401:
            # Token expired, try to refresh
            if refresh_access_token():
                return False  # Indicate retry needed
            else:
                st.error("Session expired. Please log in again.")
                st.rerun()
        else:
            st.error(f"API Error: {response['error']}")
    
    return response["success"]

