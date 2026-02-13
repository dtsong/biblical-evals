"""Questions API endpoints."""

from fastapi import APIRouter

from src.dependencies.auth import CurrentUser
from src.loaders.question_loader import load_all_questions
from src.models.question import Question

router = APIRouter(prefix="/api/v1/questions", tags=["questions"])


@router.get("", response_model=list[Question])
async def list_questions(user: CurrentUser) -> list[Question]:
    """List all available questions from the question bank."""
    return load_all_questions()
