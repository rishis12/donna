from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from datetime import datetime, timedelta
from uuid import UUID
from typing import List, Optional
from ..models.reminder import Reminder, ReminderStatus

async def create_reminder(
    db: AsyncSession,
    user_id: UUID,
    text: str,
    due_time: datetime
) -> Reminder:
    reminder = Reminder(
        user_id=user_id,
        text=text,
        due_time=due_time,
        status=ReminderStatus.ACTIVE
    )
    db.add(reminder)
    await db.commit()
    await db.refresh(reminder)
    return reminder

async def get_user_reminders(
    db: AsyncSession,
    user_id: UUID,
    status: Optional[ReminderStatus] = None
) -> List[Reminder]:
    query = select(Reminder).where(Reminder.user_id == user_id)
    if status:
        query = query.where(Reminder.status == status)
    query = query.order_by(Reminder.due_time)
    result = await db.execute(query)
    return result.scalars().all()

async def get_due_reminders(
    db: AsyncSession,
    user_id: UUID,
    within_minutes: int = 5
) -> List[Reminder]:
    now = datetime.utcnow()
    future = now + timedelta(minutes=within_minutes)
    
    query = select(Reminder).where(
        and_(
            Reminder.user_id == user_id,
            Reminder.status == ReminderStatus.ACTIVE,
            Reminder.due_time >= now,
            Reminder.due_time <= future
        )
    )
    result = await db.execute(query)
    return result.scalars().all()

async def complete_reminder(db: AsyncSession, reminder_id: UUID) -> Optional[Reminder]:
    result = await db.execute(select(Reminder).where(Reminder.id == reminder_id))
    reminder = result.scalar_one_or_none()
    if reminder:
        reminder.status = ReminderStatus.COMPLETED
        await db.commit()
        await db.refresh(reminder)
    return reminder

async def cancel_reminder(db: AsyncSession, reminder_id: UUID) -> Optional[Reminder]:
    result = await db.execute(select(Reminder).where(Reminder.id == reminder_id))
    reminder = result.scalar_one_or_none()
    if reminder:
        reminder.status = ReminderStatus.CANCELLED
        await db.commit()
        await db.refresh(reminder)
    return reminder

