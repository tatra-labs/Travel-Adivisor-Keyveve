from sqlalchemy import Column, String, Boolean, BigInteger, ForeignKey, Integer, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import BaseModel


class User(BaseModel):
    __tablename__ = "user"
    
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), default="MEMBER")  # ADMIN or MEMBER
    is_active = Column(Boolean, default=True)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    
    # Foreign keys
    org_id = Column(BigInteger, ForeignKey("org.id"), nullable=False)
    
    # Relationships
    organization = relationship("Organization", back_populates="users")
    refresh_tokens = relationship("RefreshToken", back_populates="user")
    knowledge_items = relationship("KnowledgeItem", back_populates="created_by_user")
    agent_runs = relationship("AgentRun", back_populates="user")


class RefreshToken(BaseModel):
    __tablename__ = "refresh_token"
    
    jti = Column(String(255), unique=True, index=True, nullable=False)
    hashed_token = Column(String(255), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_revoked = Column(Boolean, default=False)
    
    # Foreign keys
    user_id = Column(BigInteger, ForeignKey("user.id"), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="refresh_tokens")

