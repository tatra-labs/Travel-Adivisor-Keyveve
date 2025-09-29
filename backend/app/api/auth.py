from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models import User, Organization
from app.auth.password import password_manager
from app.auth.jwt_manager import jwt_manager
from app.auth.rate_limiter import rate_limiter
from app.auth.middleware import get_current_user, require_role, CurrentUser
from datetime import datetime

router = APIRouter(prefix="/auth", tags=["authentication"])


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    user: dict


class RefreshRequest(BaseModel):
    refresh_token: str


class RefreshResponse(BaseModel):
    access_token: str
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class CreateUserRequest(BaseModel):
    email: EmailStr
    password: str
    role: str = "MEMBER"


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate user and return tokens."""
    
    # Check rate limiting
    can_attempt, lockout_until = rate_limiter.check_login_attempts(request.email)
    if not can_attempt:
        raise HTTPException(
            status_code=429,
            detail=f"Too many login attempts. Try again after {lockout_until}",
            headers={"Retry-After": "300"}
        )
    
    # Find user
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        rate_limiter.record_login_attempt(request.email, False)
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Verify password
    if not password_manager.verify_password(request.password, user.hashed_password):
        rate_limiter.record_login_attempt(request.email, False)
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Check if password needs rehashing
    if password_manager.needs_rehash(user.hashed_password):
        user.hashed_password = password_manager.hash_password(request.password)
        db.commit()
    
    # Record successful login
    rate_limiter.record_login_attempt(request.email, True)
    
    # Update last login
    user.last_login_at = datetime.now()
    db.commit()
    
    # Create tokens
    access_token = jwt_manager.create_access_token(user.id, user.org_id, user.role)
    refresh_token, _ = jwt_manager.create_refresh_token(user.id)
    
    # Get organization info
    organization = db.query(Organization).filter(Organization.id == user.org_id).first()
    
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user={
            "id": user.id,
            "email": user.email,
            "role": user.role,
            "organization": {
                "id": organization.id,
                "name": organization.name
            } if organization else None
        }
    )


@router.post("/refresh", response_model=RefreshResponse)
async def refresh_token(request: RefreshRequest):
    """Refresh access token using refresh token."""
    
    result = jwt_manager.rotate_refresh_token(request.refresh_token)
    if not result:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    
    access_token, refresh_token, _ = result
    
    return RefreshResponse(
        access_token=access_token,
        refresh_token=refresh_token
    )


@router.post("/logout")
async def logout(request: LogoutRequest):
    """Logout and revoke refresh token."""
    
    # Verify and revoke the refresh token
    payload = jwt_manager.verify_refresh_token(request.refresh_token)
    if payload:
        jti = payload.get("jti")
        if jti:
            jwt_manager.revoke_refresh_token(jti)
    
    return {"message": "Logged out successfully"}


@router.get("/me")
async def get_current_user_info(current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get current user information."""
    
    # Get user from database
    user = db.query(User).filter(User.id == current_user.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get organization info
    organization = db.query(Organization).filter(Organization.id == current_user.org_id).first()
    
    return {
        "id": user.id,
        "email": user.email,
        "role": user.role,
        "created_at": user.created_at,
        "last_login_at": user.last_login_at,
        "organization": {
            "id": organization.id,
            "name": organization.name
        } if organization else None
    }


@router.post("/users")
async def create_user(
    request: CreateUserRequest, 
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new user (admin only)."""
    
    # Check if user is admin
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")
    
    # Validate role
    if request.role not in ["ADMIN", "MEMBER"]:
        raise HTTPException(status_code=400, detail="Invalid role")
    
    # Hash password
    password_hash = password_manager.hash_password(request.password)
    
    # Create user
    user = User(
        email=request.email,
        hashed_password=password_hash,
        role=request.role,
        org_id=current_user.org_id
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return {
        "id": user.id,
        "email": user.email,
        "role": user.role,
        "created_at": user.created_at
    }


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int, 
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a user (admin only)."""
    
    # Check if user is admin
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Can't delete yourself
    if user_id == current_user.user_id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    
    # Find user in same organization
    user = db.query(User).filter(
        User.id == user_id,
        User.org_id == current_user.org_id
    ).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Revoke all tokens for the user
    jwt_manager.revoke_all_user_tokens(user_id)
    
    # Delete user
    db.delete(user)
    db.commit()
    
    return {"message": "User deleted successfully"}

