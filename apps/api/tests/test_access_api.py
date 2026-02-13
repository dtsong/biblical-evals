"""Tests for access request and approval workflows."""

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, cast
from uuid import uuid4

import pytest
from fastapi import HTTPException

from src.api import access
from src.dependencies import auth
from tests.conftest import FakeAsyncSession, FakeExecuteResult


@pytest.mark.asyncio
async def test_get_current_user_blocks_pending(monkeypatch: pytest.MonkeyPatch):
    user = SimpleNamespace(id=uuid4(), role="reviewer", access_status="pending")

    async def fake_auth(_request, _db, _authorization):
        return user

    monkeypatch.setattr(auth, "get_authenticated_user", fake_auth)

    with pytest.raises(HTTPException) as exc:
        await auth.get_current_user(
            cast(Any, SimpleNamespace()),
            cast(Any, FakeAsyncSession()),
            "Bearer x",
        )
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_get_current_user_allows_approved(monkeypatch: pytest.MonkeyPatch):
    user = SimpleNamespace(id=uuid4(), role="reviewer", access_status="approved")

    async def fake_auth(_request, _db, _authorization):
        return user

    monkeypatch.setattr(auth, "get_authenticated_user", fake_auth)
    out = await auth.get_current_user(
        cast(Any, SimpleNamespace()),
        cast(Any, FakeAsyncSession()),
        "Bearer x",
    )
    assert out is user


@pytest.mark.asyncio
async def test_request_access_sets_pending():
    db: Any = FakeAsyncSession()
    user = SimpleNamespace(
        id=uuid4(),
        role="reviewer",
        access_status="not_requested",
        access_requested_at=None,
        access_reviewed_at=datetime.now(UTC),
        access_reviewed_by=uuid4(),
    )

    out = await access.request_access(cast(Any, user), db)
    assert out["access_status"] == "pending"
    assert user.access_status == "pending"
    assert user.access_requested_at is not None
    assert user.access_reviewed_at is None
    assert user.access_reviewed_by is None
    assert db.commits == 1


@pytest.mark.asyncio
async def test_request_access_noop_when_approved():
    db: Any = FakeAsyncSession()
    user = SimpleNamespace(id=uuid4(), role="reviewer", access_status="approved")
    out = await access.request_access(cast(Any, user), db)
    assert out["message"] == "Already approved"
    assert db.commits == 0


@pytest.mark.asyncio
async def test_list_access_requests_filters_non_admin_users():
    db: Any = FakeAsyncSession(
        execute_results=[
            FakeExecuteResult(
                many=[
                    SimpleNamespace(
                        id=uuid4(),
                        email="u@example.com",
                        display_name="U",
                        role="reviewer",
                        access_status="pending",
                        access_requested_at=None,
                        access_reviewed_at=None,
                        access_reviewed_by=None,
                    )
                ]
            )
        ]
    )
    admin = SimpleNamespace(id=uuid4(), role="admin")
    out = await access.list_access_requests(cast(Any, admin), db, "pending")
    assert out["requested_by"] == str(admin.id)
    assert len(out["users"]) == 1


@pytest.mark.asyncio
async def test_approve_and_reject_access():
    user_id = uuid4()
    user = SimpleNamespace(
        id=user_id,
        email="u@example.com",
        display_name="U",
        role="reviewer",
        access_status="pending",
        access_requested_at=None,
        access_reviewed_at=None,
        access_reviewed_by=None,
    )
    db: Any = FakeAsyncSession(get_by_id={user_id: user})
    admin = SimpleNamespace(id=uuid4(), role="admin")

    approved = await access.approve_access_request(user_id, cast(Any, admin), db)
    assert approved["user"]["access_status"] == "approved"

    rejected = await access.reject_access_request(user_id, cast(Any, admin), db)
    assert rejected["user"]["access_status"] == "rejected"


@pytest.mark.asyncio
async def test_admin_user_dependency_requires_admin(monkeypatch: pytest.MonkeyPatch):
    user = SimpleNamespace(id=uuid4(), role="reviewer", access_status="approved")

    async def fake_auth(_request, _db, _authorization):
        return user

    monkeypatch.setattr(auth, "get_authenticated_user", fake_auth)
    with pytest.raises(HTTPException) as exc:
        await auth.get_admin_user(
            cast(Any, SimpleNamespace()),
            cast(Any, FakeAsyncSession()),
            "Bearer x",
        )
    assert exc.value.status_code == 403
