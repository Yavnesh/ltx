from unittest.mock import patch
from uuid import uuid4


def test_create_video_job_unauthorized(client):
    payload = {
        "prompt": "astronaut riding horse on mars",
        "duration": 5,
        "resolution": "720p",
        "fps": 24,
        "seed": 123
    }
    response = client.post("/v1/videos", json=payload)
    assert response.status_code == 403


@patch("app.services.video_service.VideoService.trigger_generation")
def test_create_video_job_success(mock_trigger, client, auth_headers):
    payload = {
        "prompt": "astronaut riding horse on mars",
        "duration": 5,
        "resolution": "720p",
        "fps": 24,
        "seed": 123
    }
    response = client.post("/v1/videos", json=payload, headers=auth_headers)
    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "QUEUED"
    mock_trigger.assert_called_once()


def test_get_video_job_not_found(client, auth_headers):
    random_uuid = str(uuid4())
    response = client.get(f"/v1/videos/{random_uuid}", headers=auth_headers)
    assert response.status_code == 404


@patch("app.services.video_service.VideoService.trigger_generation")
def test_get_video_job_status(mock_trigger, client, auth_headers):
    payload = {
        "prompt": "flying over mountains",
        "duration": 10,
        "resolution": "720p",
        "fps": 24,
        "seed": 42
    }
    create_resp = client.post("/v1/videos", json=payload, headers=auth_headers)
    job_id = create_resp.json()["job_id"]

    status_resp = client.get(f"/v1/videos/{job_id}", headers=auth_headers)
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["id"] == job_id
    assert status_data["prompt"] == "flying over mountains"
    assert status_data["status"] == "QUEUED"


@patch("app.services.video_service.VideoService.trigger_generation")
def test_list_video_jobs(mock_trigger, client, auth_headers):
    # Create two jobs
    client.post("/v1/videos", json={"prompt": "prompt 1", "duration": 5, "seed": 1}, headers=auth_headers)
    client.post("/v1/videos", json={"prompt": "prompt 2", "duration": 10, "seed": 2}, headers=auth_headers)

    response = client.get("/v1/videos", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2


@patch("app.services.video_service.VideoService.trigger_generation")
def test_delete_video_job(mock_trigger, client, auth_headers):
    create_resp = client.post("/v1/videos", json={"prompt": "to delete", "duration": 5, "seed": 1}, headers=auth_headers)
    job_id = create_resp.json()["job_id"]

    # Delete job
    del_resp = client.delete(f"/v1/videos/{job_id}", headers=auth_headers)
    assert del_resp.status_code == 204

    # Verify deleted
    get_resp = client.get(f"/v1/videos/{job_id}", headers=auth_headers)
    assert get_resp.status_code == 404
