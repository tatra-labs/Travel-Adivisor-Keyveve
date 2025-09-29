import requests
import streamlit as st
from typing import Dict, Any, Optional, List
import json
from config import API_BASE_URL


class APIClient:
    """Client for communicating with the backend API."""
    
    def __init__(self):
        self.base_url = API_BASE_URL
        self.session = requests.Session()
        
        # Set default headers
        self.session.headers.update({
            "Content-Type": "application/json"
        })
    
    def set_auth_token(self, token: str):
        """Set the authorization token for API requests."""
        self.session.headers.update({
            "Authorization": f"Bearer {token}"
        })
    
    def clear_auth_token(self):
        """Clear the authorization token."""
        if "Authorization" in self.session.headers:
            del self.session.headers["Authorization"]
    
    def login(self, email: str, password: str) -> Dict[str, Any]:
        """Authenticate user and get tokens."""
        response = self.session.post(
            f"{self.base_url}/auth/login",
            json={"email": email, "password": password}
        )
        return self._handle_response(response)
    
    def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh access token."""
        response = self.session.post(
            f"{self.base_url}/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        return self._handle_response(response)
    
    def logout(self, refresh_token: str) -> Dict[str, Any]:
        """Logout and revoke refresh token."""
        response = self.session.post(
            f"{self.base_url}/auth/logout",
            json={"refresh_token": refresh_token}
        )
        return self._handle_response(response)
    
    def get_user_info(self) -> Dict[str, Any]:
        """Get current user information."""
        response = self.session.get(f"{self.base_url}/auth/me")
        return self._handle_response(response)
    
    def get_destinations(self) -> Dict[str, Any]:
        """Get list of destinations."""
        response = self.session.get(f"{self.base_url}/destinations")
        return self._handle_response(response)
    
    def create_destination(self, destination_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new destination."""
        response = self.session.post(
            f"{self.base_url}/destinations",
            json=destination_data
        )
        return self._handle_response(response)
    
    def get_destination(self, destination_id: int) -> Dict[str, Any]:
        """Get a specific destination by ID."""
        response = self.session.get(f"{self.base_url}/destinations/{destination_id}")
        return self._handle_response(response)
    
    def update_destination(self, destination_id: int, destination_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a destination."""
        response = self.session.put(
            f"{self.base_url}/destinations/{destination_id}",
            json=destination_data
        )
        return self._handle_response(response)
    
    def delete_destination(self, destination_id: int) -> Dict[str, Any]:
        """Soft delete a destination."""
        response = self.session.delete(f"{self.base_url}/destinations/{destination_id}")
        return self._handle_response(response)
    
    def get_knowledge_items(self) -> Dict[str, Any]:
        """Get list of knowledge items."""
        response = self.session.get(f"{self.base_url}/knowledge")
        return self._handle_response(response)
    
    def upload_knowledge_file(self, file_data: bytes, filename: str, title: str, scope: str = "org_public") -> Dict[str, Any]:
        """Upload a knowledge file."""
        files = {"file": (filename, file_data)}
        data = {"title": title, "scope": scope}
        
        # Remove Content-Type header for file upload
        headers = dict(self.session.headers)
        if "Content-Type" in headers:
            del headers["Content-Type"]
        
        response = requests.post(
            f"{self.base_url}/knowledge/upload",
            files=files,
            data=data,
            headers=headers
        )
        return self._handle_response(response)
    
    def start_agent_run(self, message: str, constraints: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Start an agent run."""
        payload = {"message": message}
        if constraints:
            payload["constraints"] = constraints
        
        response = self.session.post(
            f"{self.base_url}/agent/run",
            json=payload
        )
        return self._handle_response(response)
    
    def get_agent_run_status(self, run_id: str) -> Dict[str, Any]:
        """Get status of an agent run."""
        response = self.session.get(f"{self.base_url}/agent/run/{run_id}")
        return self._handle_response(response)
    
    def stream_agent_run(self, run_id: str):
        """Stream agent run progress."""
        response = self.session.get(
            f"{self.base_url}/agent/run/{run_id}/stream",
            stream=True
        )
        
        if response.status_code == 200:
            for line in response.iter_lines():
                if line:
                    try:
                        data = json.loads(line.decode('utf-8'))
                        yield data
                    except json.JSONDecodeError:
                        continue
        else:
            yield {"error": f"HTTP {response.status_code}: {response.text}"}
    
    def get_health(self) -> Dict[str, Any]:
        """Get API health status."""
        response = self.session.get(f"{self.base_url}/health")
        return self._handle_response(response)
    
    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """Handle API response and return JSON data or error."""
        try:
            data = response.json()
        except json.JSONDecodeError:
            data = {"error": "Invalid JSON response"}
        
        if response.status_code >= 400:
            error_msg = data.get("error", f"HTTP {response.status_code}")
            return {"success": False, "error": error_msg, "status_code": response.status_code}
        
        return {"success": True, "data": data}
    
    def get_knowledge_item(self, knowledge_id: int) -> Dict[str, Any]:
        """Get a specific knowledge item."""
        response = self.session.get(f"{self.base_url}/knowledge/{knowledge_id}")
        return self._handle_response(response)
    
    def get_knowledge_chunks(self, knowledge_id: int) -> Dict[str, Any]:
        """Get chunks for a specific knowledge item."""
        response = self.session.get(f"{self.base_url}/knowledge/{knowledge_id}/chunks")
        return self._handle_response(response)
    
    def reprocess_knowledge_item(self, knowledge_id: int) -> Dict[str, Any]:
        """Reprocess a knowledge item (re-chunk and re-embed)."""
        response = self.session.post(f"{self.base_url}/knowledge/{knowledge_id}/reprocess")
        return self._handle_response(response)
    
    def delete_knowledge_item(self, knowledge_id: int) -> Dict[str, Any]:
        """Delete a knowledge item."""
        response = self.session.delete(f"{self.base_url}/knowledge/{knowledge_id}")
        return self._handle_response(response)
    
    def start_agent_run(self, message: str, constraints: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Start a new agent run for travel planning."""
        data = {"message": message, "constraints": constraints or {}}
        response = self.session.post(f"{self.base_url}/agent/run", json=data)
        return self._handle_response(response)
    
    def get_agent_run_status(self, run_id: str) -> Dict[str, Any]:
        """Get the status of an agent run."""
        response = self.session.get(f"{self.base_url}/agent/run/{run_id}/status")
        return self._handle_response(response)
    
    def stream_agent_run(self, run_id: str):
        """Stream updates from an agent run."""
        response = self.session.get(f"{self.base_url}/agent/run/{run_id}/stream")
        return self._handle_response(response)
    
    def get_available_destinations(self) -> Dict[str, Any]:
        """Get all available destinations for dropdown selection."""
        # Get destinations from destinations API
        destinations_response = self.get_destinations()
        destinations = []
        
        if destinations_response.get("success"):
            destinations.extend(destinations_response["data"])
        
        # Get destinations from knowledge base
        knowledge_response = self.get_knowledge_items()
        if knowledge_response.get("success"):
            knowledge_items = knowledge_response["data"]
            for item in knowledge_items:
                # Extract destination names from knowledge base titles
                if "travel guide" in item["title"].lower() or "guide" in item["title"].lower():
                    # Try to extract destination from title
                    title = item["title"]
                    if "travel guide" in title.lower():
                        dest_name = title.replace("Travel Guide", "").strip()
                    elif "guide" in title.lower():
                        dest_name = title.replace("Guide", "").strip()
                    else:
                        dest_name = title
                    
                    destinations.append({
                        "id": f"kb_{item['id']}",
                        "name": dest_name,
                        "source": "Knowledge Base",
                        "description": f"From uploaded travel guide: {item['title']}"
                    })
        
        return {"success": True, "data": destinations}


# Global API client instance
api_client = APIClient()

