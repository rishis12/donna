from sqlalchemy import Column, String, DateTime, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
import enum
from datetime import datetime
from ..core.database import Base

class ReminderStatus(str, enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class Reminder(Base):
    __tablename__ = "reminders"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    text = Column(String, nullable=False)
    due_time = Column(DateTime, nullable=False)
    status = Column(Enum(ReminderStatus), default=ReminderStatus.ACTIVE)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="reminders")

