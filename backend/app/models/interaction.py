from sqlalchemy import Column, String, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from ..core.models_base import Base

def generate_uuid():
    return str(uuid.uuid4())

class Interaction(Base):
    __tablename__ = "interactions"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    user_message = Column(String, nullable=False)
    assistant_response = Column(String, nullable=False)
    intent = Column(String, nullable=True)
    entities = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="interactions")

