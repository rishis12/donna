from sqlalchemy.orm import Session
from datetime import datetime
from ..models.user_memory import UserMemory

def get_active_memories_for_user(db: Session, user_id, limit: int = 20):
    return (
        db.query(UserMemory)
        .filter(
            UserMemory.user_id == user_id,
            UserMemory.is_active == True,
            (UserMemory.expires_at == None) | (UserMemory.expires_at > datetime.utcnow()),
        )
        .order_by(UserMemory.updated_at.desc())
        .limit(limit)
        .all()
    )

def upsert_memory(db: Session, user_id, key: str, type_: str, value: dict):
    existing = (
        db.query(UserMemory)
        .filter(UserMemory.user_id == user_id, UserMemory.key == key, UserMemory.is_active == True)
        .first()
    )

    if existing:
        existing.value = value
    else:
        existing = UserMemory(user_id=user_id, key=key, type=type_, value=value)
        db.add(existing)

    db.commit()
    return existing
