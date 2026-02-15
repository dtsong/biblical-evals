"""Focused unit tests for API endpoint handlers without real DB."""

from types import SimpleNamespace
from typing import Any, cast
from uuid import uuid4

import pytest
from fastapi import BackgroundTasks, HTTPException

from src.api import config_routes, evaluations, reports, responses, reviews
from src.config import get_settings
from src.runners.import_runner import ImportBatch, ImportedResponse
from tests.conftest import FakeAsyncSession, FakeExecuteResult


@pytest.mark.asyncio
async def test_create_evaluation_sets_fields():
    user = SimpleNamespace(id=uuid4())
    body = SimpleNamespace(
        name="Test Eval",
        perspective="multi_perspective",
        scoring_dimensions=["accuracy"],
        model_list=["gpt-4o"],
        prompt_template="default",
        use_cache=True,
        review_mode="blind",
    )
    db: Any = FakeAsyncSession()

    created = await evaluations.create_evaluation(cast(Any, body), cast(Any, user), db)

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
            uuid4(),
            cast(Any, SimpleNamespace()),
            cast(Any, FakeAsyncSession()),
            BackgroundTasks(),
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
            uuid4(),
            cast(Any, SimpleNamespace()),
            cast(Any, FakeAsyncSession()),
            BackgroundTasks(),
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
            uuid4(),
            cast(Any, body),
            cast(Any, SimpleNamespace()),
            cast(Any, FakeAsyncSession()),
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
    db: Any = FakeAsyncSession(execute_results=[FakeExecuteResult(many=[])])

    payload = await evaluations.get_next_unscored(
        uuid4(), cast(Any, SimpleNamespace(id=uuid4())), db
    )
    assert payload["complete"] is True


def test_deterministic_review_seed_varies_by_user(monkeypatch: pytest.MonkeyPatch):
    get_settings.cache_clear()
    monkeypatch.setenv("NEXTAUTH_SECRET", "test-secret")
    get_settings.cache_clear()

    evaluation_id = str(uuid4())
    question_id = "Q1"
    user_a = str(uuid4())
    user_b = str(uuid4())

    seed_a = evaluations._deterministic_shuffle_key(evaluation_id, question_id, user_a)
    seed_b = evaluations._deterministic_shuffle_key(evaluation_id, question_id, user_b)
    assert seed_a != seed_b


@pytest.mark.asyncio
async def test_get_next_unscored_blind_order_is_deterministic(
    monkeypatch: pytest.MonkeyPatch,
):
    get_settings.cache_clear()
    monkeypatch.setenv("NEXTAUTH_SECRET", "test-secret")
    get_settings.cache_clear()

    eval_obj = SimpleNamespace(review_mode="blind")

    async def fake_get_eval(_db, _eid):
        return eval_obj

    monkeypatch.setattr(evaluations, "get_evaluation", fake_get_eval)

    qid = "Q1"
    r1 = SimpleNamespace(
        id=uuid4(), question_id=qid, model_name="m1", response_text="a"
    )
    r2 = SimpleNamespace(
        id=uuid4(), question_id=qid, model_name="m2", response_text="b"
    )
    r3 = SimpleNamespace(
        id=uuid4(), question_id=qid, model_name="m3", response_text="c"
    )

    db: Any = FakeAsyncSession(
        execute_results=[FakeExecuteResult(many=[r1, r2, r3])],
        get_by_id={qid: SimpleNamespace(text="Question")},
    )
    user = SimpleNamespace(id=uuid4())
    eid = uuid4()

    first = await evaluations.get_next_unscored(eid, cast(Any, user), db)

    db2: Any = FakeAsyncSession(
        execute_results=[FakeExecuteResult(many=[r1, r2, r3])],
        get_by_id={qid: SimpleNamespace(text="Question")},
    )
    second = await evaluations.get_next_unscored(eid, cast(Any, user), db2)

    assert [r["response_id"] for r in first["responses"]] == [
        r["response_id"] for r in second["responses"]
    ]
    assert [r["presentation_order"] for r in first["responses"]] == [1, 2, 3]


