from sqlalchemy import Column, String, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
import uuid
import enum
from datetime import datetime
from ..core.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class ReminderStatus(str, enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class Reminder(Base):
    __tablename__ = "reminders"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    text = Column(String, nullable=False)
    due_time = Column(DateTime, nullable=False)
    status = Column(Enum(ReminderStatus), default=ReminderStatus.ACTIVE)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="reminders")

