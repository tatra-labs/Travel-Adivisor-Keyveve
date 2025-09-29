import streamlit as st
import pandas as pd
from utils.auth import init_session_state, require_auth, check_api_response, is_admin
from utils.api_client import api_client

# Page configuration
st.set_page_config(
    page_title="Knowledge Base - Travel Advisory Agent",
    page_icon="📚",
    layout="wide"
)

# Initialize session state
init_session_state()

# Require authentication
require_auth()

st.title("📚 Knowledge Base")
st.markdown("Manage travel knowledge documents and view processing history.")

# Initialize show_upload_form if not exists
if "show_upload_form" not in st.session_state:
    st.session_state.show_upload_form = False

# Sidebar for actions
with st.sidebar:
    st.header("Actions")
    
    if st.button("📄 Upload Document"):
        st.session_state.show_upload_form = True
        # Reset all other states
        st.session_state.show_chunks = False
        st.session_state.show_reprocess = False
        st.session_state.show_delete = False
        st.session_state.selected_knowledge_id = None
    
    if st.button("📋 View Documents"):
        st.session_state.show_upload_form = False
        # Reset all other states
        st.session_state.show_chunks = False
        st.session_state.show_reprocess = False
        st.session_state.show_delete = False
        st.session_state.selected_knowledge_id = None
        st.rerun()
    
    if st.button("🔄 Refresh"):
        st.rerun()


def show_upload_form():
    """Show form to upload a new knowledge document."""
    st.subheader("Upload Knowledge Document")
    
    with st.form("upload_form"):
        title = st.text_input("Document Title*")
        
        uploaded_file = st.file_uploader(
            "Choose a file",
            type=["txt", "md", "pdf"],
            help="Supported formats: TXT, Markdown, PDF"
        )
        
        scope = st.selectbox(
            "Visibility",
            options=["org_public", "private"],
            format_func=lambda x: "Organization (visible to all members)" if x == "org_public" else "Private (only visible to you)"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            submit = st.form_submit_button("Upload", type="primary")
        with col2:
            cancel = st.form_submit_button("Cancel")
        
        if cancel:
            st.session_state.show_upload_form = False
            st.rerun()
        
        if submit:
            if title and uploaded_file:
                # Show loading state
                with st.spinner("📤 Uploading and processing document..."):
                    # Read file content
                    file_content = uploaded_file.read()
                    
                    response = api_client.upload_knowledge_file(
                        file_content, 
                        uploaded_file.name, 
                        title, 
                        scope
                    )
                
                if check_api_response(response):
                    st.success("✅ Document uploaded successfully!")
                    st.info("📄 The document has been processed and is now available for search!")
                    st.session_state.show_upload_form = False
                    st.rerun()
                else:
                    st.error("❌ Failed to upload document. Please try again.")
            else:
                st.error("❌ Please provide a title and select a file.")


def show_knowledge_table():
    """Show the knowledge items table."""
    response = api_client.get_knowledge_items()
    
    if not check_api_response(response):
        return
    
    knowledge_items = response["data"]
    
    if not knowledge_items:
        st.info("No knowledge documents found. Upload some documents to get started!")
        return
    
    # Convert to DataFrame for better display
    df_data = []
    for item in knowledge_items:
        df_data.append({
            "ID": item["id"],
            "Title": item["title"],
            "Type": item["source_type"],
            "Scope": "🌐 Organization" if item["scope"] == "org_public" else "🔒 Private",
            "Chunks": item.get("chunk_count", 0),
            "Created": item["created_at"][:10],  # Just the date
            "Status": "✅ Processed" if item.get("processed", False) else "⏳ Processing"
        })
    
    df = pd.DataFrame(df_data)
    
    # Display table
    st.subheader("Knowledge Documents")
    
    # Search and filter
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        search = st.text_input("🔍 Search documents", placeholder="Search by title or type...")
    with col2:
        scope_filter = st.selectbox("Filter by scope", ["All", "Organization", "Private"])
    with col3:
        type_filter = st.selectbox("Filter by type", ["All", "file", "manual", "url"])
    
    # Filter DataFrame
    filtered_df = df.copy()
    
    if search:
        mask = filtered_df.apply(lambda row: search.lower() in row.astype(str).str.lower().str.cat(sep=' '), axis=1)
        filtered_df = filtered_df[mask]
    
    if scope_filter != "All":
        scope_value = "🌐 Organization" if scope_filter == "Organization" else "🔒 Private"
        filtered_df = filtered_df[filtered_df["Scope"] == scope_value]
    
    if type_filter != "All":
        filtered_df = filtered_df[filtered_df["Type"] == type_filter]
    
    # Display filtered results
    if len(filtered_df) > 0:
        st.dataframe(
            filtered_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "ID": st.column_config.NumberColumn("ID", width="small"),
                "Title": st.column_config.TextColumn("Title", width="large"),
                "Type": st.column_config.TextColumn("Type", width="small"),
                "Scope": st.column_config.TextColumn("Scope", width="medium"),
                "Chunks": st.column_config.NumberColumn("Chunks", width="small"),
                "Created": st.column_config.TextColumn("Created", width="small"),
                "Status": st.column_config.TextColumn("Status", width="medium")
            }
        )
        
        # Show statistics
        st.subheader("📊 Statistics")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Documents", len(df))
        
        with col2:
            processed_count = len(df[df["Status"] == "✅ Processed"])
            st.metric("Processed", processed_count)
        
        with col3:
            org_count = len(df[df["Scope"] == "🌐 Organization"])
            st.metric("Organization", org_count)
        
        with col4:
            total_chunks = df["Chunks"].sum()
            st.metric("Total Chunks", total_chunks)
        
        # Action buttons for selected document
        if is_admin():
            st.subheader("Actions")
            selected_id = st.selectbox("Select document for actions:", 
                                     options=[None] + filtered_df["ID"].tolist(),
                                     format_func=lambda x: "Select..." if x is None else f"{filtered_df[filtered_df['ID']==x]['Title'].iloc[0]} ({x})")
            
            if selected_id:
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.button("👁️ View Chunks"):
                        st.session_state.show_chunks = True
                        st.session_state.selected_knowledge_id = selected_id
                        st.rerun()
                
                with col2:
                    if st.button("🔄 Reprocess"):
                        st.session_state.show_reprocess = True
                        st.session_state.selected_knowledge_id = selected_id
                        st.rerun()
                
                with col3:
                    if st.button("🗑️ Delete", type="secondary"):
                        st.session_state.show_delete = True
                        st.session_state.selected_knowledge_id = selected_id
                        st.rerun()
    else:
        st.info("No documents match your search criteria.")


