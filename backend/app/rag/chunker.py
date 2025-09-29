from typing import List, Dict, Any, Optional
import re
from pathlib import Path
import hashlib
from pydantic import BaseModel
import openai
from app.core.config import settings
from app.core.database import SessionLocal
from app.models import KnowledgeItem, Embedding
from sqlalchemy.orm import Session


class Chunk(BaseModel):
    """Represents a text chunk with metadata."""
    content: str
    start_char: int
    end_char: int
    chunk_index: int
    metadata: Dict[str, Any] = {}


class DocumentChunker:
    """Handles chunking of documents into manageable pieces for RAG."""
    
    def __init__(self, chunk_size: int = 1000, overlap: int = 200):
        self.chunk_size = chunk_size
        self.overlap = overlap
        
        # Initialize OpenAI client for embeddings
        if settings.openai_api_key:
            self.openai_client = openai.OpenAI(
                api_key=settings.openai_api_key,
                base_url=settings.openai_api_base
            )
        else:
            self.openai_client = None
    
    def chunk_text(self, text: str, metadata: Dict[str, Any] = None) -> List[Chunk]:
        """Chunk text into overlapping segments."""
        if not text.strip():
            return []
        
        chunks = []
        start = 0
        chunk_index = 0
        
        while start < len(text):
            # Calculate end position
            end = min(start + self.chunk_size, len(text))
            
            # Try to break at sentence boundaries if possible
            if end < len(text):
                # Look for sentence endings within the last 100 characters
                sentence_end = self._find_sentence_boundary(text, end - 100, end)
                if sentence_end > start:
                    end = sentence_end
            
            chunk_content = text[start:end].strip()
            
            if chunk_content:
                chunk = Chunk(
                    content=chunk_content,
                    start_char=start,
                    end_char=end,
                    chunk_index=chunk_index,
                    metadata=metadata or {}
                )
                chunks.append(chunk)
                chunk_index += 1
            
            # Move start position with overlap
            start = max(start + 1, end - self.overlap)
            
            # Prevent infinite loop
            if start >= len(text):
                break
        
        return chunks
    
    def _find_sentence_boundary(self, text: str, start: int, end: int) -> int:
        """Find the best sentence boundary within a range."""
        # Look for sentence endings (., !, ?)
        sentence_pattern = r'[.!?]\s+'
        
        # Search backwards from end to start
        for match in re.finditer(sentence_pattern, text[start:end]):
            return start + match.end()
        
        # If no sentence boundary found, look for paragraph breaks
        paragraph_pattern = r'\n\s*\n'
        for match in re.finditer(paragraph_pattern, text[start:end]):
            return start + match.end()
        
        # If no good boundary found, return the original end
        return end
    
    async def get_embedding(self, text: str) -> Optional[List[float]]:
        """Get embedding for text using OpenAI."""
        if not self.openai_client:
            return None
        
        try:
            response = self.openai_client.embeddings.create(
                model="text-embedding-ada-002",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"Error getting embedding: {e}")
            return None
    
    async def process_and_store_document(self, knowledge_item_id: int, text: str, 
                                       org_id: int, user_id: int) -> List[int]:
        """Process a document, chunk it, generate embeddings, and store in database."""
        db = SessionLocal()
        try:
            # Get the knowledge item
            knowledge_item = db.query(KnowledgeItem).filter(
                KnowledgeItem.id == knowledge_item_id
            ).first()
            
            if not knowledge_item:
                raise ValueError(f"Knowledge item {knowledge_item_id} not found")
            
            # Chunk the text
            chunks = self.chunk_text(text, {
                "knowledge_item_id": knowledge_item_id,
                "title": knowledge_item.title,
                "source_type": knowledge_item.source_type
            })
            
            embedding_ids = []
            
            for chunk in chunks:
                # Generate embedding
                embedding_vector = await self.get_embedding(chunk.content)
                
                if embedding_vector is None:
                    print(f"Failed to generate embedding for chunk {chunk.chunk_index}")
                    continue
                
                # Create embedding record
                embedding = Embedding(
                    knowledge_item_id=knowledge_item_id,
                    content=chunk.content,
                    embedding=embedding_vector,
                    chunk_idx=chunk.chunk_index
                )
                
                db.add(embedding)
                db.flush()  # Get the ID
                embedding_ids.append(embedding.id)
            
            db.commit()
            return embedding_ids
            
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()
    
    def extract_text_from_file(self, file_path: Path) -> str:
        """Extract text from various file formats."""
        file_extension = file_path.suffix.lower()
        
        if file_extension == '.txt':
            return self._extract_from_txt(file_path)
        elif file_extension == '.md':
            return self._extract_from_markdown(file_path)
        elif file_extension == '.pdf':
            return self._extract_from_pdf(file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_extension}")
    
    def _extract_from_txt(self, file_path: Path) -> str:
        """Extract text from plain text file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def _extract_from_markdown(self, file_path: Path) -> str:
        """Extract text from Markdown file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Remove Markdown formatting for better chunking
        # This is a simple approach; for production, consider using a proper Markdown parser
        content = re.sub(r'#{1,6}\s+', '', content)  # Remove headers
        content = re.sub(r'\*\*(.*?)\*\*', r'\1', content)  # Remove bold
        content = re.sub(r'\*(.*?)\*', r'\1', content)  # Remove italic
        content = re.sub(r'`(.*?)`', r'\1', content)  # Remove inline code
        content = re.sub(r'```.*?```', '', content, flags=re.DOTALL)  # Remove code blocks
        content = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', content)  # Remove links
        
        return content
    
    def _extract_from_pdf(self, file_path: Path) -> str:
        """Extract text from PDF file."""
        try:
            import PyPDF2
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
                return text
        except ImportError:
            raise ValueError("PyPDF2 not installed. Cannot process PDF files.")
        except Exception as e:
            raise ValueError(f"Error processing PDF: {str(e)}")


# Global chunker instance
document_chunker = DocumentChunker()

