"""Tests for runner retry behavior and loader helpers."""

import asyncio
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

import pytest

from src.loaders import config_loader, question_loader
from src.runners import litellm_runner
from src.runners.import_runner import ImportBatch, ImportedResponse, import_responses
from tests.conftest import (
    FakeAsyncSession,
    FakeExecuteResult,
    FakeLiteLLMChoice,
    FakeLiteLLMMessage,
    FakeLiteLLMResponse,
    FakeLiteLLMUsage,
    LiteLLMStub,
)


def test_load_all_questions_missing_dir(tmp_path: Path):
    missing = tmp_path / "does-not-exist"
    questions = question_loader.load_all_questions(missing)
    assert questions == []


def test_load_app_config_with_partial_files(tmp_path: Path):
    (tmp_path / "models.yaml").write_text(
        "models:\n"
        "  - name: gpt-4o\n"
        "    provider: openai\n"
        "    litellm_model: openai/gpt-4o\n"
        "    api_key_env: OPENAI_API_KEY\n"
        "    tier: standard\n"
        "    cost_per_1k_input: 0.0025\n"
        "    cost_per_1k_output: 0.01\n"
    )
    cfg = config_loader.load_app_config(tmp_path)
    assert len(cfg.models) == 1
    assert cfg.models[0].tier == "standard"
    assert cfg.perspectives == []
    assert cfg.dimensions == []
    assert cfg.templates == []


@pytest.mark.asyncio
async def test_import_responses_creates_rows():
    db: Any = FakeAsyncSession()
    batch = ImportBatch(
        responses=[
            ImportedResponse(
                question_id="SOT-001",
                model_name="gpt-4o",
                response_text="answer",
            )
        ]
    )

    responses = await import_responses(db, uuid4(), batch)
    assert len(responses) == 1
    assert db.commits == 1
    assert len(db.refreshed) == 1


@pytest.mark.asyncio
async def test_import_responses_computes_length():
    db: Any = FakeAsyncSession()
    batch = ImportBatch(
        responses=[
            ImportedResponse(
                question_id="SOT-001",
                model_name="gpt-4o",
                response_text="The quick brown fox jumps over the lazy dog",
            )
        ]
    )

    responses = await import_responses(db, uuid4(), batch)
    resp = responses[0]
    assert resp.response_length_words == 9
    assert resp.response_length_chars == 43


@pytest.mark.asyncio
async def test_call_model_success_with_metadata(mock_litellm_acompletion: LiteLLMStub):
    response = FakeLiteLLMResponse(
        choices=[FakeLiteLLMChoice(message=FakeLiteLLMMessage(content="result"))],
        usage=FakeLiteLLMUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30),
        _hidden_params={"response_cost": 0.01},
    )
    mock_litellm_acompletion.set_response("openai/gpt-4o", response)

    model_config = type(
        "ModelCfg",
        (),
        {"name": "gpt-4o", "provider": "openai", "litellm_model": "openai/gpt-4o"},
    )()
    template = type("Tpl", (), {"template": "Q: {question}"})()

    result = await litellm_runner.call_model(
        cast(Any, model_config),
        "What is grace?",
        cast(Any, template),
    )
    assert result["response_text"] == "result"
    assert result["metadata"]["total_tokens"] == 30
    assert result["metadata"]["cost_usd"] == 0.01
    assert result["metadata"]["rendered_prompt"] == "Q: What is grace?"
    assert result["metadata"]["generation_params"]["temperature"] == 0.7
    assert result["metadata"]["generation_params"]["max_tokens"] == 2048


@pytest.mark.asyncio
async def test_call_model_retries_and_fails(
    monkeypatch: pytest.MonkeyPatch,
    mock_litellm_failing: LiteLLMStub,
):
    import asyncio

    async def fake_sleep(_seconds: float) -> None:
        return None

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    mock_litellm_failing.set_response("openai/gpt-4o", RuntimeError("boom"))

    model_config = type(
        "ModelCfg",
        (),
        {"name": "gpt-4o", "provider": "openai", "litellm_model": "openai/gpt-4o"},
    )()
    template = type("Tpl", (), {"template": "Q: {question}"})()

    with pytest.raises(RuntimeError, match="failed after"):
        await litellm_runner.call_model(
            cast(Any, model_config),
            "What is grace?",
            cast(Any, template),
        )

    assert len(mock_litellm_failing.calls) == litellm_runner.MAX_RETRIES


