from sqlalchemy import Column, Integer, DateTime, BigInteger
from sqlalchemy.sql import func
from app.core.database import Base


class BaseModel(Base):
    __abstract__ = True
    
    id = Column(BigInteger, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

