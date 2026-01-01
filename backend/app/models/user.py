from sqlalchemy import Column, String, Boolean, DateTime, Text
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from ..core.models_base import Base

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=True)  # Nullable for OAuth-only users
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    onboarding_complete = Column(Boolean, default=False)
    
    # OAuth provider tracking
    auth_provider = Column(String, nullable=True)  # 'google', 'microsoft', or None for email/password
    
    # OAuth tokens (encrypted)
    google_access_token = Column(Text, nullable=True)
    google_refresh_token = Column(Text, nullable=True)
    microsoft_access_token = Column(Text, nullable=True)
    microsoft_refresh_token = Column(Text, nullable=True)
    slack_access_token = Column(Text, nullable=True)
    
    reminders = relationship("Reminder", back_populates="user")
    interactions = relationship("Interaction", back_populates="user")
    messaging_accounts = relationship("MessagingAccount", back_populates="user")
    history = relationship("UserHistory", back_populates="user", cascade="all, delete-orphan")

