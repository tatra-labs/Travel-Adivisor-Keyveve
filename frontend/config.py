import os
from dotenv import load_dotenv

load_dotenv()

# Backend API configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# Streamlit configuration
PAGE_TITLE = "Travel Advisory Agent"
PAGE_ICON = "✈️"
LAYOUT = "wide"

# UI Configuration
SIDEBAR_WIDTH = 300
MAIN_CONTENT_WIDTH = 800

# Colors and styling
PRIMARY_COLOR = "#1f77b4"
SECONDARY_COLOR = "#ff7f0e"
SUCCESS_COLOR = "#2ca02c"
ERROR_COLOR = "#d62728"
WARNING_COLOR = "#ff7f0e"

# Agent configuration
STREAMING_ENABLED = True
PROGRESS_UPDATE_INTERVAL = 0.5  # seconds

