from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.database import engine


def reset_sequence_after_delete(session: Session, table_name: str, id_column: str = "id"):
    """Reset the sequence for a table after deletions to ensure sequential IDs."""
    try:
        # Get the current maximum ID
        result = session.execute(text(f"SELECT COALESCE(MAX({id_column}), 0) FROM {table_name}"))
        max_id = result.scalar()
        
        # Reset the sequence to start from max_id + 1
        sequence_name = f"{table_name}_{id_column}_seq"
        session.execute(text(f"SELECT setval('{sequence_name}', {max_id + 1}, false)"))
        session.commit()
        
        print(f"Reset sequence {sequence_name} to {max_id + 1}")
    except Exception as e:
        print(f"Error resetting sequence for {table_name}: {e}")
        session.rollback()


def ensure_sequential_ids(session: Session, table_name: str, id_column: str = "id"):
    """Ensure IDs are sequential starting from 1."""
    try:
        # Get all records ordered by current ID
        result = session.execute(text(f"SELECT {id_column} FROM {table_name} ORDER BY {id_column}"))
        current_ids = [row[0] for row in result.fetchall()]
        
        if not current_ids:
            return
        
        # Check if IDs are already sequential starting from 1
        expected_ids = list(range(1, len(current_ids) + 1))
        if current_ids == expected_ids:
            return  # Already sequential
        
        # For tables with foreign key references, we need to handle them carefully
        if table_name == "knowledge_item":
            # Handle knowledge_item table with foreign key references
            _reorder_knowledge_item_ids(session, current_ids)
        elif table_name == "destination":
            # Handle destination table (soft delete, so different approach)
            _reorder_destination_ids(session, current_ids)
        else:
            # Generic reordering for other tables
            _reorder_generic_ids(session, table_name, id_column, current_ids)
        
        session.commit()
        print(f"Reassigned IDs for {table_name} to be sequential from 1 to {len(current_ids)}")
    except Exception as e:
        print(f"Error ensuring sequential IDs for {table_name}: {e}")
        session.rollback()


def _reorder_knowledge_item_ids(session: Session, current_ids: list):
    """Reorder knowledge_item IDs and update related embedding records."""
    # Temporarily disable foreign key constraints
    session.execute(text("SET session_replication_role = replica;"))
    
    try:
        # First, update embedding records to use temporary IDs
        for i, old_id in enumerate(current_ids):
            new_temp_id = 10000 + i + 1  # Use high numbers to avoid conflicts
            if old_id != new_temp_id:
                # Update embeddings first
                session.execute(text(f"UPDATE embedding SET knowledge_item_id = {new_temp_id} WHERE knowledge_item_id = {old_id}"))
                # Update knowledge_item
                session.execute(text(f"UPDATE knowledge_item SET id = {new_temp_id} WHERE id = {old_id}"))
        
        # Then reassign to final sequential IDs
        for i, old_temp_id in enumerate([10000 + j + 1 for j in range(len(current_ids))]):
            new_id = i + 1
            # Update embeddings
            session.execute(text(f"UPDATE embedding SET knowledge_item_id = {new_id} WHERE knowledge_item_id = {old_temp_id}"))
            # Update knowledge_item
            session.execute(text(f"UPDATE knowledge_item SET id = {new_id} WHERE id = {old_temp_id}"))
        
        # Reset sequence
        session.execute(text(f"SELECT setval('knowledge_item_id_seq', {len(current_ids)}, true)"))
    
    finally:
        # Re-enable foreign key constraints
        session.execute(text("SET session_replication_role = DEFAULT;"))


def _reorder_destination_ids(session: Session, current_ids: list):
    """Reorder destination IDs (soft delete table)."""
    # For destinations, we only reorder non-deleted records
    result = session.execute(text("SELECT id FROM destination WHERE is_deleted = false ORDER BY id"))
    active_ids = [row[0] for row in result.fetchall()]
    
    if not active_ids:
        return
    
    # Check if IDs are already sequential starting from 1
    expected_ids = list(range(1, len(active_ids) + 1))
    if active_ids == expected_ids:
        return  # Already sequential
    
    # Temporarily disable foreign key constraints
    session.execute(text("SET session_replication_role = replica;"))
    
    try:
        # Use temporary IDs to avoid conflicts
        for i, old_id in enumerate(active_ids):
            new_temp_id = 10000 + i + 1
            if old_id != new_temp_id:
                session.execute(text(f"UPDATE destination SET id = {new_temp_id} WHERE id = {old_id}"))
        
        # Reassign to final sequential IDs
        for i, old_temp_id in enumerate([10000 + j + 1 for j in range(len(active_ids))]):
            new_id = i + 1
            session.execute(text(f"UPDATE destination SET id = {new_id} WHERE id = {old_temp_id}"))
        
        # Reset sequence
        session.execute(text(f"SELECT setval('destination_id_seq', {len(active_ids)}, true)"))
    
    finally:
        # Re-enable foreign key constraints
        session.execute(text("SET session_replication_role = DEFAULT;"))


def _reorder_generic_ids(session: Session, table_name: str, id_column: str, current_ids: list):
    """Generic ID reordering for tables without complex foreign key relationships."""
    # Use temporary IDs to avoid conflicts
    for i, old_id in enumerate(current_ids):
        new_temp_id = 10000 + i + 1
        if old_id != new_temp_id:
            session.execute(text(f"UPDATE {table_name} SET {id_column} = {new_temp_id} WHERE {id_column} = {old_id}"))
    
    # Reassign to final sequential IDs
    for i, old_temp_id in enumerate([10000 + j + 1 for j in range(len(current_ids))]):
        new_id = i + 1
        session.execute(text(f"UPDATE {table_name} SET {id_column} = {new_id} WHERE {id_column} = {old_temp_id}"))
    
    # Reset sequence
    sequence_name = f"{table_name}_{id_column}_seq"
    session.execute(text(f"SELECT setval('{sequence_name}', {len(current_ids)}, true)"))
