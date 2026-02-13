"""Tests for request context middleware and logging injection."""

from __future__ import annotations

import logging

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app


@pytest.mark.asyncio
async def test_request_context_injects_trace_and_request_id(
    caplog: pytest.LogCaptureFixture,
):
    caplog.set_level(logging.INFO)

    trace = "105445aa7843bc8bf206b120001000"
    header_val = f"{trace}/1;o=1"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.get(
            "/api/v1/health", headers={"X-Cloud-Trace-Context": header_val}
        )

    records = [
        r
        for r in caplog.records
        if r.name == "src.observability.middleware"
        and r.getMessage() == "request completed"
    ]
    assert records, "Expected request completed log record"

    rec = records[-1]
    assert getattr(rec, "trace_id", None) == trace
    assert getattr(rec, "request_id", None) == trace


@pytest.mark.asyncio
async def test_request_context_does_not_leak_between_requests(
    caplog: pytest.LogCaptureFixture,
):
    caplog.set_level(logging.INFO)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.get(
            "/api/v1/health",
            headers={"X-Cloud-Trace-Context": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa/1;o=1"},
        )
        await client.get("/api/v1/health")

    records = [
        r
        for r in caplog.records
        if r.name == "src.observability.middleware"
        and r.getMessage() == "request completed"
    ]
    assert len(records) >= 2

    first, second = records[-2], records[-1]
    assert getattr(first, "trace_id", None) == "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    # Second request has no trace header; ensure previous trace id not reused.
    assert getattr(second, "trace_id", None) in (None, "")
