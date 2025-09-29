#!/usr/bin/env python3
"""
Production-ready run script for the Travel Advisory Agent backend.
"""

import uvicorn
import os
from app.core.config import settings

if __name__ == "__main__":
    # Configuration
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    
    # Run the application
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=settings.environment == "development",
        log_level="info",
        access_log=True,
        use_colors=True
    )

