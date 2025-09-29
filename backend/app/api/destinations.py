from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.core.database import get_db
from app.models.destination import Destination
from app.models.organization import Organization
from app.auth.middleware import get_current_user, CurrentUser
from app.core.database_utils import ensure_sequential_ids

router = APIRouter(prefix="/destinations", tags=["destinations"])


class DestinationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Destination name")
    country: str = Field(..., min_length=1, max_length=100, description="Country")
    city: str = Field(..., min_length=1, max_length=100, description="City")
    description: Optional[str] = Field(None, description="Description")
    tags: Optional[List[str]] = Field(default_factory=list, description="Tags")
    latitude: Optional[float] = Field(None, description="Latitude")
    longitude: Optional[float] = Field(None, description="Longitude")


class DestinationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    country: Optional[str] = Field(None, min_length=1, max_length=100)
    city: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class DestinationResponse(BaseModel):
    id: int
    name: str
    country: str
    city: str
    description: Optional[str]
    tags: List[str]
    latitude: Optional[str]
    longitude: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


@router.get("/", response_model=List[DestinationResponse])
async def get_destinations(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """Get all destinations for the current user's organization."""
    destinations = db.query(Destination).filter(
        Destination.org_id == current_user.org_id,
        Destination.is_deleted == False
    ).all()
    
    return destinations


@router.post("/", response_model=DestinationResponse, status_code=status.HTTP_201_CREATED)
async def create_destination(
    destination_data: DestinationCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """Create a new destination."""
    # Check if destination with same name already exists in organization
    existing = db.query(Destination).filter(
        Destination.org_id == current_user.org_id,
        Destination.name == destination_data.name,
        Destination.is_deleted == False
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Destination with this name already exists"
        )
    
    # Create new destination
    destination = Destination(
        name=destination_data.name,
        country=destination_data.country,
        city=destination_data.city,
        description=destination_data.description,
        tags=destination_data.tags or [],
        latitude=str(destination_data.latitude) if destination_data.latitude else None,
        longitude=str(destination_data.longitude) if destination_data.longitude else None,
        org_id=current_user.org_id
    )
    
    db.add(destination)
    db.commit()
    db.refresh(destination)
    
    return destination


@router.get("/{destination_id}", response_model=DestinationResponse)
async def get_destination(
    destination_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """Get a specific destination by ID."""
    destination = db.query(Destination).filter(
        Destination.id == destination_id,
        Destination.org_id == current_user.org_id,
        Destination.is_deleted == False
    ).first()
    
    if not destination:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Destination not found"
        )
    
    return destination


@router.put("/{destination_id}", response_model=DestinationResponse)
async def update_destination(
    destination_id: int,
    destination_data: DestinationUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """Update a destination."""
    destination = db.query(Destination).filter(
        Destination.id == destination_id,
        Destination.org_id == current_user.org_id,
        Destination.is_deleted == False
    ).first()
    
    if not destination:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Destination not found"
        )
    
    # Check for name conflicts if name is being updated
    if destination_data.name and destination_data.name != destination.name:
        existing = db.query(Destination).filter(
            Destination.org_id == current_user.org_id,
            Destination.name == destination_data.name,
            Destination.id != destination_id,
            Destination.is_deleted == False
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Destination with this name already exists"
            )
    
    # Update fields
    update_data = destination_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "latitude" and value is not None:
            setattr(destination, field, str(value))
        elif field == "longitude" and value is not None:
            setattr(destination, field, str(value))
        else:
            setattr(destination, field, value)
    
    db.commit()
    db.refresh(destination)
    
    return destination


@router.delete("/{destination_id}")
async def delete_destination(
    destination_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """Soft delete a destination."""
    destination = db.query(Destination).filter(
        Destination.id == destination_id,
        Destination.org_id == current_user.org_id,
        Destination.is_deleted == False
    ).first()
    
    if not destination:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Destination not found"
        )
    
    # Soft delete
    destination.is_deleted = True
    db.commit()
    
    # Ensure sequential IDs starting from 1 (only for active destinations)
    ensure_sequential_ids(db, "destination", "id")
    
    return {"message": "Destination deleted successfully"}


@router.post("/reorder-ids")
async def reorder_destination_ids(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """Manually reorder destination IDs to be sequential starting from 1."""
    try:
        ensure_sequential_ids(db, "destination", "id")
        return {"message": "Destination IDs reordered successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reordering IDs: {str(e)}"
        )