def show_chunks_viewer(knowledge_id: int):
    """Show chunks for a specific knowledge item."""
    st.subheader("📄 Document Chunks")
    
    try:
        # Get knowledge item details
        knowledge_response = api_client.get_knowledge_item(knowledge_id)
        if not knowledge_response.get("success"):
            st.error(f"❌ Failed to get document details: {knowledge_response.get('error', 'Unknown error')}")
            return
        
        knowledge_item = knowledge_response["data"]
        
        # Get chunks
        chunks_response = api_client.get_knowledge_chunks(knowledge_id)
        if not chunks_response.get("success"):
            st.error(f"❌ Failed to get chunks: {chunks_response.get('error', 'Unknown error')}")
            return
        
        chunks_data = chunks_response["data"]
        chunks = chunks_data.get("chunks", [])
        
        # Display document info
        st.info(f"**Document:** {knowledge_item['title']} | **Total Chunks:** {len(chunks)}")
        
        # Display chunks
        for i, chunk in enumerate(chunks):
            with st.expander(f"Chunk {chunk['chunk_idx'] + 1}"):
                st.text(chunk['content'])
        
        # Close button
        if st.button("🔙 Back to Documents"):
            st.session_state.show_chunks = False
            st.session_state.selected_knowledge_id = None
            st.rerun()
            
    except Exception as e:
        st.error(f"❌ Error loading chunks: {str(e)}")
        # Reset session state on error to allow navigation
        if st.button("🔙 Back to Documents"):
            st.session_state.show_chunks = False
            st.session_state.selected_knowledge_id = None
            st.rerun()


