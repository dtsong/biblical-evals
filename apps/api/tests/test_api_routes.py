"""Tests for API route registration and unauthenticated access."""

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app


@pytest.mark.asyncio
async def test_all_routes_registered():
    """Verify all expected routes are registered in the app."""
    routes = [route.path for route in app.routes]

    expected_prefixes = [
        "/api/v1/health",
        "/api/v1/questions",
        "/api/v1/evaluations",
        "/api/v1/reviews",
        "/api/v1/reports",
        "/api/v1/config",
    ]
    for prefix in expected_prefixes:
        assert any(r.startswith(prefix) for r in routes), (
            f"Missing route prefix: {prefix}"
        )


@pytest.mark.asyncio
async def test_protected_routes_require_auth():
    """Protected endpoints return 401 without auth."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        endpoints = [
            ("GET", "/api/v1/questions"),
            ("GET", "/api/v1/evaluations"),
            ("POST", "/api/v1/evaluations"),
            ("POST", "/api/v1/reviews"),
            ("GET", "/api/v1/config/perspectives"),
            ("GET", "/api/v1/config/dimensions"),
        ]
        for method, path in endpoints:
            if method == "GET":
                resp = await client.get(path)
            else:
                resp = await client.post(path, json={})
            assert resp.status_code == 401, (
                f"{method} {path} should require auth, got {resp.status_code}"
            )


@pytest.mark.asyncio
async def test_health_no_auth_required():
    """Health endpoint should not require authentication."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/health")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_openapi_docs_available_in_dev():
    """OpenAPI docs should be available in development."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/docs")
    if app.docs_url is None:
        assert resp.status_code == 404
    else:
        # In dev mode, should return 200 (HTML)
        assert resp.status_code == 200
