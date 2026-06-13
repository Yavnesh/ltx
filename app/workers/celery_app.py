from celery import Celery
from kombu import Exchange, Queue

from app.infrastructure.config import settings

# Initialize Celery app
celery_app = Celery(
    "ltx_platform",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

# Configure Queues
default_exchange = Exchange("default", type="direct")
dlq_exchange = Exchange("dlq", type="direct")

celery_app.conf.task_queues = (
    Queue("default", default_exchange, routing_key="default"),
    Queue("dlq", dlq_exchange, routing_key="dlq"),
)

celery_app.conf.task_default_queue = "default"
celery_app.conf.task_default_exchange = "default"
celery_app.conf.task_default_routing_key = "default"

# Configure Celery settings
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    # Configure Celery Beat schedules
    beat_schedule={
        "cleanup-completed-jobs-every-hour": {
            "task": "app.workers.tasks.cleanup_task",
            "schedule": 3600.0,  # every hour
        },
        "heartbeat-health-check-every-30-seconds": {
            "task": "app.workers.tasks.health_task",
            "schedule": 30.0,  # every 30s
        },
    },
)

# Autodiscover tasks from app.workers package
celery_app.autodiscover_tasks(["app.workers"])
