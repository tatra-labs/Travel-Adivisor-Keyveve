from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import time
import uuid
import logging
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import engine
from app.core.database import Base
from app.api import health, metrics, auth, destinations, knowledge, agent
from app.auth.jwt_manager import jwt_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Starting Travel Advisory Agent API")
    
    # Create database tables
    Base.metadata.create_all(bind=engine)
    
    # Cleanup expired tokens on startup
    jwt_manager.cleanup_expired_tokens()
    
    yield
    
    # Shutdown
    logger.info("Shutting down Travel Advisory Agent API")


# Create FastAPI app
app = FastAPI(
    title="Travel Advisory Agent API",
    description="AI-powered travel planning with agentic system",
    version="1.0.0",
    lifespan=lifespan
)

# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses."""
    response = await call_next(request)
    
    # Security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    
    return response


# Request ID middleware
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add unique request ID for tracing."""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    
    return response


# Logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests with timing."""
    start_time = time.time()
    
    # Log request
    logger.info(
        f"Request started",
        extra={
            "request_id": getattr(request.state, "request_id", "unknown"),
            "method": request.method,
            "url": str(request.url),
            "client_ip": request.client.host if request.client else "unknown"
        }
    )
    
    response = await call_next(request)
    
    # Log response
    duration_ms = (time.time() - start_time) * 1000
    logger.info(
        f"Request completed",
        extra={
            "request_id": getattr(request.state, "request_id", "unknown"),
            "status_code": response.status_code,
            "duration_ms": round(duration_ms, 2)
        }
    )
    
    return response


# CORS middleware - allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Trusted host middleware (optional, for production)
if settings.environment == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"]  # Configure with actual hosts in production
    )


# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with consistent format."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "request_id": getattr(request.state, "request_id", "unknown")
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    logger.error(
        f"Unhandled exception: {str(exc)}",
        extra={
            "request_id": getattr(request.state, "request_id", "unknown"),
            "exception_type": type(exc).__name__
        },
        exc_info=True
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "status_code": 500,
            "request_id": getattr(request.state, "request_id", "unknown")
        }
    )


# Include routers
app.include_router(health.router, tags=["health"])
app.include_router(metrics.router, tags=["metrics"])
app.include_router(auth.router, tags=["auth"])
app.include_router(destinations.router, tags=["destinations"])
app.include_router(knowledge.router, tags=["knowledge"])

# TODO: Add other routers
app.include_router(agent.router, tags=["agent"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Travel Advisory Agent API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/healthz"
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True if settings.environment == "development" else False,
        log_level="info"
    )

