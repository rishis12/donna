from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from enum import Enum

# Auth schemas
class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserResponse(BaseModel):
    id: UUID
    email: str
    is_active: bool
    google_connected: bool = False
    microsoft_connected: bool = False
    slack_connected: bool = False

# Utterance schemas
class UtteranceRequest(BaseModel):
    text: str
    current_time: str
    timezone: Optional[str] = "UTC"
    device_info: Optional[dict] = None

class IntentResponse(BaseModel):
    intent: str
    entities: dict
    response: str
    requires_confirmation: bool
    action_id: Optional[str] = None

# Reminder schemas
class ReminderStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class ReminderCreate(BaseModel):
    text: str
    due_time: datetime

class ReminderResponse(BaseModel):
    id: UUID
    text: str
    due_time: datetime
    status: ReminderStatus
    created_at: datetime

class ReminderList(BaseModel):
    reminders: List[ReminderResponse]

# Calendar schemas
class EventCreate(BaseModel):
    summary: str
    start_time: datetime
    end_time: datetime
    attendees: Optional[List[str]] = None
    description: Optional[str] = ""

class EventUpdate(BaseModel):
    summary: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    description: Optional[str] = None

# Email schemas
class EmailDraft(BaseModel):
    to: str
    subject: str
    body: str

class EmailSend(BaseModel):
    to: str
    subject: str
    body: str
    provider: str = "google"  # or "microsoft"

# Action confirmation
class ActionConfirm(BaseModel):
    action_id: str
    confirmed: bool

# Gmail account schemas
class GmailAccountCreate(BaseModel):
    email: str
    display_name: Optional[str] = None
    code: str  # OAuth authorization code
    is_primary: bool = False

class GmailAccountResponse(BaseModel):
    id: str
    email: str
    display_name: Optional[str]
    is_primary: bool
    is_active: bool
    last_synced: Optional[datetime]
    created_at: datetime

# Messaging account schemas
class MessagingAccountCreate(BaseModel):
    platform: str  # 'discord', 'slack'
    account_id: str
    account_name: Optional[str] = None
    channel_id: Optional[str] = None
    bot_token: Optional[str] = None
    webhook_url: Optional[str] = None
    access_token: Optional[str] = None

class MessagingAccountResponse(BaseModel):
    id: str
    platform: str
    account_id: str
    account_name: Optional[str]
    channel_id: Optional[str]
    is_active: bool
    is_webhook_active: bool
    created_at: datetime

class MessagingMessageSend(BaseModel):
    platform: str
    account_id: str
    channel_id: Optional[str] = None
    message: str
    thread_id: Optional[str] = None

