"""Tests for access request and approval workflows."""

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from src.api import access
from src.dependencies import auth


class FakeScalarResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class FakeExecuteResult:
    def __init__(self, many=None):
        self._many = many or []

    def scalars(self):
        return FakeScalarResult(self._many)


class FakeDb:
    def __init__(self, execute_rows=None):
        self.execute_rows = list(execute_rows or [])
        self.commits = 0
        self.refreshed = []
        self.by_id = {}

    async def execute(self, _query):
        rows = self.execute_rows.pop(0) if self.execute_rows else []
        return FakeExecuteResult(many=rows)

    async def commit(self):
        self.commits += 1

    async def refresh(self, obj):
        self.refreshed.append(obj)

    async def get(self, _model, _id):
        return self.by_id.get(_id)


@pytest.mark.asyncio
async def test_get_current_user_blocks_pending(monkeypatch: pytest.MonkeyPatch):
    user = SimpleNamespace(id=uuid4(), role="reviewer", access_status="pending")

    async def fake_auth(_request, _db, _authorization):
        return user

    monkeypatch.setattr(auth, "get_authenticated_user", fake_auth)

    with pytest.raises(HTTPException) as exc:
        await auth.get_current_user(SimpleNamespace(), FakeDb(), "Bearer x")
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_get_current_user_allows_approved(monkeypatch: pytest.MonkeyPatch):
    user = SimpleNamespace(id=uuid4(), role="reviewer", access_status="approved")

    async def fake_auth(_request, _db, _authorization):
        return user

    monkeypatch.setattr(auth, "get_authenticated_user", fake_auth)
    out = await auth.get_current_user(SimpleNamespace(), FakeDb(), "Bearer x")
    assert out is user


@pytest.mark.asyncio
async def test_request_access_sets_pending():
    db = FakeDb()
    user = SimpleNamespace(
        id=uuid4(),
        role="reviewer",
        access_status="not_requested",
        access_requested_at=None,
        access_reviewed_at=datetime.now(UTC),
        access_reviewed_by=uuid4(),
    )

    out = await access.request_access(user, db)
    assert out["access_status"] == "pending"
    assert user.access_status == "pending"
    assert user.access_requested_at is not None
    assert user.access_reviewed_at is None
    assert user.access_reviewed_by is None
    assert db.commits == 1


@pytest.mark.asyncio
async def test_request_access_noop_when_approved():
    db = FakeDb()
    user = SimpleNamespace(id=uuid4(), role="reviewer", access_status="approved")
    out = await access.request_access(user, db)
    assert out["message"] == "Already approved"
    assert db.commits == 0


@pytest.mark.asyncio
async def test_list_access_requests_filters_non_admin_users():
    db = FakeDb(
        execute_rows=[
            [
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
        ]
    )
    admin = SimpleNamespace(id=uuid4(), role="admin")
    out = await access.list_access_requests(admin, db, "pending")
    assert out["requested_by"] == str(admin.id)
    assert len(out["users"]) == 1


@pytest.mark.asyncio
async def test_approve_and_reject_access():
    db = FakeDb()
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
    db.by_id[user_id] = user
    admin = SimpleNamespace(id=uuid4(), role="admin")

    approved = await access.approve_access_request(user_id, admin, db)
    assert approved["user"]["access_status"] == "approved"

    rejected = await access.reject_access_request(user_id, admin, db)
    assert rejected["user"]["access_status"] == "rejected"


@pytest.mark.asyncio
async def test_admin_user_dependency_requires_admin(monkeypatch: pytest.MonkeyPatch):
    user = SimpleNamespace(id=uuid4(), role="reviewer", access_status="approved")

    async def fake_auth(_request, _db, _authorization):
        return user

    monkeypatch.setattr(auth, "get_authenticated_user", fake_auth)
    with pytest.raises(HTTPException) as exc:
        await auth.get_admin_user(SimpleNamespace(), FakeDb(), "Bearer x")
    assert exc.value.status_code == 403