@pytest.mark.asyncio
async def test_submit_review_requires_comment_for_low_scores():
    response_id = uuid4()
    eval_id = uuid4()
    user = SimpleNamespace(id=uuid4())
    body = SimpleNamespace(
        response_id=response_id,
        presentation_order=1,
        scores=[SimpleNamespace(dimension="accuracy", value=2, comment="")],
    )
    db: Any = FakeAsyncSession(
        execute_results=[
            FakeExecuteResult(
                one=SimpleNamespace(id=response_id, evaluation_id=eval_id)
            ),
            FakeExecuteResult(one=SimpleNamespace(id=eval_id, status="scoring")),
        ]
    )

    with pytest.raises(HTTPException) as exc:
        await reviews.submit_review(cast(Any, body), cast(Any, user), db)
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_submit_review_rejects_when_evaluation_completed():
    """Scoring is locked when evaluation status is 'completed'."""
    response_id = uuid4()
    eval_id = uuid4()
    user = SimpleNamespace(id=uuid4())
    body = SimpleNamespace(
        response_id=response_id,
        presentation_order=1,
        scores=[SimpleNamespace(dimension="accuracy", value=4, comment="good")],
    )
    db: Any = FakeAsyncSession(
        execute_results=[
            FakeExecuteResult(
                one=SimpleNamespace(id=response_id, evaluation_id=eval_id)
            ),
            FakeExecuteResult(one=SimpleNamespace(id=eval_id, status="completed")),
        ]
    )

    with pytest.raises(HTTPException) as exc:
        await reviews.submit_review(cast(Any, body), cast(Any, user), db)
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_submit_review_upserts_existing_score():
    """Submitting a score for an already-scored dimension updates the existing score."""
    response_id = uuid4()
    eval_id = uuid4()
    user_id = uuid4()
    user = SimpleNamespace(id=user_id)
    existing_score = SimpleNamespace(
        id=uuid4(),
        response_id=response_id,
        user_id=user_id,
        dimension="accuracy",
        value=3,
        comment="ok",
        scored_at=None,
    )
    body = SimpleNamespace(
        response_id=response_id,
        presentation_order=1,
        scores=[SimpleNamespace(dimension="accuracy", value=5, comment="revised")],
    )
    db: Any = FakeAsyncSession(
        execute_results=[
            FakeExecuteResult(
                one=SimpleNamespace(id=response_id, evaluation_id=eval_id)
            ),
            FakeExecuteResult(one=SimpleNamespace(id=eval_id, status="scoring")),
            # Upsert check: existing score found
            FakeExecuteResult(one=existing_score),
        ]
    )

    saved = await reviews.submit_review(cast(Any, body), cast(Any, user), db)
    assert len(saved) == 1
    assert existing_score.value == 5
    assert existing_score.comment == "revised"
    # No new objects added (updated existing)
    assert len(db.added) == 0


@pytest.mark.asyncio
async def test_report_generate_returns_markdown(monkeypatch: pytest.MonkeyPatch):
    async def fake_get_eval(_db, _eid):
        return SimpleNamespace(id=uuid4())

    async def fake_markdown(_db, _eid):
        return "# Report"

    monkeypatch.setattr(reports, "get_evaluation", fake_get_eval)
    monkeypatch.setattr(reports, "generate_markdown_report", fake_markdown)

    out = cast(
        Any,
        await reports.generate_report(
            uuid4(),
            cast(Any, SimpleNamespace()),
            cast(Any, FakeAsyncSession()),
            format="markdown",
        ),
    )
    assert out.body.decode() == "# Report"


@pytest.mark.asyncio
async def test_responses_endpoint_raises_404(monkeypatch: pytest.MonkeyPatch):
    async def fake_get_eval(_db, _eid):
        return None

    monkeypatch.setattr(responses, "get_evaluation", fake_get_eval)

    with pytest.raises(HTTPException) as exc:
        await responses.list_responses(
            uuid4(), cast(Any, SimpleNamespace()), cast(Any, FakeAsyncSession())
        )
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

    perspectives_payload = await config_routes.get_perspectives(
        cast(Any, SimpleNamespace())
    )
    dimensions_payload = await config_routes.get_dimensions(
        cast(Any, SimpleNamespace())
    )
    assert perspectives_payload == {"perspectives": [{"id": "orthodox"}]}
    assert dimensions_payload == {"dimensions": [{"name": "accuracy"}]}
