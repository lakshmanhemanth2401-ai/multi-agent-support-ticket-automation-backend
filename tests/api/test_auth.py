from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.security import hash_password
from app.db.database import Base
from app.db.session import get_db
from app.main import app
from app.models.user import User, UserRole


@pytest.fixture
def auth_client(monkeypatch):
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    Base.metadata.create_all(engine)
    with sessions() as session:
        session.add_all(
            [
                User(
                    email="admin@example.com",
                    password_hash=hash_password("correct-horse-battery-staple"),
                    role=UserRole.ADMINISTRATOR.value,
                    is_active=True,
                    created_at=datetime.now(timezone.utc),
                ),
                User(
                    email="agent@example.com",
                    password_hash=hash_password("another-secure-password"),
                    role=UserRole.SUPPORT_AGENT.value,
                    is_active=True,
                    created_at=datetime.now(timezone.utc),
                ),
            ]
        )
        session.commit()

    def override_db():
        with sessions() as session:
            yield session

    monkeypatch.setattr(
        settings, "jwt_secret", SecretStr("test-secret-with-at-least-32-characters")
    )
    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
    engine.dispose()


def _login(
    client: TestClient,
    email: str = "admin@example.com",
    password: str = "correct-horse-battery-staple",
):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})


def test_login_current_user_refresh_and_logout(auth_client: TestClient) -> None:
    login = _login(auth_client)
    assert login.status_code == 200
    tokens = login.json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    current = auth_client.get("/api/v1/auth/me", headers=headers)
    assert current.status_code == 200
    assert current.json()["role"] == "administrator"

    refreshed = auth_client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert refreshed.status_code == 200
    rotated = refreshed.json()
    assert rotated["refresh_token"] != tokens["refresh_token"]

    replay = auth_client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert replay.status_code == 401

    logout = auth_client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": rotated["refresh_token"]},
        headers={"Authorization": f"Bearer {rotated['access_token']}"},
    )
    assert logout.status_code == 204
    assert (
        auth_client.post(
            "/api/v1/auth/refresh", json={"refresh_token": rotated["refresh_token"]}
        ).status_code
        == 401
    )


def test_invalid_login_and_missing_token_return_consistent_401(auth_client: TestClient) -> None:
    invalid = _login(auth_client, password="incorrect-password")
    protected = auth_client.get("/api/v1/tickets")

    assert invalid.status_code == 401
    assert protected.status_code == 401
    assert invalid.json()["error"]["code"] == "authentication_required"
    assert protected.headers["WWW-Authenticate"] == "Bearer"


def test_role_mismatch_returns_403(auth_client: TestClient) -> None:
    tokens = _login(
        auth_client, email="agent@example.com", password="another-secure-password"
    ).json()
    response = auth_client.get(
        "/metrics", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "permission_denied"
