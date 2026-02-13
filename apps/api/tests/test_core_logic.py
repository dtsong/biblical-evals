"""Unit tests for config, JWT, scoring, and reporting logic."""

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.config import Settings
from src.core import jwt as jwt_module
from src.reporting import generator
from src.scoring.aggregator import AggregatedReport
from src.scoring.engine import identify_strengths_weaknesses, rank_models


def test_effective_database_url_injects_password():
    """DATABASE_PASSWORD is injected into database_url when username exists."""
    settings = Settings(
        database_url="postgresql+asyncpg://user@localhost:5432/appdb",
        database_password="secret123",
    )
    assert settings.effective_database_url == (
        "postgresql+asyncpg://user:secret123@localhost:5432/appdb"
    )


def test_effective_database_url_unchanged_without_password():
    settings = Settings(
        database_url="postgresql+asyncpg://user@localhost:5432/appdb",
        database_password=None,
    )
    assert (
        settings.effective_database_url
        == "postgresql+asyncpg://user@localhost:5432/appdb"
    )


def test_environment_flags():
    dev = Settings(environment="development")
    prod = Settings(environment="production")
    assert dev.is_development is True
    assert dev.is_production is False
    assert prod.is_development is False
    assert prod.is_production is True


def test_verify_token_returns_none_on_invalid_token(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        jwt_module,
        "get_settings",
        lambda: SimpleNamespace(nextauth_secret="abc123"),
    )
    assert jwt_module.verify_token("definitely-not-a-jwt") is None


def test_verify_token_requires_sub_claim(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        jwt_module,
        "get_settings",
        lambda: SimpleNamespace(nextauth_secret="abc123"),
    )
    monkeypatch.setattr(
        jwt_module.jwt, "decode", lambda *_args, **_kwargs: {"email": "a@b.com"}
    )
    assert jwt_module.verify_token("token") is None


def test_verify_token_success(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        jwt_module,
        "get_settings",
        lambda: SimpleNamespace(nextauth_secret="abc123"),
    )
    monkeypatch.setattr(
        jwt_module.jwt,
        "decode",
        lambda *_args, **_kwargs: {
            "sub": "auth-id-1",
            "email": "u@example.com",
            "name": "User",
            "picture": "https://example.com/pic.png",
        },
    )
    decoded = jwt_module.verify_token("token")
    assert decoded is not None
    assert decoded.sub == "auth-id-1"
    assert decoded.email == "u@example.com"


def test_verify_token_raises_when_secret_missing(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        jwt_module,
        "get_settings",
        lambda: SimpleNamespace(nextauth_secret=None),
    )
    with pytest.raises(jwt_module.TokenVerificationError):
        jwt_module.verify_token("token")


def test_rank_models_and_strengths_weaknesses():
    report = AggregatedReport()
    report.model_averages = {
        "model-a": {"accuracy": 4.5, "clarity": 3.8, "charity": 4.2},
        "model-b": {"accuracy": 3.9, "clarity": 4.3, "charity": 3.4},
    }
    report.model_overall = {"model-a": 4.17, "model-b": 3.87}

    rankings = rank_models(report)
    assert rankings[0]["model"] == "model-a"
    assert rankings[0]["rank"] == 1

    sw = identify_strengths_weaknesses(report)
    assert sw["model-a"]["strengths"] == ["charity", "accuracy"]
    assert sw["model-a"]["weaknesses"] == ["clarity", "charity"]


@pytest.mark.asyncio
async def test_generate_report_data_raises_for_missing_evaluation(
    monkeypatch: pytest.MonkeyPatch,
):
    async def fake_get_eval(_db, _evaluation_id):
        return None

    monkeypatch.setattr(generator, "get_evaluation", fake_get_eval)

    with pytest.raises(ValueError, match="not found"):
        await generator.generate_report_data(SimpleNamespace(), uuid4())


@pytest.mark.asyncio
async def test_generate_report_data_returns_expected_shape(
    monkeypatch: pytest.MonkeyPatch,
):
    eval_id = uuid4()
    fake_eval = SimpleNamespace(
        id=eval_id,
        name="Eval",
        perspective="multi_perspective",
        review_mode="blind",
        model_list=["m1", "m2"],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    async def fake_get_eval(_db, _evaluation_id):
        return fake_eval

    async def fake_aggregate(_db, _evaluation_id):
        report = AggregatedReport()
        report.model_averages = {"m1": {"accuracy": 4.2}}
        report.model_overall = {"m1": 4.2}
        report.total_responses = 2
        report.total_scores = 4
        report.reviewer_count = 1
        return report

    monkeypatch.setattr(generator, "get_evaluation", fake_get_eval)
    monkeypatch.setattr(generator, "aggregate_scores", fake_aggregate)

    data = await generator.generate_report_data(SimpleNamespace(), eval_id)
    assert data["evaluation"]["id"] == str(eval_id)
    assert data["rankings"][0]["model"] == "m1"
    assert data["total_responses"] == 2
    assert "strengths_weaknesses" in data
