from datetime import datetime
from uuid import UUID

from sqlalchemy import asc, desc
from sqlalchemy.orm import Session

from app.infrastructure.models import Job, JobEvent, JobStatus


class JobRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, job_id: UUID) -> Job | None:
        return self.db.query(Job).filter(Job.id == job_id).first()

    def get_by_id_and_user(self, job_id: UUID, user_id: UUID) -> Job | None:
        return (
            self.db.query(Job).filter(Job.id == job_id, Job.user_id == user_id).first()
        )

    def create(
        self,
        user_id: UUID,
        prompt: str,
        duration: int,
        resolution: str,
        seed: int,
    ) -> Job:
        job = Job(
            user_id=user_id,
            prompt=prompt,
            duration=duration,
            resolution=resolution,
            seed=seed,
            status=JobStatus.QUEUED.value,
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        self.create_event(job.id, "JOB_CREATED", {"status": JobStatus.QUEUED.value})
        return job

    def update_status(
        self,
        job_id: UUID,
        status: JobStatus,
        video_url: str | None = None,
        failure_reason: str | None = None,
    ) -> Job | None:
        job = self.get_by_id(job_id)
        if not job:
            return None

        # Update timestamps based on state transitions
        if status == JobStatus.PROCESSING:
            job.started_at = datetime.utcnow()
        elif status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
            job.completed_at = datetime.utcnow()

        job.status = status.value
        if video_url is not None:
            job.video_url = video_url
        if failure_reason is not None:
            job.failure_reason = failure_reason

        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)

        self.create_event(
            job_id,
            f"JOB_STATUS_{status.value}",
            {
                "video_url": video_url,
                "failure_reason": failure_reason,
            },
        )
        return job

    def delete(self, job_id: UUID) -> bool:
        job = self.get_by_id(job_id)
        if not job:
            return False
        self.db.delete(job)
        self.db.commit()
        return True

    def list_jobs(
        self,
        user_id: UUID,
        status: str | None = None,
        sort_by: str = "created_at",
        sort_dir: str = "desc",
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Job], int]:
        query = self.db.query(Job).filter(Job.user_id == user_id)

        if status:
            query = query.filter(Job.status == status.upper())

        # Sorting
        sort_column = getattr(Job, sort_by, Job.created_at)
        if sort_dir.lower() == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))

        total = query.count()
        items = query.offset(offset).limit(limit).all()

        return items, total

    def create_event(
        self, job_id: UUID, event_type: str, payload: dict | None = None
    ) -> JobEvent:
        event = JobEvent(
            job_id=job_id,
            event_type=event_type,
            payload=payload,
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event
