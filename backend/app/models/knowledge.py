from sqlalchemy import Column, String, Boolean, BigInteger, ForeignKey, Text, Integer
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from .base import BaseModel


class KnowledgeItem(BaseModel):
    __tablename__ = "knowledge_item"
    
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    source_type = Column(String(50), nullable=False)  # "pdf", "markdown", "manual"
    source_path = Column(String(500))
    scope = Column(String(50), default="private")  # "org_public" or "private"
    version = Column(Integer, default=1)
    
    # Foreign keys
    org_id = Column(BigInteger, ForeignKey("org.id"), nullable=False)
    created_by = Column(BigInteger, ForeignKey("user.id"), nullable=False)
    
    # Relationships
    organization = relationship("Organization", back_populates="knowledge_items")
    created_by_user = relationship("User", back_populates="knowledge_items")
    embeddings = relationship("Embedding", back_populates="knowledge_item", cascade="all, delete-orphan")


class Embedding(BaseModel):
    __tablename__ = "embedding"
    
    chunk_idx = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(1536), nullable=False)  # OpenAI embedding dimension
    
    # Foreign keys
    knowledge_item_id = Column(BigInteger, ForeignKey("knowledge_item.id", ondelete="CASCADE"), nullable=False)
    
    # Relationships
    knowledge_item = relationship("KnowledgeItem", back_populates="embeddings")

