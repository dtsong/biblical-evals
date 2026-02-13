"""Additional tests to improve API and dependency coverage."""

from contextlib import asynccontextmanager
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from src.api import evaluations, reports, reviews
from src.core.jwt import TokenVerificationError
from src.db import repository
from src.dependencies import auth
from src.main import lifespan


class FakeScalarResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class FakeExecuteResult:
    def __init__(self, one=None, many=None, scalar=None):
        self._one = one
        self._many = many or []
        self._scalar = scalar

    def scalar_one_or_none(self):
        return self._one

    def scalars(self):
        return FakeScalarResult(self._many)

    def scalar(self):
        return self._scalar


class FakeDb:
    def __init__(self, execute_results=None, commit_error=None):
        self.execute_results = list(execute_results or [])
        self.added = []
        self.commits = 0
        self.refreshed = []
        self.rollbacks = 0
        self.commit_error = commit_error

    async def execute(self, _query):
        if self.execute_results:
            return self.execute_results.pop(0)
        return FakeExecuteResult()

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        self.commits += 1
        if self.commit_error and self.commits == 1:
            raise self.commit_error

    async def refresh(self, obj):
        self.refreshed.append(obj)

    async def rollback(self):
        self.rollbacks += 1

    async def get(self, _model, _id):
        return None


@pytest.mark.asyncio
async def test_get_current_user_auth_header_validation():
    db = FakeDb()
    with pytest.raises(HTTPException) as exc_missing:
        await auth.get_current_user(SimpleNamespace(), db, None)
    assert exc_missing.value.status_code == 401

    with pytest.raises(HTTPException) as exc_bad:
        await auth.get_current_user(SimpleNamespace(), db, "Token abc")
    assert exc_bad.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_handles_verification_errors(
    monkeypatch: pytest.MonkeyPatch,
):
    db = FakeDb()

    def raise_infra(_token):
        raise TokenVerificationError("bad config")

    monkeypatch.setattr(auth, "verify_token", raise_infra)
    with pytest.raises(HTTPException) as exc:
        await auth.get_current_user(SimpleNamespace(), db, "Bearer abc")
    assert exc.value.status_code == 503

    monkeypatch.setattr(auth, "verify_token", lambda _token: None)
    with pytest.raises(HTTPException) as exc_invalid:
        await auth.get_current_user(SimpleNamespace(), db, "Bearer abc")
    assert exc_invalid.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_returns_existing_user(monkeypatch: pytest.MonkeyPatch):
    existing = SimpleNamespace(id=uuid4(), email="u@example.com")
    db = FakeDb(execute_results=[FakeExecuteResult(one=existing)])
    monkeypatch.setattr(
        auth,
        "verify_token",
        lambda _token: SimpleNamespace(sub="sub-1", email="u@example.com", name="U"),
    )

    user = await auth.get_current_user(SimpleNamespace(), db, "Bearer token")
    assert user is existing


@pytest.mark.asyncio
async def test_get_current_user_creates_user_when_missing(
    monkeypatch: pytest.MonkeyPatch,
):
    db = FakeDb(
        execute_results=[FakeExecuteResult(one=None), FakeExecuteResult(one=None)]
    )
    monkeypatch.setattr(
        auth,
        "verify_token",
        lambda _token: SimpleNamespace(
            sub="sub-1", email="new@example.com", name="New User"
        ),
    )

    user = await auth.get_current_user(SimpleNamespace(), db, "Bearer token")
    assert user.email == "new@example.com"
    assert db.commits == 1
    assert db.refreshed


@pytest.mark.asyncio
async def test_get_current_user_handles_integrity_error(
    monkeypatch: pytest.MonkeyPatch,
):
    existing = SimpleNamespace(id=uuid4(), email="existing@example.com")
    db = FakeDb(
        execute_results=[
            FakeExecuteResult(one=None),
            FakeExecuteResult(one=None),
            FakeExecuteResult(one=existing),
        ],
        commit_error=IntegrityError("x", "y", "z"),
    )
    monkeypatch.setattr(
        auth,
        "verify_token",
        lambda _token: SimpleNamespace(
            sub="sub-1", email="existing@example.com", name="User"
        ),
    )

    user = await auth.get_current_user(SimpleNamespace(), db, "Bearer token")
    assert user is existing
    assert db.rollbacks == 1


@pytest.mark.asyncio
async def test_get_current_user_optional(monkeypatch: pytest.MonkeyPatch):
    db = FakeDb()
    assert await auth.get_current_user_optional(SimpleNamespace(), db, None) is None

    async def fake_current(_req, _db, _auth):
        return "ok"

    monkeypatch.setattr(auth, "get_current_user", fake_current)
    assert (
        await auth.get_current_user_optional(SimpleNamespace(), db, "Bearer t") == "ok"
    )


