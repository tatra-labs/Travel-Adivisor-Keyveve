#!/usr/bin/env python3
"""
Production-ready run script for the Travel Advisory Agent frontend.
"""

import streamlit.web.cli as stcli
import sys
import os

if __name__ == "__main__":
    # Configuration
    host = os.getenv("STREAMLIT_HOST", "0.0.0.0")
    port = os.getenv("STREAMLIT_PORT", "8501")
    
    # Set Streamlit configuration
    sys.argv = [
        "streamlit",
        "run",
        "app.py",
        "--server.address", host,
        "--server.port", port,
        "--server.headless", "true",
        "--browser.gatherUsageStats", "false"
    ]
    
    # Run Streamlit
    stcli.main()

