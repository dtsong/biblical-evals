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


@pytest.mark.asyncio
async def test_aggregate_scores_excludes_perspective_from_overall():
    """Perspective dimensions (e.g. denominational_alignment) must not
    contaminate model_overall or head_to_head comparisons."""
    rid1 = uuid4()
    rid2 = uuid4()
    uid = uuid4()

    responses = [
        SimpleNamespace(
            id=rid1, evaluation_id=uuid4(), model_name="m1", question_id="Q1"
        ),
        SimpleNamespace(
            id=rid2, evaluation_id=uuid4(), model_name="m2", question_id="Q1"
        ),
    ]
    scores = [
        # Quality dimension: both models score 4
        SimpleNamespace(
            response_id=rid1, user_id=uid, dimension="factual_accuracy", value=4
        ),
        SimpleNamespace(
            response_id=rid2, user_id=uid, dimension="factual_accuracy", value=4
        ),
        # Perspective dimension: m1 scores 1, m2 scores 5
        # Without fix, this would drag m1 overall down and boost m2
        SimpleNamespace(
            response_id=rid1,
            user_id=uid,
            dimension="denominational_alignment",
            value=1,
        ),
        SimpleNamespace(
            response_id=rid2,
            user_id=uid,
            dimension="denominational_alignment",
            value=5,
        ),
    ]

    db: Any = FakeAsyncSession(
        execute_results=[
            FakeExecuteResult(many=responses),
            FakeExecuteResult(many=scores),
        ]
    )
    report = await aggregate_scores(
        db, uuid4(), perspective_dimensions={"denominational_alignment"}
    )

    # Overall should be based ONLY on quality dimensions
    assert report.model_overall["m1"] == 4.0
    assert report.model_overall["m2"] == 4.0

    # Denominational alignment still appears in per-model averages
    assert report.model_averages["m1"]["denominational_alignment"] == 1.0
    assert report.model_averages["m2"]["denominational_alignment"] == 5.0

    # Perspective scores reported separately
    assert report.perspective_scores["denominational_alignment"]["m1"] == 1.0
    assert report.perspective_scores["denominational_alignment"]["m2"] == 5.0

    # Head-to-head excludes perspective dimensions
    assert "denominational_alignment" not in report.head_to_head["m1"]["m2"]
    assert report.head_to_head["m1"]["m2"]["factual_accuracy"] == 0.0

    # Dimension averages still include all dimensions for reference
    assert "denominational_alignment" in report.dimension_averages
    assert "factual_accuracy" in report.dimension_averages


@pytest.mark.asyncio
async def test_aggregate_scores_no_perspective_dims_preserves_behavior():
    """When no perspective_dimensions are passed, all dims included in overall
    (backward compatibility)."""
    rid = uuid4()
    uid = uuid4()

    responses = [
        SimpleNamespace(
            id=rid, evaluation_id=uuid4(), model_name="m1", question_id="Q1"
        ),
    ]
    scores = [
        SimpleNamespace(response_id=rid, user_id=uid, dimension="accuracy", value=4),
        SimpleNamespace(response_id=rid, user_id=uid, dimension="alignment", value=2),
    ]

    db: Any = FakeAsyncSession(
        execute_results=[
            FakeExecuteResult(many=responses),
            FakeExecuteResult(many=scores),
        ]
    )
    # No perspective_dimensions passed — all dims in overall
    report = await aggregate_scores(db, uuid4())
    assert report.model_overall["m1"] == 3.0  # (4+2)/2
    assert report.perspective_scores == {}