@pytest.mark.asyncio
async def test_repository_functions():
    obj = SimpleNamespace(id=uuid4())
    many = [obj]
    db = FakeDb(
        execute_results=[
            FakeExecuteResult(one=obj),
            FakeExecuteResult(one=obj),
            FakeExecuteResult(many=many),
            FakeExecuteResult(one=obj),
            FakeExecuteResult(many=many),
            FakeExecuteResult(many=many),
            FakeExecuteResult(many=many),
        ]
    )

    assert await repository.get_user_by_auth_id(db, "id") is obj
    assert await repository.get_evaluation(db, uuid4()) is obj
    assert await repository.list_evaluations(db) == many
    assert await repository.get_question(db, "Q1") is obj
    assert await repository.list_questions(db) == many
    assert await repository.get_responses_for_evaluation(db, uuid4()) == many
    assert await repository.get_scores_for_response(db, uuid4()) == many


@pytest.mark.asyncio
async def test_reports_get_and_generate_branches(monkeypatch: pytest.MonkeyPatch):
    async def fake_get_eval(_db, _eid):
        return SimpleNamespace(id=uuid4())

    async def fake_report_data(_db, _eid):
        return {"ok": True}

    async def fake_html(_db, _eid):
        return "<h1>ok</h1>"

    async def fake_markdown(_db, _eid):
        return "# ok"

    monkeypatch.setattr(reports, "get_evaluation", fake_get_eval)
    monkeypatch.setattr(reports, "generate_report_data", fake_report_data)
    monkeypatch.setattr(reports, "generate_html_report", fake_html)
    monkeypatch.setattr(reports, "generate_markdown_report", fake_markdown)

    got = await reports.get_report(uuid4(), SimpleNamespace(), FakeDb())
    assert got == {"ok": True}

    html = await reports.generate_report(
        uuid4(), SimpleNamespace(), FakeDb(), format="html"
    )
    assert html.body.decode() == "<h1>ok</h1>"

    json_payload = await reports.generate_report(
        uuid4(), SimpleNamespace(), FakeDb(), format="json"
    )
    assert json_payload == {"ok": True}


@pytest.mark.asyncio
async def test_reviews_submit_review_success_path():
    response_id = uuid4()
    body = SimpleNamespace(
        response_id=response_id,
        scores=[SimpleNamespace(dimension="accuracy", value=4, comment="good")],
    )
    user = SimpleNamespace(id=uuid4())
    db = FakeDb(
        execute_results=[FakeExecuteResult(one=SimpleNamespace(id=response_id))]
    )

    saved = await reviews.submit_review(body, user, db)
    assert len(saved) == 1
    assert db.commits == 1
    assert len(db.refreshed) == 1


@pytest.mark.asyncio
async def test_get_evaluation_detail_and_progress(monkeypatch: pytest.MonkeyPatch):
    evaluation_obj = SimpleNamespace(id=uuid4())

    async def fake_get_eval(_db, _eid):
        return evaluation_obj

    monkeypatch.setattr(evaluations, "get_evaluation", fake_get_eval)

    detail = await evaluations.get_evaluation_detail(
        uuid4(), SimpleNamespace(), FakeDb()
    )
    assert detail is evaluation_obj

    db = FakeDb(
        execute_results=[
            FakeExecuteResult(scalar=20),
            FakeExecuteResult(scalar=5),
            FakeExecuteResult(scalar=2),
            FakeExecuteResult(scalar=3),
            FakeExecuteResult(scalar=7),
        ]
    )
    out = await evaluations.get_review_progress(
        uuid4(), SimpleNamespace(id=uuid4()), db
    )
    assert out["total_responses"] == 20
    assert out["scored_by_you"] == 5
    assert out["remaining_for_you"] == 15


@pytest.mark.asyncio
async def test_get_evaluation_detail_not_found(monkeypatch: pytest.MonkeyPatch):
    async def fake_get_eval(_db, _eid):
        return None

    monkeypatch.setattr(evaluations, "get_evaluation", fake_get_eval)
    with pytest.raises(HTTPException) as exc:
        await evaluations.get_evaluation_detail(uuid4(), SimpleNamespace(), FakeDb())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_lifespan_logs_with_and_without_secret(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("src.main.settings", SimpleNamespace(nextauth_secret="abc"))
    async with lifespan(SimpleNamespace()):
        pass

    monkeypatch.setattr("src.main.settings", SimpleNamespace(nextauth_secret=None))
    async with lifespan(SimpleNamespace()):
        pass


@pytest.mark.asyncio
async def test_run_evaluation_task_returns_when_model_missing(
    monkeypatch: pytest.MonkeyPatch,
):
    eval_obj = SimpleNamespace(status="running")

    class Session(FakeDb):
        async def get(self, model, _id):
            if getattr(model, "__name__", "") == "Evaluation":
                return eval_obj
            return None

    @asynccontextmanager
    async def fake_session_factory():
        yield Session()

    monkeypatch.setattr(
        evaluations, "load_app_config", lambda: SimpleNamespace(models=[], templates=[])
    )
    monkeypatch.setattr(evaluations, "load_all_questions", lambda: [])
    monkeypatch.setattr("src.db.database.async_session_factory", fake_session_factory)

    await evaluations._run_evaluation_task(uuid4(), ["m1"], "default")
    assert eval_obj.status == "running"
