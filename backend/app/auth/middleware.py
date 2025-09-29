from typing import Optional, Dict, Any
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.auth.jwt_manager import jwt_manager
from app.auth.rate_limiter import rate_limiter
from app.models import User
from app.core.database import SessionLocal

# Security scheme for FastAPI
security = HTTPBearer()


class CurrentUser:
    """Context class to hold current user information."""
    def __init__(self, user_id: int, org_id: int, role: str):
        self.user_id = user_id
        self.org_id = org_id
        self.role = role


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> CurrentUser:
    """Dependency to get the current authenticated user."""
    token = credentials.credentials
    
    # Verify token
    payload = jwt_manager.verify_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return CurrentUser(
        user_id=int(payload["sub"]),
        org_id=payload["org_id"],
        role=payload["role"]
    )


def require_role(required_role: str):
    """Factory function to create a role requirement dependency."""
    async def role_dependency(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if current_user.role != required_role:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user
    return role_dependency


async def check_api_rate_limit(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """Dependency to check API rate limiting."""
    if not rate_limiter.check_api_rate_limit(current_user.user_id):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    return current_user


async def check_agent_rate_limit(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """Dependency to check agent request rate limiting."""
    if not rate_limiter.check_agent_rate_limit(current_user.user_id):
        raise HTTPException(status_code=429, detail="Agent rate limit exceeded")
    return current_user


def get_user_from_db(user_id: int) -> Optional[User]:
    """Get user from database by ID."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        return user
    finally:
        db.close()


def filter_by_org(query, model_class, org_id: int):
    """Filter a query by organization ID."""
    return query.filter(model_class.org_id == org_id)


def ensure_org_access(org_id: int, current_user: CurrentUser) -> bool:
    """Ensure the current user has access to the specified organization."""
    return current_user.org_id == org_id

