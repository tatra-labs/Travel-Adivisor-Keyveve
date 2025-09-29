from sqlalchemy import Column, String, Boolean, BigInteger, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from .base import BaseModel


class Destination(BaseModel):
    __tablename__ = "destination"
    
    name = Column(String(255), nullable=False)
    country = Column(String(100), nullable=False)
    city = Column(String(100), nullable=False)
    description = Column(Text)
    tags = Column(JSON)  # List of tags like ["family-friendly", "museums", "outdoor"]
    latitude = Column(String(50))
    longitude = Column(String(50))
    is_deleted = Column(Boolean, default=False)  # Soft delete
    
    # Foreign keys
    org_id = Column(BigInteger, ForeignKey("org.id"), nullable=False)
    
    # Relationships
    organization = relationship("Organization", back_populates="destinations")

