from sqlalchemy import Column, String, Boolean
from sqlalchemy.orm import relationship
from .base import BaseModel


class Organization(BaseModel):
    __tablename__ = "org"
    
    name = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    users = relationship("User", back_populates="organization")
    destinations = relationship("Destination", back_populates="organization")
    knowledge_items = relationship("KnowledgeItem", back_populates="organization")
    agent_runs = relationship("AgentRun", back_populates="organization")

