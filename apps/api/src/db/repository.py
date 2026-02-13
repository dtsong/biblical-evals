"""Database repository for common query patterns."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Evaluation, Question, Response, Score, User


async def get_user_by_auth_id(db: AsyncSession, auth_provider_id: str) -> User | None:
    """Find a user by their auth provider ID."""
    result = await db.execute(
        select(User).where(User.auth_provider_id == auth_provider_id)
    )
    return result.scalar_one_or_none()


async def get_evaluation(db: AsyncSession, evaluation_id: UUID) -> Evaluation | None:
    """Get an evaluation by ID."""
    result = await db.execute(select(Evaluation).where(Evaluation.id == evaluation_id))
    return result.scalar_one_or_none()


async def list_evaluations(db: AsyncSession) -> list[Evaluation]:
    """List all evaluations ordered by creation date."""
    result = await db.execute(select(Evaluation).order_by(Evaluation.created_at.desc()))
    return list(result.scalars().all())


async def get_question(db: AsyncSession, question_id: str) -> Question | None:
    """Get a question by ID."""
    result = await db.execute(select(Question).where(Question.id == question_id))
    return result.scalar_one_or_none()


async def list_questions(db: AsyncSession) -> list[Question]:
    """List all questions."""
    result = await db.execute(select(Question).order_by(Question.id))
    return list(result.scalars().all())


async def get_responses_for_evaluation(
    db: AsyncSession, evaluation_id: UUID
) -> list[Response]:
    """Get all responses for an evaluation."""
    result = await db.execute(
        select(Response)
        .where(Response.evaluation_id == evaluation_id)
        .order_by(Response.question_id, Response.model_name)
    )
    return list(result.scalars().all())


async def get_scores_for_response(db: AsyncSession, response_id: UUID) -> list[Score]:
    """Get all scores for a response."""
    result = await db.execute(
        select(Score).where(Score.response_id == response_id).order_by(Score.dimension)
    )
    return list(result.scalars().all())
