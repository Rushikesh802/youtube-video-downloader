import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get("/healthz")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


@pytest.mark.asyncio
async def test_user_registration_and_login_flow(client: AsyncClient):
    # 1. Register a new user
    register_payload = {
        "email": "creator@example.com",
        "password": "SecurePassword123!",
    }
    register_res = await client.post("/api/v1/auth/register", json=register_payload)
    assert register_res.status_code == 201
    register_data = register_res.json()
    assert "access_token" in register_data
    assert register_data["token_type"] == "bearer"

    # 2. Attempt duplicate registration -> should return 409
    dup_res = await client.post("/api/v1/auth/register", json=register_payload)
    assert dup_res.status_code == 409

    # 3. Login with correct credentials
    login_payload = {
        "email": "creator@example.com",
        "password": "SecurePassword123!",
    }
    login_res = await client.post("/api/v1/auth/login", json=login_payload)
    assert login_res.status_code == 200
    token_data = login_res.json()
    token = token_data["access_token"]
    assert token

    # 4. Login with invalid password -> should return 401
    bad_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "creator@example.com", "password": "WrongPassword!"},
    )
    assert bad_login.status_code == 401

    # 5. Access protected /auth/me with valid Bearer token
    headers = {"Authorization": f"Bearer {token}"}
    me_res = await client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["email"] == "creator@example.com"
    assert me_data["role"] == "user"
    assert me_data["is_active"] is True
    assert "id" in me_data

    # 6. Also access /api/v1/users/me route
    users_me_res = await client.get("/api/v1/users/me", headers=headers)
    assert users_me_res.status_code == 200
    assert users_me_res.json()["email"] == "creator@example.com"


@pytest.mark.asyncio
async def test_protected_routes_without_auth(client: AsyncClient):
    # Missing token -> 401
    res1 = await client.get("/api/v1/auth/me")
    assert res1.status_code == 401

    # Invalid token -> 401
    res2 = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid.token.payload"},
    )
    assert res2.status_code == 401
