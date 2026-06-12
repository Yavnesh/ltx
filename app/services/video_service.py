from uuid import UUID
import structlog

logger = structlog.get_logger()


class VideoService:
    def trigger_generation(
        self,
        job_id: UUID,
        prompt: str,
        duration: int,
        resolution: str,
        fps: int,
        seed: int,
    ) -> None:
        logger.info("Triggering video generation task via Celery", job_id=str(job_id))

        # Lazy import of Celery tasks to prevent circular imports
        from app.workers.tasks import generate_video_task

        # Dispatch task to Celery
        generate_video_task.delay(
            job_id=str(job_id),
            prompt=prompt,
            duration=duration,
            resolution=resolution,
            fps=fps,
            seed=seed,
        )
