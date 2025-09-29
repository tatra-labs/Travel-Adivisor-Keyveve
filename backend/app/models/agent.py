from sqlalchemy import Column, String, BigInteger, ForeignKey, Text, DateTime, Numeric, JSON
from sqlalchemy.orm import relationship
from .base import BaseModel


class AgentRun(BaseModel):
    __tablename__ = "agent_run"
    
    trace_id = Column(String(255), unique=True, index=True, nullable=False)
    status = Column(String(50), nullable=False)  # "running", "completed", "failed"
    started_at = Column(DateTime(timezone=True), nullable=False)
    finished_at = Column(DateTime(timezone=True))
    plan_snapshot = Column(JSON)
    tool_log = Column(JSON)
    cost_usd = Column(Numeric(8, 2))
    error_message = Column(Text)
    
    # Foreign keys
    org_id = Column(BigInteger, ForeignKey("org.id"), nullable=False)
    user_id = Column(BigInteger, ForeignKey("user.id", ondelete="SET NULL"))
    
    # Relationships
    organization = relationship("Organization", back_populates="agent_runs")
    user = relationship("User", back_populates="agent_runs")

