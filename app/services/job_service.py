from uuid import UUID
from sqlalchemy.orm import Session
import structlog

from app.infrastructure.models import Job, JobStatus
from app.repositories.job_repository import JobRepository

logger = structlog.get_logger()

# Allowed state transitions definition
VALID_TRANSITIONS = {
    JobStatus.QUEUED.value: [JobStatus.PROCESSING.value, JobStatus.CANCELLED.value],
    JobStatus.PROCESSING.value: [JobStatus.COMPLETED.value, JobStatus.FAILED.value],
}


class JobService:
    def __init__(self, db: Session):
        self.job_repo = JobRepository(db)

    def create_job(
        self,
        user_id: UUID,
        prompt: str,
        duration: int,
        resolution: str,
        seed: int,
    ) -> Job:
        return self.job_repo.create(
            user_id=user_id,
            prompt=prompt,
            duration=duration,
            resolution=resolution,
            seed=seed,
        )

    def get_job(self, job_id: UUID) -> Job | None:
        return self.job_repo.get_by_id(job_id)

    def get_user_job(self, job_id: UUID, user_id: UUID) -> Job | None:
        return self.job_repo.get_by_id_and_user(job_id, user_id)

    def transition_status(
        self,
        job_id: UUID,
        target_status: JobStatus,
        video_url: str | None = None,
        failure_reason: str | None = None,
    ) -> Job:
        job = self.job_repo.get_by_id(job_id)
        if not job:
            raise ValueError(f"Job with ID {job_id} not found")

        current_status = job.status
        allowed = VALID_TRANSITIONS.get(current_status, [])

        if target_status.value not in allowed:
            raise ValueError(
                f"Invalid transition from status '{current_status}' to '{target_status.value}'"
            )

        updated_job = self.job_repo.update_status(
            job_id=job_id,
            status=target_status,
            video_url=video_url,
            failure_reason=failure_reason,
        )
        logger.info(
            "Job transitioned status",
            job_id=str(job_id),
            from_status=current_status,
            to_status=target_status.value,
        )
        return updated_job

    def list_user_jobs(
        self,
        user_id: UUID,
        status: str | None = None,
        sort_by: str = "created_at",
        sort_dir: str = "desc",
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Job], int]:
        return self.job_repo.list_jobs(
            user_id=user_id,
            status=status,
            sort_by=sort_by,
            sort_dir=sort_dir,
            limit=limit,
            offset=offset,
        )

    def delete_job(self, job_id: UUID, user_id: UUID) -> bool:
        job = self.job_repo.get_by_id_and_user(job_id, user_id)
        if not job:
            return False

        # If job is running, we cancel it, or clean up any associated storage files
        if job.status == JobStatus.QUEUED.value or job.status == JobStatus.PROCESSING.value:
            # Enforce CANCELLED status transition if deleting a running/queued job
            try:
                self.transition_status(job_id, JobStatus.CANCELLED)
            except Exception:
                pass

        return self.job_repo.delete(job_id)
