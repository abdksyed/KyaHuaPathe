import uuid
from datetime import datetime
from enum import Enum

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pydantic import BaseModel, Field


class TriggerType(str, Enum):
    DATE = "date"
    CRON = "cron"


class CronParameters(BaseModel):
    year: str | None = Field(default=None)
    month: str | None = Field(default=None)
    day: str | None = Field(default=None)
    week: str | None = Field(default=None)
    day_of_week: str | None = Field(default=None)
    hour: str | None = Field(default=None)
    minute: str | None = Field(default=None)
    second: str | None = Field(default=None)


class TaskService:
    _instance: "TaskService" | None = None  # singleton instance

    def __init__(self, db_url: str):
        self._db_url = db_url
        self.scheduler = AsyncIOScheduler(
            jobstores={"default": SQLAlchemyJobStore(url=self._db_url)},
            job_defaults={
                "coalesce": True,  # if missed multiple times, run only once
                "misfire_grace_time": None,  # always fire, even if late
            },
        )

    @classmethod
    def get_instance(cls, db_url: str) -> "TaskService":
        if cls._instance is None:
            cls._instance = cls(db_url)
        if cls._instance is not None and db_url != cls._instance._db_url:
            raise ValueError("TaskService already initialized with a different db_url")
        return cls._instance

    # region lifespan management

    async def start(self):
        self.scheduler.start()

    async def stop(self):
        self.scheduler.shutdown()

    # endregion

    # region CRUD operations
    async def create_task(
        self,
        message: str,
        trigger_type: TriggerType,
        chat_id: int,
        reply_message_id: int,
        trigger_time: str | None = None,
        cron_parameters: CronParameters | None = None,
    ) -> str:
        """Create a scheduled task.

        Args:
            message: The reminder message to send.
            trigger_type: One of DATE or CRON.
            chat_id: The Telegram chat ID to send the reminder to.
            reply_message_id: The Telegram message ID to reply to.
            trigger_time: Required for DATE trigger - when to fire.
            cron_parameters: Required for CRON trigger - schedule pattern.
        """
        reminder_id = str(uuid.uuid4())

        job_kwargs = {
            "func": "src.tasks:send_reminder",  # Use string reference for serialization
            "trigger": trigger_type.value,
            "kwargs": {
                "message": message,
                "chat_id": chat_id,
                "reply_message_id": reply_message_id,
            },
            "id": reminder_id,
        }

        if trigger_type == TriggerType.DATE:
            if not trigger_time:
                raise ValueError("trigger_time is required for DATE trigger")
            job_kwargs["run_date"] = datetime.fromisoformat(trigger_time)
        elif trigger_type == TriggerType.CRON:
            if not cron_parameters:
                raise ValueError("cron_parameters is required for CRON trigger")
            # Exclude None values to avoid APScheduler errors
            cron_kwargs = {
                k: v for k, v in cron_parameters.model_dump().items() if v is not None
            }
            if not cron_kwargs:
                raise ValueError("Atleast one cron field must be specified")

            job_kwargs.update(cron_kwargs)

        self.scheduler.add_job(**job_kwargs)
        return reminder_id

    async def delete_task(self, task_id: str):
        self.scheduler.remove_job(task_id)

    async def list_tasks(self, chat_id: int) -> list[dict]:
        """List all scheduled tasks for a specific chat."""
        jobs = self.scheduler.get_jobs()
        reminders = []
        for job in jobs:
            if job.kwargs["chat_id"] != chat_id:
                continue
            reminders.append(
                {
                    "id": job.id,
                    "message": job.kwargs["message"],
                    "next_run_time": str(job.next_run_time),
                    "trigger": str(job.trigger),
                }
            )
        return reminders


async def send_reminder(message: str, chat_id: int, reply_message_id: int):
    """Send a reminder message to a Telegram chat.

    This function is called by APScheduler when a reminder fires.
    Uses the global application from bot.py to send messages.
    """
    # Import here to avoid circular imports
    from src.telegram.bot import application, send_reply_to_chat

    if application and application.bot:
        await send_reply_to_chat(
            message=f"🔔 **Reminder**\n\n{message}",
            bot=application.bot,
            chat_id=chat_id,
            reply_message_id=reply_message_id,
        )
