from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from ..core.database import Base

class MessagingAccount(Base):
    __tablename__ = "messaging_accounts"

    id = Column(String(36), primary_key=True, default=lambda: str(__import__('uuid').uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)

    # Platform type: 'discord', 'slack'
    platform = Column(String, nullable=False, index=True)

    # Platform-specific identifiers
    account_id = Column(String, nullable=False)  # User ID, Channel ID, etc.
    account_name = Column(String, nullable=True)  # Display name
    channel_id = Column(String, nullable=True)  # For Discord/Slack channels

    # Bot/API credentials (encrypted)
    bot_token = Column(String, nullable=True)  # For bot integrations
    webhook_url = Column(String, nullable=True)  # For webhook integrations
    access_token = Column(String, nullable=True)  # For OAuth integrations

    # Account status
    is_active = Column(Boolean, default=True)
    is_webhook_active = Column(Boolean, default=False)

    # Metadata
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationship
    user = relationship("User", back_populates="messaging_accounts")

    def __repr__(self):
        return f"<MessagingAccount(platform='{self.platform}', name='{self.account_name}')>"
