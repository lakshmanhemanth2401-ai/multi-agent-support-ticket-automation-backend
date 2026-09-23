import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings, settings
from app.main import create_app


def test_cors_rejects_wildcard_and_invalid_schemes() -> None:
    with pytest.raises(ValidationError):
        Settings(cors_allowed_origins=["*"], _env_file=None)
    with pytest.raises(ValidationError):
        Settings(cors_allowed_origins=["file://local"], _env_file=None)


def test_cors_only_allows_configured_origin(monkeypatch) -> None:
    monkeypatch.setattr(settings, "cors_allowed_origins", ["https://support.example.com"])
    with TestClient(create_app()) as client:
        allowed = client.options(
            "/api/v1/tickets",
            headers={
                "Origin": "https://support.example.com",
                "Access-Control-Request-Method": "POST",
            },
        )
        denied = client.options(
            "/api/v1/tickets",
            headers={
                "Origin": "https://evil.example.com",
                "Access-Control-Request-Method": "POST",
            },
        )

    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "https://support.example.com"
    assert denied.status_code == 400
    assert "access-control-allow-origin" not in denied.headers
