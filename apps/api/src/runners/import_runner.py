"""Import runner for pre-collected LLM responses."""

import logging
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Response as ResponseModel

logger = logging.getLogger(__name__)


class ImportedResponse(BaseModel):
    """Schema for a single imported response."""

    question_id: str
    model_name: str
    response_text: str
    metadata: dict = Field(default_factory=dict)


class ImportBatch(BaseModel):
    """Schema for a batch import request."""

    responses: list[ImportedResponse]


async def import_responses(
    db: AsyncSession,
    evaluation_id: UUID,
    batch: ImportBatch,
) -> list[ResponseModel]:
    """Import pre-collected responses into an evaluation.

    Returns list of created Response records.
    """
    responses: list[ResponseModel] = []

    for item in batch.responses:
        response = ResponseModel(
            id=uuid4(),
            evaluation_id=evaluation_id,
            question_id=item.question_id,
            model_name=item.model_name,
            response_text=item.response_text,
            source="import",
            raw_metadata=item.metadata,
        )
        db.add(response)
        responses.append(response)

    await db.commit()
    for r in responses:
        await db.refresh(r)

    logger.info(
        "Imported %d responses for evaluation %s",
        len(responses),
        evaluation_id,
    )
    return responses