@pytest.mark.asyncio
async def test_run_evaluation_collects_successful_calls(
    monkeypatch: pytest.MonkeyPatch,
):
    async def fake_call_model(_cfg, _question_text, _template):
        return {"response_text": "ok", "metadata": {"total_tokens": 12}}

    monkeypatch.setattr(litellm_runner, "call_model", fake_call_model)

    db: Any = FakeAsyncSession()
    results = await litellm_runner.run_evaluation(
        db=db,
        evaluation_id=uuid4(),
        question_ids=["Q1", "Q2"],
        question_texts={"Q1": "text 1", "Q2": "text 2"},
        model_configs=cast(
            Any,
            [
                type("MC", (), {"name": "m1"})(),
                type("MC", (), {"name": "m2"})(),
            ],
        ),
        prompt_template=cast(Any, type("Tpl", (), {"template": "Q: {question}"})()),
    )

    assert len(results) == 4
    assert db.commits == 1
    assert len(db.refreshed) == 4


@pytest.mark.asyncio
async def test_run_evaluation_uses_cached_response_when_available(
    monkeypatch: pytest.MonkeyPatch,
):
    called = {"count": 0}

    async def fake_call_model(*_args, **_kwargs):
        called["count"] += 1
        return {"response_text": "fresh", "metadata": {"total_tokens": 12}}

    monkeypatch.setattr(litellm_runner, "call_model", fake_call_model)

    cached = type(
        "Cached",
        (),
        {
            "id": uuid4(),
            "response_text": "cached",
            "response_length_words": 1,
            "response_length_chars": 6,
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "cost_usd": 0.01,
            "latency_seconds": 0.2,
            "raw_metadata": {"total_tokens": 30},
        },
    )()

    db: Any = FakeAsyncSession(execute_results=[FakeExecuteResult(one=cached)])
    results = await litellm_runner.run_evaluation(
        db=db,
        evaluation_id=uuid4(),
        question_ids=["Q1"],
        question_texts={"Q1": "text"},
        model_configs=cast(Any, [type("MC", (), {"name": "m1"})()]),
        prompt_template=cast(
            Any,
            type("Tpl", (), {"id": "default", "template": "Q: {question}"})(),
        ),
        use_cache=True,
    )

    assert called["count"] == 0
    assert len(results) == 1
    assert results[0].source == "cache"
    assert results[0].cache_source_response_id == cached.id


@pytest.mark.asyncio
async def test_run_evaluation_calls_model_when_cache_misses(
    monkeypatch: pytest.MonkeyPatch,
):
    called = {"count": 0}

    async def fake_call_model(*_args, **_kwargs):
        called["count"] += 1
        return {"response_text": "fresh", "metadata": {"total_tokens": 12}}

    monkeypatch.setattr(litellm_runner, "call_model", fake_call_model)

    db: Any = FakeAsyncSession(execute_results=[FakeExecuteResult(one=None)])
    results = await litellm_runner.run_evaluation(
        db=db,
        evaluation_id=uuid4(),
        question_ids=["Q1"],
        question_texts={"Q1": "text"},
        model_configs=cast(Any, [type("MC", (), {"name": "m1"})()]),
        prompt_template=cast(
            Any,
            type("Tpl", (), {"id": "default", "template": "Q: {question}"})(),
        ),
        use_cache=True,
    )

    assert called["count"] == 1
    assert len(results) == 1
    assert results[0].source == "api"


@pytest.mark.asyncio
async def test_run_evaluation_enforces_per_provider_concurrency_limit(
    monkeypatch: pytest.MonkeyPatch,
):
    state = {"running": 0, "max_running": 0}
    lock = asyncio.Lock()

    async def fake_call_model(model_config: Any, _question_text: str, _template: Any):
        async with lock:
            state["running"] += 1
            state["max_running"] = max(state["max_running"], state["running"])
        await asyncio.sleep(0.01)
        async with lock:
            state["running"] -= 1
        return {"response_text": model_config.name, "metadata": {"total_tokens": 1}}

    monkeypatch.setattr(litellm_runner, "call_model", fake_call_model)

    db: Any = FakeAsyncSession(execute_results=[FakeExecuteResult(one=None)] * 2)
    results = await litellm_runner.run_evaluation(
        db=db,
        evaluation_id=uuid4(),
        question_ids=["Q1"],
        question_texts={"Q1": "text"},
        model_configs=cast(
            Any,
            [
                type(
                    "MC",
                    (),
                    {"name": "m1", "provider": "openai", "concurrency_limit": 1},
                )(),
                type(
                    "MC",
                    (),
                    {"name": "m2", "provider": "openai", "concurrency_limit": 1},
                )(),
            ],
        ),
        prompt_template=cast(
            Any,
            type("Tpl", (), {"id": "default", "template": "Q: {question}"})(),
        ),
        use_cache=True,
    )

    assert len(results) == 2
    assert state["max_running"] == 1
