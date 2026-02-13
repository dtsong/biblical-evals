"""Response API endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.database import get_db
from src.db.repository import get_evaluation, get_responses_for_evaluation
from src.dependencies.auth import CurrentUser
from src.models.response import LLMResponse

router = APIRouter(prefix="/api/v1/evaluations", tags=["responses"])


@router.get(
    "/{evaluation_id}/responses",
    response_model=list[LLMResponse],
)
async def list_responses(
    evaluation_id: UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list:
    """List all responses for an evaluation."""
    evaluation = await get_evaluation(db, evaluation_id)
    if not evaluation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evaluation not found",
        )
    return await get_responses_for_evaluation(db, evaluation_id)
