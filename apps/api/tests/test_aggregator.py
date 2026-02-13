"""Tests for score aggregation calculations."""

from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest

from src.scoring.aggregator import aggregate_scores
from tests.conftest import FakeAsyncSession, FakeExecuteResult


@pytest.mark.asyncio
async def test_aggregate_scores_computes_averages():
    rid1 = uuid4()
    rid2 = uuid4()
    uid1 = uuid4()
    uid2 = uuid4()

    responses = [
        SimpleNamespace(
            id=rid1, evaluation_id=uuid4(), model_name="m1", question_id="Q1"
        ),
        SimpleNamespace(
            id=rid2, evaluation_id=uuid4(), model_name="m2", question_id="Q1"
        ),
    ]
    scores = [
        SimpleNamespace(response_id=rid1, user_id=uid1, dimension="accuracy", value=5),
        SimpleNamespace(response_id=rid1, user_id=uid2, dimension="accuracy", value=3),
        SimpleNamespace(response_id=rid2, user_id=uid1, dimension="accuracy", value=4),
        SimpleNamespace(response_id=rid2, user_id=uid2, dimension="accuracy", value=2),
    ]

    db: Any = FakeAsyncSession(
        execute_results=[
            FakeExecuteResult(many=responses),
            FakeExecuteResult(many=scores),
        ]
    )
    report = await aggregate_scores(db, uuid4())

    assert report.total_responses == 2
    assert report.total_scores == 4
    assert report.reviewer_count == 2
    assert report.model_averages["m1"]["accuracy"] == 4.0
    assert report.model_averages["m2"]["accuracy"] == 3.0
    assert report.model_overall["m1"] == 4.0
    assert report.head_to_head["m1"]["m2"]["accuracy"] == 1.0


@pytest.mark.asyncio
async def test_aggregate_scores_handles_empty_input():
    db: Any = FakeAsyncSession(
        execute_results=[
            FakeExecuteResult(many=[]),
            FakeExecuteResult(many=[]),
        ]
    )
    report = await aggregate_scores(db, uuid4())
    assert report.total_responses == 0
    assert report.total_scores == 0
    assert report.model_averages == {}
