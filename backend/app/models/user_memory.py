from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Float, JSON
from sqlalchemy.sql import func
import uuid
from ..db.base import Base

def generate_uuid():
    return str(uuid.uuid4())

class UserMemory(Base):
    __tablename__ = "user_memory"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), index=True, nullable=False)

    type = Column(String, nullable=False)  # "preference" | "habit" | "fact"
    key = Column(String, nullable=False)
    value = Column(JSON, nullable=False)

    confidence = Column(Float, default=0.8)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)