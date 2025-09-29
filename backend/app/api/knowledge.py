from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File, Form
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime
import io

from app.core.database import get_db
from app.models.knowledge import KnowledgeItem, Embedding
from app.models.organization import Organization
from app.auth.middleware import get_current_user, CurrentUser
from app.rag.chunker import DocumentChunker
from app.core.database_utils import ensure_sequential_ids

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


class KnowledgeItemResponse(BaseModel):
    id: int
    title: str
    content: str
    source_type: str
    source_path: Optional[str]
    scope: str
    version: int
    chunk_count: int
    processed: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class KnowledgeItemCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, description="Document title")
    content: str = Field(..., description="Document content")
    source_type: str = Field(..., description="Source type: file, manual, url")
    scope: str = Field(default="private", description="Scope: org_public or private")


@router.get("/", response_model=List[KnowledgeItemResponse])
async def get_knowledge_items(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """Get all knowledge items for the current user's organization."""
    # Get knowledge items based on scope
    knowledge_items = db.query(KnowledgeItem).filter(
        KnowledgeItem.org_id == current_user.org_id
    ).filter(
        (KnowledgeItem.scope == "org_public") | 
        (KnowledgeItem.created_by == current_user.user_id)
    ).all()
    
    # Add chunk count and processed status
    result = []
    for item in knowledge_items:
        chunk_count = db.query(Embedding).filter(
            Embedding.knowledge_item_id == item.id
        ).count()
        
        result.append(KnowledgeItemResponse(
            id=item.id,
            title=item.title,
            content=item.content,
            source_type=item.source_type,
            source_path=item.source_path,
            scope=item.scope,
            version=item.version,
            chunk_count=chunk_count,
            processed=chunk_count > 0,
            created_at=item.created_at,
            updated_at=item.updated_at
        ))
    
    return result


@router.post("/upload", response_model=KnowledgeItemResponse, status_code=status.HTTP_201_CREATED)
async def upload_knowledge_file(
    file: UploadFile = File(...),
    title: str = Form(...),
    scope: str = Form(default="private"),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """Upload a knowledge file."""
    # Validate file type - be more flexible with MIME type detection
    allowed_types = ["text/plain", "text/markdown", "application/pdf"]
    allowed_extensions = [".txt", ".md", ".markdown", ".pdf"]
    
    # Get file extension
    file_extension = None
    if file.filename:
        file_extension = file.filename.lower().split('.')[-1]
        if file_extension:
            file_extension = f".{file_extension}"
    
    # Check both MIME type and file extension
    content_type_valid = file.content_type in allowed_types if file.content_type else False
    extension_valid = file_extension in allowed_extensions if file_extension else False
    
    if not content_type_valid and not extension_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not supported. Detected: {file.content_type or 'None'}, Extension: {file_extension or 'None'}. Allowed types: {allowed_types}, Allowed extensions: {allowed_extensions}"
        )
    
    # Read file content
    try:
        content = await file.read()
        
        # Determine content type based on extension if MIME type is not reliable
        if file_extension in [".txt", ".md", ".markdown"]:
            try:
                text_content = content.decode('utf-8')
            except UnicodeDecodeError:
                # Try with different encodings
                try:
                    text_content = content.decode('utf-8', errors='replace')
                except UnicodeDecodeError:
                    try:
                        text_content = content.decode('latin-1')
                    except UnicodeDecodeError:
                        text_content = content.decode('utf-8', errors='ignore')
        elif file_extension == ".pdf":
            # For PDF, we'll store the binary content for now
            # In a real implementation, you'd extract text from PDF
            text_content = f"[PDF file: {file.filename}] - Text extraction not implemented yet"
        else:
            # Fallback: try to decode as text
            try:
                text_content = content.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    text_content = content.decode('utf-8', errors='replace')
                except UnicodeDecodeError:
                    text_content = f"[Binary file: {file.filename}] - Content could not be decoded as text"
                
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error reading file: {str(e)}"
        )
    
    # Determine source type based on file extension
    if file_extension == ".pdf":
        source_type = "pdf"
    elif file_extension in [".md", ".markdown"]:
        source_type = "markdown"
    else:
        source_type = "file"
    
    # Create knowledge item
    knowledge_item = KnowledgeItem(
        title=title,
        content=text_content,
        source_type=source_type,
        source_path=file.filename,
        scope=scope,
        org_id=current_user.org_id,
        created_by=current_user.user_id
    )
    
    db.add(knowledge_item)
    db.commit()
    db.refresh(knowledge_item)
    
    # Process the document (chunk and embed)
    try:
        chunker = DocumentChunker()
        embedding_ids = await chunker.process_and_store_document(
            knowledge_item.id, 
            text_content, 
            current_user.org_id, 
            current_user.user_id
        )
        print(f"Successfully processed document {knowledge_item.id}: {len(embedding_ids)} chunks created")
    except Exception as e:
        # Log detailed error but don't fail the upload
        import traceback
        print(f"Error processing document {knowledge_item.id}: {e}")
        print(f"Full traceback: {traceback.format_exc()}")
    
    # Get chunk count
    chunk_count = db.query(Embedding).filter(
        Embedding.knowledge_item_id == knowledge_item.id
    ).count()
    
    return KnowledgeItemResponse(
        id=knowledge_item.id,
        title=knowledge_item.title,
        content=knowledge_item.content,
        source_type=knowledge_item.source_type,
        source_path=knowledge_item.source_path,
        scope=knowledge_item.scope,
        version=knowledge_item.version,
        chunk_count=chunk_count,
        processed=chunk_count > 0,
        created_at=knowledge_item.created_at,
        updated_at=knowledge_item.updated_at
    )


