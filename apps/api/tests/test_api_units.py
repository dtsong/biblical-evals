"""Focused unit tests for API endpoint handlers without real DB."""

from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import BackgroundTasks, HTTPException

from src.api import config_routes, evaluations, reports, responses, reviews
from src.runners.import_runner import ImportBatch, ImportedResponse


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
    def __init__(self, execute_results=None):
        self.added = []
        self.commits = 0
        self.refreshed = []
        self.execute_results = list(execute_results or [])

    async def execute(self, _query):
        if self.execute_results:
            return self.execute_results.pop(0)
        return FakeExecuteResult()

    async def get(self, _model, _id):
        return None

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        self.commits += 1

    async def refresh(self, obj):
        self.refreshed.append(obj)


@pytest.mark.asyncio
async def test_create_evaluation_sets_fields():
    user = SimpleNamespace(id=uuid4())
    body = SimpleNamespace(
        name="Test Eval",
        perspective="multi_perspective",
        scoring_dimensions=["accuracy"],
        model_list=["gpt-4o"],
        prompt_template="default",
        review_mode="blind",
    )
    db = FakeDb()

    created = await evaluations.create_evaluation(body, user, db)

    assert created.name == "Test Eval"
    assert created.created_by == user.id
    assert created.status == "created"
    assert db.commits == 1
    assert len(db.added) == 1


@pytest.mark.asyncio
async def test_trigger_run_raises_404_when_missing(monkeypatch: pytest.MonkeyPatch):
    async def fake_get_eval(_db, _eid):
        return None

    monkeypatch.setattr(evaluations, "get_evaluation", fake_get_eval)

    with pytest.raises(HTTPException) as exc:
        await evaluations.trigger_run(
            uuid4(), SimpleNamespace(), FakeDb(), BackgroundTasks()
        )
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_trigger_run_raises_409_for_invalid_state(
    monkeypatch: pytest.MonkeyPatch,
):
    async def fake_get_eval(_db, _eid):
        return SimpleNamespace(
            status="reviewing", model_list=["m"], prompt_template="default"
        )

    monkeypatch.setattr(evaluations, "get_evaluation", fake_get_eval)

    with pytest.raises(HTTPException) as exc:
        await evaluations.trigger_run(
            uuid4(), SimpleNamespace(), FakeDb(), BackgroundTasks()
        )
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_import_eval_responses_raises_for_unknown_question(
    monkeypatch: pytest.MonkeyPatch,
):
    async def fake_get_eval(_db, _eid):
        return SimpleNamespace(status="created")

    monkeypatch.setattr(evaluations, "get_evaluation", fake_get_eval)
    monkeypatch.setattr(evaluations, "load_all_questions", lambda: [])

    body = ImportBatch(
        responses=[
            ImportedResponse(
                question_id="UNKNOWN",
                model_name="gpt-4o",
                response_text="text",
            )
        ]
    )

    with pytest.raises(HTTPException) as exc:
        await evaluations.import_eval_responses(
            uuid4(), body, SimpleNamespace(), FakeDb()
        )
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_get_next_unscored_returns_complete_when_none(
    monkeypatch: pytest.MonkeyPatch,
):
    eval_obj = SimpleNamespace(review_mode="blind")

    async def fake_get_eval(_db, _eid):
        return eval_obj

    monkeypatch.setattr(evaluations, "get_evaluation", fake_get_eval)
    db = FakeDb(execute_results=[FakeExecuteResult(many=[])])

    payload = await evaluations.get_next_unscored(
        uuid4(), SimpleNamespace(id=uuid4()), db
    )
    assert payload["complete"] is True


@pytest.mark.asyncio
async def test_submit_review_requires_comment_for_low_scores():
    response_id = uuid4()
    user = SimpleNamespace(id=uuid4())
    body = SimpleNamespace(
        response_id=response_id,
        scores=[SimpleNamespace(dimension="accuracy", value=2, comment="")],
    )
    db = FakeDb(
        execute_results=[FakeExecuteResult(one=SimpleNamespace(id=response_id))]
    )

    with pytest.raises(HTTPException) as exc:
        await reviews.submit_review(body, user, db)
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_report_generate_returns_markdown(monkeypatch: pytest.MonkeyPatch):
    async def fake_get_eval(_db, _eid):
        return SimpleNamespace(id=uuid4())

    async def fake_markdown(_db, _eid):
        return "# Report"

    monkeypatch.setattr(reports, "get_evaluation", fake_get_eval)
    monkeypatch.setattr(reports, "generate_markdown_report", fake_markdown)

    out = await reports.generate_report(
        uuid4(), SimpleNamespace(), FakeDb(), format="markdown"
    )
    assert out.body.decode() == "# Report"


@pytest.mark.asyncio
async def test_responses_endpoint_raises_404(monkeypatch: pytest.MonkeyPatch):
    async def fake_get_eval(_db, _eid):
        return None

    monkeypatch.setattr(responses, "get_evaluation", fake_get_eval)

    with pytest.raises(HTTPException) as exc:
        await responses.list_responses(uuid4(), SimpleNamespace(), FakeDb())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_config_routes_return_dumped_payload(monkeypatch: pytest.MonkeyPatch):
    perspective = SimpleNamespace(model_dump=lambda: {"id": "orthodox"})
    dimension = SimpleNamespace(model_dump=lambda: {"name": "accuracy"})
    monkeypatch.setattr(
        config_routes,
        "load_app_config",
        lambda: SimpleNamespace(perspectives=[perspective], dimensions=[dimension]),
    )

    perspectives_payload = await config_routes.get_perspectives(SimpleNamespace())
    dimensions_payload = await config_routes.get_dimensions(SimpleNamespace())
    assert perspectives_payload == {"perspectives": [{"id": "orthodox"}]}
    assert dimensions_payload == {"dimensions": [{"name": "accuracy"}]}
