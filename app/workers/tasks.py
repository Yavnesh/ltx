import os
import time
from datetime import datetime
from uuid import UUID

import structlog
from celery.exceptions import MaxRetriesExceededError

from app.infrastructure.database import SessionLocal
from app.infrastructure.generators import get_video_generator
from app.infrastructure.models import JobStatus
from app.services.job_service import JobService
from app.services.storage_service import StorageService
from app.workers.celery_app import celery_app

logger = structlog.get_logger()


@celery_app.task(
    bind=True,
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,  # Exponential backoff
    retry_jitter=True,
)
def generate_video_task(
    self,
    job_id: str,
    prompt: str,
    duration: int,
    resolution: str,
    fps: int,
    seed: int,
) -> str:
    logger.info(
        "Task generate_video_task started", job_id=job_id, retry=self.request.retries
    )

    db = SessionLocal()
    job_service = JobService(db)
    storage_service = StorageService()
    generator = get_video_generator()

    # Transition to PROCESSING on task startup
    try:
        job_service.transition_status(UUID(job_id), JobStatus.PROCESSING)
    except Exception as e:
        logger.error(
            "Failed to transition status to PROCESSING", job_id=job_id, error=str(e)
        )
        db.close()
        return f"failed_initial_transition: {str(e)}"

    local_path = f"/tmp/{job_id}.mp4"

    try:
        # Generate the video
        generator.generate(
            prompt=prompt,
            duration=duration,
            resolution=resolution,
            fps=fps,
            seed=seed,
            output_path=local_path,
        )

        # Upload the video to Object Storage
        filename = f"{job_id}.mp4"
        video_url = storage_service.upload_video(local_path, filename)

        # Transition status to COMPLETED
        job_service.transition_status(
            UUID(job_id),
            JobStatus.COMPLETED,
            video_url=video_url,
        )

        logger.info(
            "Video generation and upload completed successfully",
            job_id=job_id,
            url=video_url,
        )
        return video_url

    except Exception as exc:
        logger.error(
            "Exception during video generation task execution",
            job_id=job_id,
            error=str(exc),
        )
        # Handle retry flow
        try:
            db.close()
            # Clean up local file if it exists
            if os.path.exists(local_path):
                os.remove(local_path)

            # Retry task
            # Calculate exponential backoff manually or let celery retry_backoff handle it
            countdown = int(2**self.request.retries) + 5
            raise self.retry(exc=exc, countdown=countdown)

        except MaxRetriesExceededError:
            logger.error("Max retries exceeded for job", job_id=job_id)
            # Re-establish db session to mark as failed
            db_fail = SessionLocal()
            js_fail = JobService(db_fail)
            try:
                js_fail.transition_status(
                    UUID(job_id),
                    JobStatus.FAILED,
                    failure_reason=f"Failed after max retries. Error: {str(exc)}",
                )
            except Exception as transition_err:
                logger.error(
                    "Failed to update status to FAILED on max retries",
                    error=str(transition_err),
                )
            finally:
                db_fail.close()

            # Push to DLQ exchange
            # Send message manually to DLQ
            celery_app.send_task(
                "app.workers.tasks.dead_letter_task",
                args=[job_id, str(exc)],
                queue="dlq",
            )
            raise exc
    finally:
        # Clean up local temporary file
        if os.path.exists(local_path):
            try:
                os.remove(local_path)
            except OSError:
                pass
        db.close()


@celery_app.task
def dead_letter_task(job_id: str, error_msg: str) -> None:
    logger.critical(
        "Job failed permanently and sent to DLQ", job_id=job_id, error=error_msg
    )


@celery_app.task
def cleanup_task() -> str:
    logger.info("Periodic cleanup task running")
    # Clean up any local files in /tmp/ltx_storage older than 24 hours if running in local storage mode
    from app.infrastructure.config import settings

    if settings.STORAGE_PROVIDER_TYPE == "local" and os.path.exists(
        settings.STORAGE_LOCAL_PATH
    ):
        count = 0
        now = time.time()
        for f in os.listdir(settings.STORAGE_LOCAL_PATH):
            fp = os.path.join(settings.STORAGE_LOCAL_PATH, f)
            # Delete if older than 1 day
            if os.stat(fp).st_mtime < now - 86400:
                os.remove(fp)
                count += 1
        logger.info("Cleaned up expired files from local storage", count=count)
    return "cleanup_completed"


@celery_app.task
def health_task() -> str:
    # Heartbeat task writes status to Redis to prove Celery worker is active
    import redis

    from app.infrastructure.config import settings

    r = redis.Redis.from_url(settings.REDIS_URL)
    timestamp = datetime.utcnow().isoformat()
    r.set("celery_worker_heartbeat", timestamp)
    logger.debug("Worker heartbeat written", timestamp=timestamp)
    return timestamp
