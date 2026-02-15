"""Review/scoring API endpoints."""

from datetime import UTC, datetime
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.database import get_db
from src.db.models import Evaluation as EvaluationModel
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
    """Submit scores for a response (upsert semantics)."""
    # Verify response exists and load its evaluation
    result = await db.execute(
        select(ResponseModel).where(ResponseModel.id == body.response_id)
    )
    response = result.scalar_one_or_none()
    if not response:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Response not found",
        )

    # Check scoring lock: reject scores when evaluation is completed
    eval_result = await db.execute(
        select(EvaluationModel).where(EvaluationModel.id == response.evaluation_id)
    )
    evaluation = eval_result.scalar_one_or_none()
    if evaluation and evaluation.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Scoring is locked: evaluation has been completed",
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

        # Upsert: update existing score or create new one
        existing_result = await db.execute(
            select(ScoreModel).where(
                and_(
                    ScoreModel.response_id == body.response_id,
                    ScoreModel.user_id == user.id,
                    ScoreModel.dimension == score_input.dimension,
                )
            )
        )
        existing_score = existing_result.scalar_one_or_none()

        if existing_score:
            existing_score.value = score_input.value
            existing_score.comment = score_input.comment
            existing_score.presentation_order = body.presentation_order
            existing_score.scored_at = datetime.now(UTC)
            scores.append(existing_score)
        else:
            score = ScoreModel(
                id=uuid4(),
                response_id=body.response_id,
                user_id=user.id,
                dimension=score_input.dimension,
                value=score_input.value,
                comment=score_input.comment,
                presentation_order=body.presentation_order,
            )
            db.add(score)
            scores.append(score)

    await db.commit()
    for s in scores:
        await db.refresh(s)

    return scores
