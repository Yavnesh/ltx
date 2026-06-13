from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
import structlog

from app.api.dependencies import get_current_user, check_rate_limit
from app.api.schemas import (
    VideoJobCreateSchema,
    VideoJobListResponseSchema,
    VideoJobResponseSchema,
)
from app.infrastructure.database import get_db
from app.infrastructure.models import User
from app.services.job_service import JobService
from app.services.video_service import VideoService

router = APIRouter(prefix="/videos", tags=["videos"])
logger = structlog.get_logger()


@router.post(
    "", status_code=status.HTTP_202_ACCEPTED, dependencies=[Depends(check_rate_limit)]
)
def create_video_job(
    payload: VideoJobCreateSchema,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job_service = JobService(db)
    video_service = VideoService()

    # Reject oversized prompts or malicious looking strings (Security NFR)
    if len(payload.prompt.strip()) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Prompt is too short. Minimum 3 characters.",
        )

    # 1. Create Job in database in QUEUED state
    job = job_service.create_job(
        user_id=current_user.id,
        prompt=payload.prompt,
        duration=payload.duration,
        resolution=payload.resolution,
        seed=payload.seed,
    )

    # 2. Trigger asynchronous Celery video generation task
    # LTX Video standard FPS is typically 24
    video_service.trigger_generation(
        job_id=job.id,
        prompt=job.prompt,
        duration=job.duration,
        resolution=job.resolution,
        fps=payload.fps,
        seed=job.seed,
    )

    logger.info("Created video job", job_id=str(job.id), user_id=str(current_user.id))

    return {
        "job_id": str(job.id),
        "status": job.status,
    }


@router.get("/{job_id}", response_model=VideoJobResponseSchema)
def get_video_job_status(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job_service = JobService(db)
    job = job_service.get_user_job(job_id, current_user.id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video job not found",
        )
    return job


@router.get("", response_model=VideoJobListResponseSchema)
def list_video_jobs(
    status: str | None = Query(None, description="Filter jobs by status"),
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_dir: str = Query("desc", description="Sort direction: asc or desc"),
    limit: int = Query(20, ge=1, le=100, description="Pagination limit"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job_service = JobService(db)

    # Check allowed sort columns to prevent SQL injection
    allowed_sort_fields = {
        "created_at",
        "started_at",
        "completed_at",
        "status",
        "duration",
    }
    if sort_by not in allowed_sort_fields:
        sort_by = "created_at"

    items, total = job_service.list_user_jobs(
        user_id=current_user.id,
        status=status,
        sort_by=sort_by,
        sort_dir=sort_dir,
        limit=limit,
        offset=offset,
    )

    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_video_job(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job_service = JobService(db)
    success = job_service.delete_job(job_id, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video job not found",
        )
    logger.info("Deleted video job", job_id=str(job_id), user_id=str(current_user.id))
    return None