@router.post("/{knowledge_id}/reprocess")
async def reprocess_knowledge_item(
    knowledge_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """Reprocess a knowledge item (re-chunk and re-embed)."""
    knowledge_item = db.query(KnowledgeItem).filter(
        KnowledgeItem.id == knowledge_id,
        KnowledgeItem.org_id == current_user.org_id
    ).filter(
        (KnowledgeItem.scope == "org_public") | 
        (KnowledgeItem.created_by == current_user.user_id)
    ).first()
    
    if not knowledge_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge item not found"
        )
    
    # Delete existing embeddings
    db.query(Embedding).filter(
        Embedding.knowledge_item_id == knowledge_id
    ).delete()
    
    # Reprocess the document
    try:
        chunker = DocumentChunker()
        await chunker.process_and_store_document(
            knowledge_item.id, 
            knowledge_item.content, 
            current_user.org_id, 
            current_user.user_id
        )
        
        db.commit()
        
        # Get new chunk count
        chunk_count = db.query(Embedding).filter(
            Embedding.knowledge_item_id == knowledge_id
        ).count()
        
        return {
            "message": "Knowledge item reprocessed successfully",
            "chunk_count": chunk_count
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reprocessing document: {str(e)}"
        )


@router.get("/{knowledge_id}", response_model=KnowledgeItemResponse)
async def get_knowledge_item(
    knowledge_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """Get a specific knowledge item by ID."""
    knowledge_item = db.query(KnowledgeItem).filter(
        KnowledgeItem.id == knowledge_id,
        KnowledgeItem.org_id == current_user.org_id
    ).filter(
        (KnowledgeItem.scope == "org_public") | 
        (KnowledgeItem.created_by == current_user.user_id)
    ).first()
    
    if not knowledge_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge item not found"
        )
    
    # Get chunk count
    chunk_count = db.query(Embedding).filter(
        Embedding.knowledge_item_id == knowledge_item.id
    ).count()
    
    return KnowledgeItemResponse(
        id=knowledge_item.id,
        title=knowledge_item.title,
        content=knowledge_item.content,
        source_type=knowledge_item.source_type,
        source_path=knowledge_item.source_path,
        scope=knowledge_item.scope,
        version=knowledge_item.version,
        chunk_count=chunk_count,
        processed=chunk_count > 0,
        created_at=knowledge_item.created_at,
        updated_at=knowledge_item.updated_at
    )


@router.get("/{knowledge_id}/chunks")
async def get_knowledge_chunks(
    knowledge_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """Get chunks for a specific knowledge item."""
    # Verify access to knowledge item
    knowledge_item = db.query(KnowledgeItem).filter(
        KnowledgeItem.id == knowledge_id,
        KnowledgeItem.org_id == current_user.org_id
    ).filter(
        (KnowledgeItem.scope == "org_public") | 
        (KnowledgeItem.created_by == current_user.user_id)
    ).first()
    
    if not knowledge_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge item not found"
        )
    
    # Get chunks
    chunks = db.query(Embedding).filter(
        Embedding.knowledge_item_id == knowledge_id
    ).order_by(Embedding.chunk_idx).all()
    
    return {
        "knowledge_item_id": knowledge_id,
        "title": knowledge_item.title,
        "chunks": [
            {
                "chunk_idx": chunk.chunk_idx,
                "content": chunk.content,
                "created_at": chunk.created_at
            }
            for chunk in chunks
        ]
    }


@router.delete("/{knowledge_id}")
async def delete_knowledge_item(
    knowledge_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """Delete a knowledge item and its embeddings."""
    knowledge_item = db.query(KnowledgeItem).filter(
        KnowledgeItem.id == knowledge_id,
        KnowledgeItem.org_id == current_user.org_id
    ).filter(
        (KnowledgeItem.scope == "org_public") | 
        (KnowledgeItem.created_by == current_user.user_id)
    ).first()
    
    if not knowledge_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge item not found"
        )
    
    # Delete embeddings first (cascade should handle this, but being explicit)
    db.query(Embedding).filter(
        Embedding.knowledge_item_id == knowledge_id
    ).delete()
    
    # Delete knowledge item
    db.delete(knowledge_item)
    db.commit()
    
    # Ensure sequential IDs starting from 1
    ensure_sequential_ids(db, "knowledge_item", "id")
    
    return {"message": "Knowledge item deleted successfully"}


@router.post("/reorder-ids")
async def reorder_knowledge_ids(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """Manually reorder knowledge item IDs to be sequential starting from 1."""
    try:
        ensure_sequential_ids(db, "knowledge_item", "id")
        return {"message": "Knowledge item IDs reordered successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reordering IDs: {str(e)}"
        )
