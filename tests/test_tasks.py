from unittest.mock import patch, MagicMock
import pytest
from uuid import uuid4

from app.infrastructure.models import Job, JobStatus, User
from app.workers.tasks import generate_video_task


@pytest.fixture
def test_user_and_job(db_session):
    # Create user
    user = User(email="task-tester@example.com", password_hash="hash")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # Create job
    job = Job(
        user_id=user.id,
        prompt="rendering tasks test",
        status=JobStatus.QUEUED.value,
        seed=111,
        duration=5,
        resolution="720p",
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    return user, job


@patch("app.workers.tasks.get_video_generator")
@patch("app.workers.tasks.StorageService")
@patch("app.workers.tasks.SessionLocal")
def test_generate_video_task_success(mock_session_local, mock_storage_service, mock_get_gen, test_user_and_job, db_session):
    user, job = test_user_and_job

    # Set up DB session mocks
    db_session.close = MagicMock()
    mock_session_local.return_value = db_session

    # Set up generator mock
    mock_gen = MagicMock()
    mock_get_gen.return_value = mock_gen

    # Set up storage upload mock
    mock_storage = MagicMock()
    mock_storage.upload_video.return_value = "https://s3.amazonaws.com/test-bucket/videos/test-job.mp4"
    mock_storage_service.return_value = mock_storage

    job_uuid = job.id
    job_prompt = job.prompt
    job_duration = job.duration
    job_resolution = job.resolution
    job_seed = job.seed

    # Execute task synchronously
    result = generate_video_task.run(
        job_id=str(job_uuid),
        prompt=job_prompt,
        duration=job_duration,
        resolution=job_resolution,
        fps=24,
        seed=job_seed,
    )

    # Assert results
    assert result == "https://s3.amazonaws.com/test-bucket/videos/test-job.mp4"
    mock_gen.generate.assert_called_once()
    mock_storage.upload_video.assert_called_once()

    # Re-fetch job to verify it's COMPLETED
    db_session.refresh(job)
    assert job.status == JobStatus.COMPLETED.value
    assert job.video_url == "https://s3.amazonaws.com/test-bucket/videos/test-job.mp4"
    assert job.started_at is not None
    assert job.completed_at is not None
