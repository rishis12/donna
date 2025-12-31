"""APScheduler background task scheduler."""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
import logging
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from ..core.database import async_session
from ..models.reminder import Reminder, ReminderStatus
from sqlalchemy import select, and_, text

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

async def check_due_reminders():
    """Background job to check for due reminders."""
    try:
        from ..core.database import async_session
        async with async_session() as session:
            now = datetime.utcnow()
            # Check reminders due in the next 5 minutes
            query = select(Reminder).where(
                and_(
                    Reminder.status == ReminderStatus.ACTIVE,
                    Reminder.due_time <= now
                )
            )
            result = await session.execute(query)
            reminders = result.scalars().all()
            
            if reminders:
                logger.info(f"Found {len(reminders)} due reminders")
                # In a real implementation, you'd send notifications here
                # For now, just log them
                for reminder in reminders:
                    logger.info(f"Reminder due: {reminder.text} (User: {reminder.user_id})")
                    # Mark as completed after processing
                    reminder.status = ReminderStatus.COMPLETED
                
                await session.commit()
    except Exception as e:
        logger.error(f"Error checking reminders: {str(e)}")

def start_scheduler():
    """Start the background scheduler."""
    if not scheduler.running:
        # Check for due reminders every minute
        scheduler.add_job(
            check_due_reminders,
            trigger=IntervalTrigger(minutes=1),
            id='check_reminders',
            name='Check due reminders',
            replace_existing=True
        )
        
        scheduler.start()
        logger.info("Background scheduler started")
    else:
        logger.warning("Scheduler already running")

def shutdown_scheduler():
    """Shutdown the scheduler gracefully."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Background scheduler stopped")

