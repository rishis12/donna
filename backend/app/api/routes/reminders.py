from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID
from ..schemas import ReminderCreate, ReminderResponse, ReminderList, ReminderStatus
from ..deps import get_current_user
from ...core.database import get_db
from ...models.user import User
from ...services import reminder_service
from ...models.reminder import ReminderStatus as DBReminderStatus

router = APIRouter(prefix="/reminders", tags=["reminders"])

@router.post("/create", response_model=ReminderResponse)
async def create_reminder(
    data: ReminderCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    reminder = await reminder_service.create_reminder(
        db, user.id, data.text, data.due_time
    )
    return ReminderResponse(
        id=reminder.id,
        text=reminder.text,
        due_time=reminder.due_time,
        status=ReminderStatus(reminder.status.value),
        created_at=reminder.created_at
    )

@router.get("/list", response_model=ReminderList)
async def list_reminders(
    status: Optional[ReminderStatus] = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    db_status = DBReminderStatus(status.value) if status else None
    reminders = await reminder_service.get_user_reminders(db, user.id, db_status)
    return ReminderList(reminders=[
        ReminderResponse(
            id=r.id,
            text=r.text,
            due_time=r.due_time,
            status=ReminderStatus(r.status.value),
            created_at=r.created_at
        ) for r in reminders
    ])

@router.get("/due", response_model=ReminderList)
async def get_due_reminders(
    within_minutes: int = 5,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    reminders = await reminder_service.get_due_reminders(db, user.id, within_minutes)
    return ReminderList(reminders=[
        ReminderResponse(
            id=r.id,
            text=r.text,
            due_time=r.due_time,
            status=ReminderStatus(r.status.value),
            created_at=r.created_at
        ) for r in reminders
    ])

@router.post("/{reminder_id}/complete", response_model=ReminderResponse)
async def complete_reminder(
    reminder_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    reminder = await reminder_service.complete_reminder(db, reminder_id)
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")
    return ReminderResponse(
        id=reminder.id,
        text=reminder.text,
        due_time=reminder.due_time,
        status=ReminderStatus(reminder.status.value),
        created_at=reminder.created_at
    )

@router.post("/{reminder_id}/cancel", response_model=ReminderResponse)
async def cancel_reminder(
    reminder_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    reminder = await reminder_service.cancel_reminder(db, reminder_id)
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")
    return ReminderResponse(
        id=reminder.id,
        text=reminder.text,
        due_time=reminder.due_time,
        status=ReminderStatus(reminder.status.value),
        created_at=reminder.created_at
    )