def show_reprocess_dialog(knowledge_id: int):
    """Show reprocess confirmation dialog."""
    st.subheader("🔄 Reprocess Document")
    
    try:
        # Get knowledge item details
        knowledge_response = api_client.get_knowledge_item(knowledge_id)
        if not knowledge_response.get("success"):
            st.error(f"❌ Failed to get document details: {knowledge_response.get('error', 'Unknown error')}")
            return
        
        knowledge_item = knowledge_response["data"]
        
        st.warning(f"**Document:** {knowledge_item['title']}")
        st.info("This will re-chunk and re-embed the document. This may take a few moments.")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("✅ Yes, Reprocess", type="primary"):
                with st.spinner("Reprocessing document..."):
                    try:
                        response = api_client.reprocess_knowledge_item(knowledge_id)
                        if response.get("success"):
                            st.success("✅ Document reprocessed successfully!")
                            st.info(f"📊 {response['data'].get('chunk_count', 0)} chunks created")
                        else:
                            st.error(f"❌ Failed to reprocess: {response.get('error', 'Unknown error')}")
                    except Exception as e:
                        st.error(f"❌ Error during reprocessing: {str(e)}")
                
                # Reset state and return to main view
                st.session_state.show_reprocess = False
                st.session_state.selected_knowledge_id = None
                st.rerun()
        
        with col2:
            if st.button("❌ Cancel"):
                st.session_state.show_reprocess = False
                st.session_state.selected_knowledge_id = None
                st.rerun()
                
    except Exception as e:
        st.error(f"❌ Error loading document: {str(e)}")
        # Reset session state on error to allow navigation
        if st.button("🔙 Back to Documents"):
            st.session_state.show_reprocess = False
            st.session_state.selected_knowledge_id = None
            st.rerun()


def show_delete_dialog(knowledge_id: int):
    """Show delete confirmation dialog."""
    st.subheader("🗑️ Delete Document")
    
    try:
        # Get knowledge item details
        knowledge_response = api_client.get_knowledge_item(knowledge_id)
        if not knowledge_response.get("success"):
            st.error(f"❌ Failed to get document details: {knowledge_response.get('error', 'Unknown error')}")
            return
        
        knowledge_item = knowledge_response["data"]
        
        st.error(f"**Document:** {knowledge_item['title']}")
        st.warning("⚠️ This action cannot be undone. All chunks and embeddings will be permanently deleted.")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🗑️ Yes, Delete", type="primary"):
                with st.spinner("Deleting document..."):
                    try:
                        response = api_client.delete_knowledge_item(knowledge_id)
                        if response.get("success"):
                            st.success("✅ Document deleted successfully!")
                        else:
                            st.error(f"❌ Failed to delete: {response.get('error', 'Unknown error')}")
                    except Exception as e:
                        st.error(f"❌ Error during deletion: {str(e)}")
                
                # Reset state and return to main view
                st.session_state.show_delete = False
                st.session_state.selected_knowledge_id = None
                st.rerun()
        
        with col2:
            if st.button("❌ Cancel"):
                st.session_state.show_delete = False
                st.session_state.selected_knowledge_id = None
                st.rerun()
                
    except Exception as e:
        st.error(f"❌ Error loading document: {str(e)}")
        # Reset session state on error to allow navigation
        if st.button("🔙 Back to Documents"):
            st.session_state.show_delete = False
            st.session_state.selected_knowledge_id = None
            st.rerun()


# Main content
if st.session_state.get("show_chunks", False):
    show_chunks_viewer(st.session_state.selected_knowledge_id)
elif st.session_state.get("show_reprocess", False):
    show_reprocess_dialog(st.session_state.selected_knowledge_id)
elif st.session_state.get("show_delete", False):
    show_delete_dialog(st.session_state.selected_knowledge_id)
elif st.session_state.get("show_upload_form", False):
    show_upload_form()
else:
    show_knowledge_table()

# Footer
st.markdown("---")
st.markdown("💡 **Tip**: Upload travel guides, destination information, and other relevant documents to improve the agent's knowledge and recommendations!")

