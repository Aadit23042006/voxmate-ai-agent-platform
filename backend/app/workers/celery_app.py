import os
from celery import Celery


# REDIS_URL must be provided by the runtime environment.
# Local development should define REDIS_URL in .env.
REDIS_URL = os.getenv("REDIS_URL")

if not REDIS_URL:
    raise RuntimeError(
        "REDIS_URL is required. Configure it in the environment before starting Celery."
    )


# Initialize Celery application
celery_app = Celery(
    "voxmate",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        "app.workers.tasks",
    ],
)

# Configure Celery execution settings
celery_app.conf.update(
    broker_connection_retry_on_startup=True,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,
)

# Periodic processors. The worker is launched with --beat in docker-compose.yml.
# Tasks are idempotent at the application level where the underlying records
# have a sent/last_run state; keep the interval conservative.
celery_app.conf.beat_schedule = {
    "process-smart-notifications-every-minute": {
        "task": "app.workers.tasks.process_smart_notifications",
        "schedule": 60.0,
    },
    "process-workflow-automations-every-minute": {
        "task": "app.workers.tasks.process_workflow_automations",
        "schedule": 60.0,
    },
}


if __name__ == "__main__":
    celery_app.start()
