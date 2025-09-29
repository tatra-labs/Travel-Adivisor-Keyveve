import streamlit as st
import pandas as pd
from utils.auth import init_session_state, require_auth, check_api_response, is_admin
from utils.api_client import api_client

# Page configuration
st.set_page_config(
    page_title="Destinations - Travel Advisory Agent",
    page_icon="🏖️",
    layout="wide"
)

# Initialize session state
init_session_state()

# Require authentication
require_auth()

st.title("🏖️ Destinations")
st.markdown("Manage travel destinations and view planning history.")

# Initialize show_add_form if not exists
if "show_add_form" not in st.session_state:
    st.session_state.show_add_form = False

# Sidebar for actions
with st.sidebar:
    st.header("Actions")
    
    if is_admin():
        if st.button("➕ Add New Destination"):
            st.session_state.show_add_form = True
    
    if st.button("📋 View Destinations"):
        st.session_state.show_add_form = False
        st.rerun()
    
    if st.button("🔄 Refresh"):
        st.rerun()


def show_edit_destination_form():
    """Show form to edit an existing destination."""
    if "edit_destination_data" not in st.session_state:
        st.error("No destination data found for editing.")
        return
    
    dest_data = st.session_state.edit_destination_data
    dest_id = st.session_state.edit_destination_id
    
    st.subheader(f"✏️ Edit Destination: {dest_data['name']}")
    
    with st.form("edit_destination_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            name = st.text_input("Destination Name*", value=dest_data.get("name", ""), placeholder="e.g., Tokyo, Japan")
            country = st.text_input("Country*", value=dest_data.get("country", ""), placeholder="e.g., Japan")
            
        with col2:
            city = st.text_input("City*", value=dest_data.get("city", ""), placeholder="e.g., Tokyo")
            tags = st.text_input("Tags (comma-separated)", 
                               value=", ".join(dest_data.get("tags", [])), 
                               placeholder="e.g., culture, food, temples", 
                               help="Add tags to help categorize this destination")
        
        description = st.text_area("Description", 
                                 value=dest_data.get("description", ""), 
                                 placeholder="Brief description of what makes this destination special...", 
                                 help="Optional: Describe what makes this destination unique or what activities are popular there")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            submit = st.form_submit_button("💾 Save Changes", type="primary")
        with col2:
            cancel = st.form_submit_button("❌ Cancel")
        with col3:
            if st.form_submit_button("🗑️ Delete Destination"):
                st.session_state.delete_destination_id = dest_id
                st.rerun()
        
        if cancel:
            # Clear edit state
            if "edit_destination_id" in st.session_state:
                del st.session_state.edit_destination_id
            if "edit_destination_data" in st.session_state:
                del st.session_state.edit_destination_data
            st.rerun()
        
        if submit:
            if name and country and city:
                with st.spinner("💾 Updating destination..."):
                    destination_data = {
                        "name": name,
                        "country": country,
                        "city": city,
                        "tags": [tag.strip() for tag in tags.split(",") if tag.strip()],
                        "description": description or None
                    }
                    
                    response = api_client.update_destination(dest_id, destination_data)
                
                if check_api_response(response):
                    st.success("✅ Destination updated successfully!")
                    # Clear edit state
                    if "edit_destination_id" in st.session_state:
                        del st.session_state.edit_destination_id
                    if "edit_destination_data" in st.session_state:
                        del st.session_state.edit_destination_data
                    st.rerun()
                else:
                    st.error("❌ Failed to update destination. Please try again.")
            else:
                st.error("❌ Please fill in all required fields (Name, Country, and City).")


def show_destination_stats():
    """Show statistics for a selected destination."""
    if "view_stats_id" not in st.session_state:
        st.error("No destination selected for statistics.")
        return
    
    dest_id = st.session_state.view_stats_id
    
    # Get destination data
    response = api_client.get_destination(dest_id)
    if not check_api_response(response):
        st.error("❌ Failed to load destination data.")
        return
    
    dest_data = response["data"]
    
    st.subheader(f"📊 Statistics for: {dest_data['name']}")
    
    # Create columns for stats display
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📍 Destination Information")
        st.info(f"""
        **Name**: {dest_data.get('name', 'N/A')}  
        **Country**: {dest_data.get('country', 'N/A')}  
        **City**: {dest_data.get('city', 'N/A')}  
        **Created**: {dest_data.get('created_at', 'N/A')[:10] if dest_data.get('created_at') else 'N/A'}
        """)
        
        if dest_data.get('tags'):
            st.markdown("### 🏷️ Tags")
            for tag in dest_data['tags']:
                st.badge(tag)
    
    with col2:
        st.markdown("### 📝 Description")
        if dest_data.get('description'):
            st.write(dest_data['description'])
        else:
            st.info("No description available.")
        
        st.markdown("### 📈 Usage Statistics")
        st.metric("Days Since Created", 
                 (pd.Timestamp.now() - pd.Timestamp(dest_data.get('created_at', pd.Timestamp.now()))).days if dest_data.get('created_at') else 0)
        st.metric("Number of Tags", len(dest_data.get('tags', [])))
    
    # Close button
    if st.button("❌ Close Stats", key="close_stats"):
        if "view_stats_id" in st.session_state:
            del st.session_state.view_stats_id
        st.rerun()


def show_add_destination_form():
    """Show form to add a new destination."""
    st.subheader("Add New Destination")
    
    with st.form("add_destination_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            name = st.text_input("Destination Name*", placeholder="e.g., Tokyo, Japan")
            country = st.text_input("Country*", placeholder="e.g., Japan")
            
        with col2:
            city = st.text_input("City*", placeholder="e.g., Tokyo")
            tags = st.text_input("Tags (comma-separated)", placeholder="e.g., culture, food, temples", help="Add tags to help categorize this destination")
        
        description = st.text_area("Description", placeholder="Brief description of what makes this destination special...", help="Optional: Describe what makes this destination unique or what activities are popular there")
        
        col1, col2 = st.columns(2)
        with col1:
            submit = st.form_submit_button("Add Destination", type="primary")
        with col2:
            cancel = st.form_submit_button("Cancel")
        
        if cancel:
            st.session_state.show_add_form = False
            st.rerun()
        
        if submit:
            if name and country and city:
                with st.spinner("💾 Adding destination..."):
                    destination_data = {
                        "name": name,
                        "country": country,
                        "city": city,
                        "tags": [tag.strip() for tag in tags.split(",") if tag.strip()],
                        "description": description or None
                    }
                    
                    response = api_client.create_destination(destination_data)
                
                if check_api_response(response):
                    st.success("✅ Destination added successfully!")
                    st.session_state.show_add_form = False
                    st.rerun()
                else:
                    st.error("❌ Failed to add destination. Please try again.")
            else:
                st.error("❌ Please fill in all required fields (Name, Country, and City).")


def show_destinations_table():
    """Show the destinations table."""
    response = api_client.get_destinations()
    
    if not check_api_response(response):
        return
    
    destinations = response["data"]
    
    if not destinations:
        st.info("No destinations found. Add some destinations to get started!")
        return
    
    # Convert to DataFrame for better display
    df_data = []
    for dest in destinations:
        df_data.append({
            "ID": dest["id"],
            "Name": dest["name"],
            "Country": dest["country"],
            "City": dest.get("city", ""),
            "Tags": ", ".join(dest.get("tags", [])),
            "Description": dest.get("description", "")[:60] + "..." if dest.get("description") and len(dest.get("description", "")) > 60 else dest.get("description", ""),
            "Created": dest["created_at"][:10] if dest.get("created_at") else "Unknown"
        })
    
    df = pd.DataFrame(df_data)
    
    # Display table
    st.subheader("Your Destinations")
    
    # Search and filter
    col1, col2 = st.columns([3, 1])
    with col1:
        search = st.text_input("🔍 Search destinations", placeholder="Search by name, country, or tags...")
    with col2:
        show_all = st.checkbox("Show all", value=True)
    
    # Filter DataFrame
    if search:
        mask = df.apply(lambda row: search.lower() in row.astype(str).str.lower().str.cat(sep=' '), axis=1)
        df = df[mask]
    
    # Display filtered results
    if len(df) > 0:
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "ID": st.column_config.NumberColumn("ID", width="small"),
                "Name": st.column_config.TextColumn("Name", width="medium"),
                "Country": st.column_config.TextColumn("Country", width="medium"),
                "City": st.column_config.TextColumn("City", width="medium"),
                "Tags": st.column_config.TextColumn("Tags", width="large"),
                "Description": st.column_config.TextColumn("Description", width="large"),
                "Created": st.column_config.TextColumn("Created", width="small")
            }
        )
        
        # Action buttons for selected destination
        if is_admin():
            st.subheader("Actions")
            selected_id = st.selectbox("Select destination for actions:", 
                                     options=[None] + df["ID"].tolist(),
                                     format_func=lambda x: "Select..." if x is None else f"{df[df['ID']==x]['Name'].iloc[0]} ({x})")
            
            if selected_id:
                # Get the selected destination data
                selected_dest = next((dest for dest in destinations if dest["id"] == selected_id), None)
                
                if selected_dest:
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        if st.button("✏️ Edit", key=f"edit_{selected_id}"):
                            st.session_state.edit_destination_id = selected_id
                            st.session_state.edit_destination_data = selected_dest
                            st.rerun()
                    
                    with col2:
                        if st.button("🗑️ Delete", type="secondary", key=f"delete_{selected_id}"):
                            st.session_state.delete_destination_id = selected_id
                            st.rerun()
                    
                    with col3:
                        if st.button("📊 View Stats", key=f"stats_{selected_id}"):
                            st.session_state.view_stats_id = selected_id
                            st.rerun()
                
                # Handle delete confirmation
                if st.session_state.get("delete_destination_id") == selected_id:
                    st.warning(f"⚠️ Are you sure you want to delete '{selected_dest['name']}'?")
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("✅ Yes, Delete", type="secondary"):
                            response = api_client.delete_destination(selected_id)
                            if check_api_response(response):
                                st.success("✅ Destination deleted successfully!")
                                # Clear the delete state
                                if "delete_destination_id" in st.session_state:
                                    del st.session_state.delete_destination_id
                                st.rerun()
                            else:
                                st.error("❌ Failed to delete destination.")
                    with col2:
                        if st.button("❌ Cancel"):
                            if "delete_destination_id" in st.session_state:
                                del st.session_state.delete_destination_id
                            st.rerun()
    else:
        st.info("No destinations match your search criteria.")


# Main content - handle different views
if st.session_state.get("edit_destination_id"):
    show_edit_destination_form()
elif st.session_state.get("view_stats_id"):
    show_destination_stats()
elif st.session_state.get("show_add_form", False) and is_admin():
    show_add_destination_form()
else:
    show_destinations_table()

# Footer
st.markdown("---")
st.markdown("💡 **Tip**: Destinations are used as starting points for travel planning. Add your favorite places to get personalized recommendations!")

