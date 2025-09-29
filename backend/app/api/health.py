from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from app.core.database import SessionLocal
from app.tools.weather import WeatherTool
from app.models import Embedding
import asyncio
from datetime import datetime
from typing import Dict, Any

router = APIRouter()


async def check_database() -> Dict[str, Any]:
    """Check database connectivity and basic operations."""
    try:
        db = SessionLocal()
        try:
            # Test basic connectivity
            result = db.execute(text("SELECT 1"))
            result.fetchone()
            
            # Test embeddings table
            embedding_count = db.query(Embedding).count()
            
            return {
                "status": "healthy",
                "embedding_count": embedding_count,
                "timestamp": datetime.now().isoformat()
            }
        finally:
            db.close()
    except SQLAlchemyError as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


async def check_embeddings_service() -> Dict[str, Any]:
    """Check if embeddings service (OpenAI) is accessible."""
    try:
        from app.rag.chunker import document_chunker
        
        # Test with a simple query
        embedding = await document_chunker.get_embedding("test query")
        
        if embedding:
            return {
                "status": "healthy",
                "embedding_dimensions": len(embedding),
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "status": "degraded",
                "error": "No embedding returned",
                "timestamp": datetime.now().isoformat()
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


async def check_outbound_tool() -> Dict[str, Any]:
    """Check if outbound tools are working (test weather tool)."""
    try:
        weather_tool = WeatherTool()
        
        # Test with a simple weather request
        result = await weather_tool.execute({
            "latitude": 35.6762,
            "longitude": 139.6503,
            "start_date": "2025-01-01",
            "end_date": "2025-01-02"
        })
        
        if result.success:
            return {
                "status": "healthy",
                "tool": "weather",
                "cached": result.cached,
                "duration_ms": result.duration_ms,
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "status": "unhealthy",
                "tool": "weather",
                "error": result.error,
                "timestamp": datetime.now().isoformat()
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "tool": "weather",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@router.get("/healthz")
async def health_check():
    """
    Comprehensive health check endpoint.
    Returns 200 if all systems are healthy, 503 if any critical system is down.
    """
    # Run all health checks concurrently
    db_check, embeddings_check, tool_check = await asyncio.gather(
        check_database(),
        check_embeddings_service(),
        check_outbound_tool(),
        return_exceptions=True
    )
    
    # Handle exceptions
    if isinstance(db_check, Exception):
        db_check = {"status": "unhealthy", "error": str(db_check)}
    if isinstance(embeddings_check, Exception):
        embeddings_check = {"status": "unhealthy", "error": str(embeddings_check)}
    if isinstance(tool_check, Exception):
        tool_check = {"status": "unhealthy", "error": str(tool_check)}
    
    # Determine overall health
    all_healthy = all(
        check.get("status") == "healthy" 
        for check in [db_check, embeddings_check, tool_check]
    )
    
    # Allow degraded embeddings service (not critical for basic functionality)
    critical_healthy = (
        db_check.get("status") == "healthy" and
        tool_check.get("status") == "healthy"
    )
    
    overall_status = "healthy" if all_healthy else ("degraded" if critical_healthy else "unhealthy")
    
    response = {
        "status": overall_status,
        "timestamp": datetime.now().isoformat(),
        "checks": {
            "database": db_check,
            "embeddings": embeddings_check,
            "outbound_tools": tool_check
        },
        "version": "1.0.0"
    }
    
    # Return appropriate HTTP status
    if overall_status == "unhealthy":
        raise HTTPException(status_code=503, detail=response)
    
    return response


@router.get("/health")
async def simple_health_check():
    """Simple health check for load balancers."""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

