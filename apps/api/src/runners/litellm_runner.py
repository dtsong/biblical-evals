"""LiteLLM runner for calling LLM APIs and collecting responses."""

import logging
import time
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Response as ResponseModel
from src.loaders.config_loader import ModelConfig, PromptTemplate

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 2.0


async def call_model(
    model_config: ModelConfig,
    question_text: str,
    prompt_template: PromptTemplate,
) -> dict:
    """Call a single LLM model via LiteLLM.

    Returns a dict with response_text and metadata (tokens, cost, latency).
    Retries up to MAX_RETRIES times on transient failures.
    """
    import litellm

    prompt = prompt_template.template.replace("{question}", question_text)

    last_error: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            start_time = time.time()
            response = await litellm.acompletion(
                model=model_config.litellm_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=2048,
            )
            latency = time.time() - start_time

            response_text = response.choices[0].message.content or ""
            usage = response.usage

            metadata = {
                "model": model_config.litellm_model,
                "provider": model_config.provider,
                "prompt_tokens": usage.prompt_tokens if usage else None,
                "completion_tokens": (usage.completion_tokens if usage else None),
                "total_tokens": usage.total_tokens if usage else None,
                "latency_seconds": round(latency, 3),
            }

            # LiteLLM provides cost tracking
            if hasattr(response, "_hidden_params"):
                cost = response._hidden_params.get("response_cost")
                if cost is not None:
                    metadata["cost_usd"] = cost

            logger.info(
                "Model %s responded in %.2fs (%s tokens)",
                model_config.name,
                latency,
                metadata.get("total_tokens", "?"),
            )
            return {
                "response_text": response_text,
                "metadata": metadata,
            }

        except Exception as e:
            last_error = e
            logger.warning(
                "Model %s attempt %d/%d failed: %s",
                model_config.name,
                attempt,
                MAX_RETRIES,
                e,
            )
            if attempt < MAX_RETRIES:
                import asyncio

                await asyncio.sleep(RETRY_DELAY_SECONDS * attempt)

    logger.error(
        "Model %s failed after %d attempts: %s",
        model_config.name,
        MAX_RETRIES,
        last_error,
    )
    raise RuntimeError(
        f"Model {model_config.name} failed after {MAX_RETRIES} attempts: {last_error}"
    )


async def run_evaluation(
    db: AsyncSession,
    evaluation_id: UUID,
    question_ids: list[str],
    question_texts: dict[str, str],
    model_configs: list[ModelConfig],
    prompt_template: PromptTemplate,
) -> list[ResponseModel]:
    """Run all models against all questions for an evaluation.

    Returns list of created Response records.
    """
    responses: list[ResponseModel] = []
    total = len(question_ids) * len(model_configs)
    completed = 0

    for question_id in question_ids:
        question_text = question_texts[question_id]
        for model_config in model_configs:
            completed += 1
            logger.info(
                "Running %d/%d: %s on %s",
                completed,
                total,
                model_config.name,
                question_id,
            )

            try:
                result = await call_model(model_config, question_text, prompt_template)
                response = ResponseModel(
                    id=uuid4(),
                    evaluation_id=evaluation_id,
                    question_id=question_id,
                    model_name=model_config.name,
                    response_text=result["response_text"],
                    source="api",
                    raw_metadata=result["metadata"],
                )
                db.add(response)
                responses.append(response)

            except RuntimeError:
                logger.exception(
                    "Skipping %s for %s after all retries failed",
                    model_config.name,
                    question_id,
                )

    await db.commit()
    for r in responses:
        await db.refresh(r)

    logger.info(
        "Evaluation %s: collected %d/%d responses",
        evaluation_id,
        len(responses),
        total,
    )
    return responses
