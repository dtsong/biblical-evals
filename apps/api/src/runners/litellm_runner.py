"""LiteLLM runner for calling LLM APIs and collecting responses."""

import asyncio
import logging
import os
import time
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.db.models import Response as ResponseModel
from src.loaders.config_loader import ModelConfig, PromptTemplate
from src.models.llm_metadata import GenerationParams, LLMResponseRawMetadata
from src.observability.context import reset_evaluation_id, set_evaluation_id

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 2.0


def _get_field(obj: Any, field: str) -> Any:
    """Best-effort get for both dict-like and attribute-like responses."""

    if isinstance(obj, dict):
        return obj.get(field)
    return getattr(obj, field, None)


async def call_model(
    model_config: ModelConfig,
    question_text: str,
    prompt_template: PromptTemplate,
) -> dict:
    """Call a single LLM model via LiteLLM.

    Returns a dict with response_text and metadata (tokens, cost, latency).
    Retries up to MAX_RETRIES times on transient failures.
    """
    # Canonical Google key is GOOGLE_AI_API_KEY, but some providers/libraries still
    # look for GOOGLE_API_KEY. Preserve compatibility at call time.
    if not os.getenv("GOOGLE_API_KEY") and os.getenv("GOOGLE_AI_API_KEY"):
        os.environ["GOOGLE_API_KEY"] = os.environ["GOOGLE_AI_API_KEY"]

    import litellm

    rendered_prompt = prompt_template.template.replace("{question}", question_text)

    # For now these are fixed; later issues make these evaluation-configurable.
    temperature = 0.7
    max_tokens = 2048

    last_error: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            timestamp_request = datetime.now(UTC)
            start_time = time.time()
            response = await litellm.acompletion(
                model=model_config.litellm_model,
                messages=[{"role": "user", "content": rendered_prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            latency = time.time() - start_time
            timestamp_response = datetime.now(UTC)

            resp = cast(Any, response)
            response_text = resp.choices[0].message.content or ""
            usage = getattr(resp, "usage", None)

            generation_params = GenerationParams(
                temperature=temperature,
                max_tokens=max_tokens,
            )

            metadata = LLMResponseRawMetadata(
                model=model_config.litellm_model,
                provider=model_config.provider,
                model_version=_get_field(resp, "model"),
                system_fingerprint=_get_field(resp, "system_fingerprint"),
                provider_response_id=_get_field(resp, "id"),
                rendered_prompt=rendered_prompt,
                generation_params=generation_params,
                prompt_tokens=(usage.prompt_tokens if usage else None),
                completion_tokens=(usage.completion_tokens if usage else None),
                total_tokens=(usage.total_tokens if usage else None),
                latency_seconds=round(latency, 3),
                timestamp_request=timestamp_request,
                timestamp_response=timestamp_response,
            )

            # LiteLLM provides cost tracking
            if hasattr(resp, "_hidden_params"):
                cost = resp._hidden_params.get("response_cost")
                if cost is not None:
                    metadata.cost_usd = float(cost)

            logger.info(
                "Model responded",
                extra={
                    "model": model_config.name,
                    "provider": model_config.provider,
                    "latency_seconds": round(latency, 3),
                    "total_tokens": metadata.total_tokens,
                },
            )
            return {
                "response_text": response_text,
                "metadata": metadata.model_dump(mode="json"),
                "prompt_tokens": metadata.prompt_tokens,
                "completion_tokens": metadata.completion_tokens,
                "cost_usd": metadata.cost_usd,
                "latency_seconds": metadata.latency_seconds,
            }

        except Exception as e:
            last_error = e
            logger.warning(
                "Model attempt failed",
                extra={
                    "model": model_config.name,
                    "provider": model_config.provider,
                    "attempt": attempt,
                    "max_retries": MAX_RETRIES,
                    "error": str(e),
                },
            )
            if attempt < MAX_RETRIES:
                import asyncio

                await asyncio.sleep(RETRY_DELAY_SECONDS * attempt)

    logger.error(
        "Model failed after retries",
        extra={
            "model": model_config.name,
            "provider": model_config.provider,
            "max_retries": MAX_RETRIES,
            "error": str(last_error) if last_error else None,
        },
    )
    raise RuntimeError(
        f"Model {model_config.name} failed after {MAX_RETRIES} attempts: {last_error}"
    )


async def _find_cached_response(
    db: AsyncSession,
    *,
    question_id: str,
    model_name: str,
    prompt_template_id: str,
) -> ResponseModel | None:
    settings = get_settings()
    cutoff = datetime.now(UTC) - timedelta(days=settings.response_cache_ttl_days)

    result = await db.execute(
        select(ResponseModel)
        .where(
            ResponseModel.question_id == question_id,
            ResponseModel.model_name == model_name,
            ResponseModel.prompt_template_id == prompt_template_id,
            ResponseModel.created_at >= cutoff,
        )
        .order_by(ResponseModel.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def run_evaluation(
    db: AsyncSession,
    evaluation_id: UUID,
    question_ids: list[str],
    question_texts: dict[str, str],
    model_configs: list[ModelConfig],
    prompt_template: PromptTemplate,
    *,
    use_cache: bool = True,
) -> list[ResponseModel]:
    """Run all models against all questions for an evaluation.

    Returns list of created Response records.
    """
    tok = set_evaluation_id(str(evaluation_id))
    responses: list[ResponseModel] = []
    total = len(question_ids) * len(model_configs)

    prompt_template_id = getattr(prompt_template, "id", "default")
    pending_calls: list[tuple[str, str, ModelConfig]] = []

    # First pass: apply cache lookups (DB-backed) and collect remaining calls.
    for question_id in question_ids:
        question_text = question_texts[question_id]
        for model_config in model_configs:
            if use_cache:
                cached = await _find_cached_response(
                    db,
                    question_id=question_id,
                    model_name=model_config.name,
                    prompt_template_id=prompt_template_id,
                )
                if cached is not None:
                    response = ResponseModel(
                        id=uuid4(),
                        evaluation_id=evaluation_id,
                        question_id=question_id,
                        model_name=model_config.name,
                        prompt_template_id=prompt_template_id,
                        cache_source_response_id=cached.id,
                        response_text=cached.response_text,
                        response_length_words=cached.response_length_words,
                        response_length_chars=cached.response_length_chars,
                        prompt_tokens=cached.prompt_tokens,
                        completion_tokens=cached.completion_tokens,
                        cost_usd=cached.cost_usd,
                        latency_seconds=cached.latency_seconds,
                        source="cache",
                        raw_metadata=cached.raw_metadata,
                    )
                    if (
                        response.response_length_words is None
                        or response.response_length_chars is None
                    ):
                        response.compute_response_length()
                    db.add(response)
                    responses.append(response)
                    continue

            pending_calls.append((question_id, question_text, model_config))

    # Second pass: run remaining calls concurrently with per-provider limits.
    provider_limits: dict[str, int] = {}
    for _qid, _qtext, mc in pending_calls:
        provider = getattr(mc, "provider", "default")
        limit = int(getattr(mc, "concurrency_limit", 5))
        provider_limits[provider] = min(provider_limits.get(provider, limit), limit)

    semaphores = {
        provider: asyncio.Semaphore(limit)
        for provider, limit in provider_limits.items()
    }

    async def _run_one(
        qid: str,
        qtext: str,
        mc: ModelConfig,
    ) -> tuple[str, ModelConfig, dict]:
        provider = getattr(mc, "provider", "default")
        sem = semaphores.get(provider)
        if sem is None:
            sem = asyncio.Semaphore(1)
            semaphores[provider] = sem

        async with sem:
            result = await call_model(mc, qtext, prompt_template)
            return (qid, mc, result)

    tasks = [
        asyncio.create_task(_run_one(qid, qtext, mc))
        for (qid, qtext, mc) in pending_calls
    ]

    for fut in asyncio.as_completed(tasks):
        try:
            question_id, model_config, result = await fut
        except Exception as e:
            logger.exception("Skipping model after retries", exc_info=e)
            continue

        response = ResponseModel(
            id=uuid4(),
            evaluation_id=evaluation_id,
            question_id=question_id,
            model_name=model_config.name,
            prompt_template_id=prompt_template_id,
            response_text=result["response_text"],
            prompt_tokens=result.get("prompt_tokens"),
            completion_tokens=result.get("completion_tokens"),
            cost_usd=result.get("cost_usd"),
            latency_seconds=result.get("latency_seconds"),
            source="api",
            raw_metadata=result["metadata"],
        )
        response.compute_response_length()
        db.add(response)
        responses.append(response)

    # Single commit for all rows keeps behavior predictable and fast,
    # and matches unit-test expectations around transaction boundaries.
    await db.commit()
    for r in responses:
        await db.refresh(r)

    reset_evaluation_id(tok)

    logger.info(
        "Evaluation responses collected",
        extra={
            "evaluation_id": str(evaluation_id),
            "responses_collected": len(responses),
            "total": total,
        },
    )
    return responses
