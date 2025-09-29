from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import text
import openai
from app.core.database import SessionLocal
from app.models import KnowledgeItem, Embedding
from app.core.config import settings
from .base import BaseTool, ToolInput, ToolOutput


class RAGInput(ToolInput):
    """Input schema for RAG retrieval."""
    query: str = Field(..., description="Search query")
    org_id: int = Field(..., description="Organization ID for filtering")
    user_id: Optional[int] = Field(None, description="User ID for private content access")
    max_results: int = Field(5, ge=1, le=20, description="Maximum number of results")
    similarity_threshold: float = Field(0.7, ge=0.0, le=1.0, description="Minimum similarity score")


class RAGResult(BaseModel):
    """RAG search result."""
    knowledge_item_id: int
    title: str
    content_snippet: str
    similarity_score: float
    source_type: str
    scope: str


class RAGOutput(ToolOutput):
    """Output schema for RAG retrieval."""
    results: List[RAGResult] = []
    query_embedding: Optional[List[float]] = None


class RAGTool(BaseTool):
    """Tool for retrieving relevant knowledge using RAG (Retrieval-Augmented Generation)."""
    
    def __init__(self):
        super().__init__(
            name="rag",
            description="Retrieve relevant knowledge from the knowledge base using semantic search",
            timeout_seconds=15
        )
        
        # Initialize OpenAI client
        if settings.openai_api_key:
            self.openai_client = openai.OpenAI(
                api_key=settings.openai_api_key,
                base_url=settings.openai_api_base
            )
        else:
            self.openai_client = None
    
    async def _get_query_embedding(self, query: str) -> Optional[List[float]]:
        """Get embedding for the query using OpenAI."""
        if not self.openai_client:
            return None
        
        try:
            response = self.openai_client.embeddings.create(
                model="text-embedding-ada-002",
                input=query
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"Error getting embedding: {e}")
            return None
    
    def _search_with_embedding(self, db: Session, query_embedding: List[float], 
                              org_id: int, user_id: Optional[int], 
                              max_results: int, similarity_threshold: float) -> List[RAGResult]:
        """Search knowledge base using vector similarity."""
        try:
            # Build the query with proper access control
            base_query = """
                SELECT 
                    ki.id,
                    ki.title,
                    e.content,
                    1 - (e.embedding <=> :query_embedding) as similarity_score,
                    ki.source_type,
                    ki.scope
                FROM embedding e
                JOIN knowledge_item ki ON e.knowledge_item_id = ki.id
                WHERE ki.org_id = :org_id
                AND (
                    ki.scope = 'org_public' 
                    OR (ki.scope = 'private' AND ki.created_by = :user_id)
                )
                AND 1 - (e.embedding <=> :query_embedding) >= :similarity_threshold
                ORDER BY similarity_score DESC
                LIMIT :max_results
            """
            
            result = db.execute(
                text(base_query),
                {
                    "query_embedding": query_embedding,
                    "org_id": org_id,
                    "user_id": user_id,
                    "similarity_threshold": similarity_threshold,
                    "max_results": max_results
                }
            )
            
            results = []
            for row in result:
                rag_result = RAGResult(
                    knowledge_item_id=row.id,
                    title=row.title,
                    content_snippet=row.content[:500] + "..." if len(row.content) > 500 else row.content,
                    similarity_score=float(row.similarity_score),
                    source_type=row.source_type,
                    scope=row.scope
                )
                results.append(rag_result)
            
            return results
            
        except Exception as e:
            print(f"Error in vector search: {e}")
            return []
    
    def _search_with_keywords(self, db: Session, query: str, org_id: int, 
                             user_id: Optional[int], max_results: int) -> List[RAGResult]:
        """Fallback keyword search when embeddings are not available."""
        try:
            # Simple text search using PostgreSQL full-text search
            search_query = """
                SELECT DISTINCT
                    ki.id,
                    ki.title,
                    ki.content,
                    ts_rank(to_tsvector('english', ki.content), plainto_tsquery('english', :query)) as rank,
                    ki.source_type,
                    ki.scope
                FROM knowledge_item ki
                WHERE ki.org_id = :org_id
                AND (
                    ki.scope = 'org_public' 
                    OR (ki.scope = 'private' AND ki.created_by = :user_id)
                )
                AND (
                    to_tsvector('english', ki.content) @@ plainto_tsquery('english', :query)
                    OR ki.title ILIKE :like_query
                    OR ki.content ILIKE :like_query
                )
                ORDER BY rank DESC, ki.created_at DESC
                LIMIT :max_results
            """
            
            like_query = f"%{query}%"
            result = db.execute(
                text(search_query),
                {
                    "query": query,
                    "like_query": like_query,
                    "org_id": org_id,
                    "user_id": user_id,
                    "max_results": max_results
                }
            )
            
            results = []
            for row in result:
                # Extract relevant snippet around the query terms
                content = row.content
                query_words = query.lower().split()
                
                # Find the best snippet
                snippet = content[:500] + "..." if len(content) > 500 else content
                for word in query_words:
                    if word in content.lower():
                        start_idx = max(0, content.lower().find(word) - 100)
                        end_idx = min(len(content), start_idx + 500)
                        snippet = "..." + content[start_idx:end_idx] + "..."
                        break
                
                rag_result = RAGResult(
                    knowledge_item_id=row.id,
                    title=row.title,
                    content_snippet=snippet,
                    similarity_score=float(row.rank) if row.rank else 0.5,
                    source_type=row.source_type,
                    scope=row.scope
                )
                results.append(rag_result)
            
            return results
            
        except Exception as e:
            print(f"Error in keyword search: {e}")
            return []
    
    async def _execute(self, input_data: RAGInput) -> RAGOutput:
        """Execute RAG retrieval."""
        db = SessionLocal()
        
        try:
            # Get query embedding
            query_embedding = await self._get_query_embedding(input_data.query)
            
            results = []
            
            if query_embedding:
                # Use vector similarity search
                results = self._search_with_embedding(
                    db, query_embedding, input_data.org_id, input_data.user_id,
                    input_data.max_results, input_data.similarity_threshold
                )
            
            # Fallback to keyword search if no vector results or no embeddings
            if not results:
                results = self._search_with_keywords(
                    db, input_data.query, input_data.org_id, input_data.user_id,
                    input_data.max_results
                )
            
            return RAGOutput(
                success=True,
                data={
                    "results": [r.model_dump() for r in results],
                    "query": input_data.query,
                    "total_results": len(results)
                },
                results=results,
                query_embedding=query_embedding
            )
            
        except Exception as e:
            return RAGOutput(
                success=False,
                error=f"RAG search failed: {str(e)}"
            )
        finally:
            db.close()
    
    def get_input_schema(self) -> type[ToolInput]:
        return RAGInput
    
    def get_output_schema(self) -> type[ToolOutput]:
        return RAGOutput

