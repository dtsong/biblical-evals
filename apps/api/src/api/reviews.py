"""Review/scoring API endpoints."""

from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.database import get_db
from src.db.models import Response as ResponseModel
from src.db.models import Score as ScoreModel
from src.dependencies.auth import CurrentUser
from src.models.score import ReviewSubmission, ScoreResponse

router = APIRouter(prefix="/api/v1/reviews", tags=["reviews"])


@router.post(
    "",
    response_model=list[ScoreResponse],
    status_code=status.HTTP_201_CREATED,
)
async def submit_review(
    body: ReviewSubmission,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[ScoreModel]:
    """Submit scores for a response."""
    # Verify response exists
    result = await db.execute(
        select(ResponseModel).where(ResponseModel.id == body.response_id)
    )
    response = result.scalar_one_or_none()
    if not response:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Response not found",
        )

    scores = []
    for score_input in body.scores:
        # Require comment for low scores
        if score_input.value <= 3 and not score_input.comment:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Comment required for scores <= 3 "
                    f"(dimension: {score_input.dimension})"
                ),
            )

        score = ScoreModel(
            id=uuid4(),
            response_id=body.response_id,
            user_id=user.id,
            dimension=score_input.dimension,
            value=score_input.value,
            comment=score_input.comment,
        )
        db.add(score)
        scores.append(score)

    await db.commit()
    for s in scores:
        await db.refresh(s)

    return scores
