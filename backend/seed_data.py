#!/usr/bin/env python3
"""Seed script to populate the database with sample data."""

import asyncio
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models import Organization, User, Destination, KnowledgeItem
from app.auth.password import password_manager


def create_sample_data():
    """Create sample organizations, users, destinations, and knowledge items."""
    db = SessionLocal()
    
    try:
        # Create sample organization
        org = Organization(
            name="Sample Travel Agency",
            is_active=True
        )
        db.add(org)
        db.commit()
        db.refresh(org)
        
        # Create sample admin user
        admin_user = User(
            email="admin@example.com",
            hashed_password=password_manager.hash_password("admin123"),
            role="ADMIN",
            is_active=True,
            org_id=org.id
        )
        db.add(admin_user)
        
        # Create sample member user
        member_user = User(
            email="user@example.com",
            hashed_password=password_manager.hash_password("user123"),
            role="MEMBER",
            is_active=True,
            org_id=org.id
        )
        db.add(member_user)
        db.commit()
        db.refresh(admin_user)
        db.refresh(member_user)
        
        # Create sample destinations
        destinations = [
            Destination(
                name="Kyoto, Japan",
                country="Japan",
                city="Kyoto",
                description="Ancient capital of Japan with beautiful temples and traditional culture",
                tags=["cultural", "temples", "traditional", "family-friendly"],
                latitude="35.0116",
                longitude="135.7681",
                org_id=org.id
            ),
            Destination(
                name="Paris, France",
                country="France",
                city="Paris",
                description="City of Light with world-class museums and romantic atmosphere",
                tags=["museums", "art", "romantic", "cultural"],
                latitude="48.8566",
                longitude="2.3522",
                org_id=org.id
            ),
            Destination(
                name="Tokyo, Japan",
                country="Japan",
                city="Tokyo",
                description="Modern metropolis with cutting-edge technology and traditional culture",
                tags=["modern", "technology", "food", "family-friendly"],
                latitude="35.6762",
                longitude="139.6503",
                org_id=org.id
            )
        ]
        
        for dest in destinations:
            db.add(dest)
        
        # Create sample knowledge items
        knowledge_items = [
            KnowledgeItem(
                title="Japan Travel Guide",
                content="Japan is known for its rich cultural heritage, delicious cuisine, and modern technology. When visiting Japan, it's important to understand local customs such as bowing, removing shoes indoors, and being quiet on public transportation. The best time to visit is during spring (cherry blossom season) or autumn (fall colors).",
                source_type="manual",
                scope="org_public",
                org_id=org.id,
                created_by=admin_user.id
            ),
            KnowledgeItem(
                title="Paris Museum Tips",
                content="The Louvre Museum is the world's largest art museum and requires at least a full day to explore properly. Book tickets in advance to avoid long queues. The Musée d'Orsay houses the world's finest collection of Impressionist paintings. Many museums are closed on Mondays or Tuesdays, so plan accordingly.",
                source_type="manual",
                scope="org_public",
                org_id=org.id,
                created_by=admin_user.id
            ),
            KnowledgeItem(
                title="Family Travel Tips",
                content="When traveling with children, pack extra snacks, entertainment, and comfortable clothing. Research family-friendly restaurants and activities in advance. Many destinations offer special discounts for families. Consider staying in accommodations with kitchen facilities for convenience.",
                source_type="manual",
                scope="private",
                org_id=org.id,
                created_by=member_user.id
            )
        ]
        
        for item in knowledge_items:
            db.add(item)
        
        db.commit()
        print("Sample data created successfully!")
        print(f"Organization: {org.name} (ID: {org.id})")
        print(f"Admin user: {admin_user.email}")
        print(f"Member user: {member_user.email}")
        print(f"Created {len(destinations)} destinations")
        print(f"Created {len(knowledge_items)} knowledge items")
        
    except Exception as e:
        print(f"Error creating sample data: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    create_sample_data()

