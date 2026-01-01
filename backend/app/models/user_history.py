from sqlalchemy import Column, String, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from ..core.models_base import Base

def generate_uuid():
    return str(uuid.uuid4())

class UserHistory(Base):
    __tablename__ = "user_history"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    message = Column(Text, nullable=False)
    intent = Column(String, nullable=True)
    meta_data = Column(JSON, nullable=True)  # Renamed from metadata (reserved in SQLAlchemy)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    user = relationship("User", back_populates="history")
