def test_register_user_success(client):
    payload = {"email": "user@example.com", "password": "securepassword"}
    response = client.post("/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "user@example.com"
    assert "id" in data


def test_register_duplicate_email(client):
    payload = {"email": "user@example.com", "password": "securepassword"}
    response = client.post("/v1/auth/register", json=payload)
    assert response.status_code == 201

    # Try duplicate
    response2 = client.post("/v1/auth/register", json=payload)
    assert response2.status_code == 400
    assert "already exists" in response2.json()["detail"]


def test_login_success(client):
    payload = {"email": "user@example.com", "password": "securepassword"}
    client.post("/v1/auth/register", json=payload)

    response = client.post("/v1/auth/token", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_invalid_credentials(client):
    payload = {"email": "user@example.com", "password": "securepassword"}
    client.post("/v1/auth/register", json=payload)

    # Wrong password
    response = client.post(
        "/v1/auth/token",
        json={"email": "user@example.com", "password": "wrongpassword"},
    )
    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]
