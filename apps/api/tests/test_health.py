"""Tests for the health endpoint."""

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

from src.db.database import get_db
from src.main import app
from tests.conftest import FakeAsyncSession, FakeExecuteResult


@pytest.mark.asyncio
async def test_health_check():
    """Health endpoint returns ok."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


@pytest.mark.asyncio
async def test_readiness_check_healthy(monkeypatch: pytest.MonkeyPatch):
    async def override_get_db() -> AsyncGenerator[FakeAsyncSession, None]:
        yield FakeAsyncSession(execute_results=[FakeExecuteResult(scalar=1)])

    monkeypatch.setenv("NEXTAUTH_SECRET", "secret")
    monkeypatch.setenv("OPENAI_API_KEY", "x")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "y")
    monkeypatch.setenv("GOOGLE_AI_API_KEY", "z")
    monkeypatch.setenv("COMMIT_SHA", "abc1234")

    monkeypatch.setattr(
        "src.api.health.load_app_config",
        lambda: type(
            "Cfg",
            (),
            {
                "models": [
                    type(
                        "M", (), {"provider": "openai", "api_key_env": "OPENAI_API_KEY"}
                    )(),
                    type(
                        "M",
                        (),
                        {"provider": "anthropic", "api_key_env": "ANTHROPIC_API_KEY"},
                    )(),
                    type(
                        "M",
                        (),
                        {"provider": "google", "api_key_env": "GOOGLE_AI_API_KEY"},
                    )(),
                ]
            },
        )(),
    )

    app.dependency_overrides[get_db] = override_get_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/health/ready")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["commit"] == "abc1234"
        assert data["checks"]["database"]["status"] == "ok"
        assert data["checks"]["auth"]["status"] == "ok"
        assert data["checks"]["llm_keys"]["status"] == "ok"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_readiness_check_degraded_when_missing_provider_key(
    monkeypatch: pytest.MonkeyPatch,
):
    async def override_get_db() -> AsyncGenerator[FakeAsyncSession, None]:
        yield FakeAsyncSession(execute_results=[FakeExecuteResult(scalar=1)])

    monkeypatch.setenv("NEXTAUTH_SECRET", "secret")
    monkeypatch.setenv("OPENAI_API_KEY", "x")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "y")
    monkeypatch.delenv("GOOGLE_AI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    monkeypatch.setattr(
        "src.api.health.load_app_config",
        lambda: type(
            "Cfg",
            (),
            {
                "models": [
                    type(
                        "M", (), {"provider": "openai", "api_key_env": "OPENAI_API_KEY"}
                    )(),
                    type(
                        "M",
                        (),
                        {"provider": "google", "api_key_env": "GOOGLE_AI_API_KEY"},
                    )(),
                ]
            },
        )(),
    )

    app.dependency_overrides[get_db] = override_get_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/health/ready")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["checks"]["llm_keys"]["status"] == "missing"
        assert "google" in data["checks"]["llm_keys"]["missing_providers"]
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_readiness_check_unhealthy_when_db_fails(
    monkeypatch: pytest.MonkeyPatch,
):
    async def override_get_db() -> AsyncGenerator[FakeAsyncSession, None]:
        yield FakeAsyncSession(execute_results=[RuntimeError("db down")])

    monkeypatch.setenv("NEXTAUTH_SECRET", "secret")
    monkeypatch.setenv("OPENAI_API_KEY", "x")

    monkeypatch.setattr(
        "src.api.health.load_app_config",
        lambda: type(
            "Cfg",
            (),
            {
                "models": [
                    type(
                        "M", (), {"provider": "openai", "api_key_env": "OPENAI_API_KEY"}
                    )()
                ]
            },
        )(),
    )

    app.dependency_overrides[get_db] = override_get_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/health/ready")

        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["checks"]["database"]["status"] == "error"
    finally:
        app.dependency_overrides.clear()
