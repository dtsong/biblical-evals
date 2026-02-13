"""Evaluation API endpoints."""

import logging
import random
from typing import Annotated, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.database import get_db
from src.db.models import Evaluation, Question, Score
from src.db.models import Response as ResponseModel
from src.db.repository import get_evaluation, list_evaluations
from src.dependencies.auth import CurrentUser
from src.loaders.config_loader import load_app_config
from src.loaders.question_loader import load_all_questions
from src.models.evaluation import EvaluationCreate, EvaluationResponse
from src.observability.context import reset_evaluation_id, set_evaluation_id
from src.runners.import_runner import ImportBatch, import_responses

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/evaluations", tags=["evaluations"])


@router.post(
    "",
    response_model=EvaluationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_evaluation(
    body: EvaluationCreate,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Evaluation:
    """Create a new evaluation run."""
    evaluation = Evaluation(
        id=uuid4(),
        name=body.name,
        status="created",
        perspective=body.perspective,
        scoring_dimensions=body.scoring_dimensions,
        model_list=body.model_list,
        prompt_template=body.prompt_template,
        review_mode=body.review_mode,
        created_by=user.id,
    )
    db.add(evaluation)
    await db.commit()
    await db.refresh(evaluation)
    return evaluation


@router.get("", response_model=list[EvaluationResponse])
async def list_all_evaluations(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[Evaluation]:
    """List all evaluation runs."""
    return await list_evaluations(db)


@router.get("/{evaluation_id}", response_model=EvaluationResponse)
async def get_evaluation_detail(
    evaluation_id: UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Evaluation:
    """Get details for a specific evaluation."""
    evaluation = await get_evaluation(db, evaluation_id)
    if not evaluation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evaluation not found",
        )
    return evaluation


async def _run_evaluation_task(
    evaluation_id: UUID,
    model_names: list[str],
    prompt_template_id: str,
) -> None:
    """Background task to run LLM evaluation."""
    from src.db.database import async_session_factory
    from src.runners.litellm_runner import run_evaluation

    config = load_app_config()
    questions = load_all_questions()

    # Find matching model configs
    model_configs = [m for m in config.models if m.name in model_names]
    if not model_configs:
        logger.error(
            "No matching model configs",
            extra={"model_names": model_names},
        )
        return

    # Find prompt template
    template = next(
        (t for t in config.templates if t.id == prompt_template_id),
        None,
    )
    if not template:
        logger.error(
            "Prompt template not found",
            extra={"prompt_template_id": prompt_template_id},
        )
        return

    question_ids = [q.id for q in questions]
    question_texts = {q.id: q.text for q in questions}

    async with async_session_factory() as db:
        tok = set_evaluation_id(str(evaluation_id))
        # Sync questions to database
        for q in questions:
            existing = await db.get(Question, q.id)
            if not existing:
                db.add(
                    Question(
                        id=q.id,
                        text=q.text,
                        type=q.type,
                        category=q.type,
                        difficulty=q.difficulty,
                        metadata_json={
                            "scripture_references": q.scripture_references,
                            "tags": q.tags,
                        },
                    )
                )
        await db.commit()

        # Update status to running
        eval_obj = await db.get(Evaluation, evaluation_id)
        if eval_obj:
            eval_obj.status = "running"
            await db.commit()

        try:
            await run_evaluation(
                db=db,
                evaluation_id=evaluation_id,
                question_ids=question_ids,
                question_texts=question_texts,
                model_configs=model_configs,
                prompt_template=template,
            )
            # Update status to reviewing
            eval_obj = await db.get(Evaluation, evaluation_id)
            if eval_obj:
                eval_obj.status = "reviewing"
                await db.commit()

        except Exception:
            logger.exception(
                "Evaluation failed",
                extra={"evaluation_id": str(evaluation_id)},
            )
            eval_obj = await db.get(Evaluation, evaluation_id)
            if eval_obj:
                eval_obj.status = "created"
                await db.commit()

        reset_evaluation_id(tok)


@router.post("/{evaluation_id}/run")
async def trigger_run(
    evaluation_id: UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    background_tasks: BackgroundTasks,
) -> dict:
    """Trigger response collection for an evaluation."""
    evaluation = await get_evaluation(db, evaluation_id)
    if not evaluation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evaluation not found",
        )

    if evaluation.status not in ("created", "collecting"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot run evaluation in '{evaluation.status}' status",
        )

    evaluation.status = "collecting"
    await db.commit()

    model_names_any: Any = evaluation.model_list
    model_names: list[str] = list(model_names_any) if model_names_any else []

    background_tasks.add_task(
        _run_evaluation_task,
        evaluation_id,
        model_names,
        evaluation.prompt_template,
    )

    return {
        "message": "Evaluation run started",
        "evaluation_id": str(evaluation_id),
    }


@router.post("/{evaluation_id}/import")
async def import_eval_responses(
    evaluation_id: UUID,
    body: ImportBatch,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Import pre-collected responses for an evaluation."""
    evaluation = await get_evaluation(db, evaluation_id)
    if not evaluation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evaluation not found",
        )

    # Sync referenced questions to database
    questions = load_all_questions()
    q_map = {q.id: q for q in questions}
    for item in body.responses:
        if item.question_id not in q_map:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unknown question_id: {item.question_id}",
            )
        existing = await db.get(Question, item.question_id)
        if not existing:
            q = q_map[item.question_id]
            db.add(
                Question(
                    id=q.id,
                    text=q.text,
                    type=q.type,
                    category=q.type,
                    difficulty=q.difficulty,
                    metadata_json={
                        "scripture_references": q.scripture_references,
                        "tags": q.tags,
                    },
                )
            )
    await db.commit()

    responses = await import_responses(db, evaluation_id, body)

    if evaluation.status == "created":
        evaluation.status = "reviewing"
        await db.commit()

    return {
        "message": f"Imported {len(responses)} responses",
        "count": len(responses),
    }


@router.get("/{evaluation_id}/review")
async def get_next_unscored(
    evaluation_id: UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Get the next unscored response for review.

    In blind mode, model names are hidden and response order is shuffled.
    """
    evaluation = await get_evaluation(db, evaluation_id)
    if not evaluation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evaluation not found",
        )

    # Find responses not yet scored by this user
    scored_subq = (
        select(Score.response_id).where(Score.user_id == user.id).distinct().subquery()
    )

    result = await db.execute(
        select(ResponseModel)
        .where(
            ResponseModel.evaluation_id == evaluation_id,
            ResponseModel.id.notin_(select(scored_subq)),
        )
        .order_by(ResponseModel.question_id, ResponseModel.model_name)
    )
    unscored = list(result.scalars().all())

    if not unscored:
        return {
            "complete": True,
            "message": "All responses have been scored",
        }

    # Group by question for side-by-side review
    question_id = unscored[0].question_id
    question_responses = [r for r in unscored if r.question_id == question_id]

    # In blind mode, shuffle and hide model names
    is_blind = evaluation.review_mode == "blind"
    if is_blind:
        random.shuffle(question_responses)

    labels = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    items = []
    for i, resp in enumerate(question_responses):
        item = {
            "response_id": str(resp.id),
            "label": f"Response {labels[i]}" if is_blind else resp.model_name,
            "response_text": resp.response_text,
            "question_id": resp.question_id,
        }
        if not is_blind:
            item["model_name"] = resp.model_name
        items.append(item)

    # Get question text
    question = await db.get(Question, question_id)

    return {
        "complete": False,
        "question": {
            "id": question_id,
            "text": question.text if question else "",
        },
        "responses": items,
        "review_mode": evaluation.review_mode,
    }


@router.get("/{evaluation_id}/progress")
async def get_review_progress(
    evaluation_id: UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Get review completion statistics for an evaluation."""
    evaluation = await get_evaluation(db, evaluation_id)
    if not evaluation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evaluation not found",
        )

    # Total responses
    total_result = await db.execute(
        select(func.count(ResponseModel.id)).where(
            ResponseModel.evaluation_id == evaluation_id
        )
    )
    total_responses = total_result.scalar() or 0

    # Responses scored by current user
    scored_result = await db.execute(
        select(func.count(func.distinct(Score.response_id))).where(
            Score.user_id == user.id,
            Score.response_id.in_(
                select(ResponseModel.id).where(
                    ResponseModel.evaluation_id == evaluation_id
                )
            ),
        )
    )
    scored_by_user = scored_result.scalar() or 0

    # Total unique scorers
    scorers_result = await db.execute(
        select(func.count(func.distinct(Score.user_id))).where(
            Score.response_id.in_(
                select(ResponseModel.id).where(
                    ResponseModel.evaluation_id == evaluation_id
                )
            ),
        )
    )
    total_reviewers = scorers_result.scalar() or 0

    # Unique models
    models_result = await db.execute(
        select(func.count(func.distinct(ResponseModel.model_name))).where(
            ResponseModel.evaluation_id == evaluation_id
        )
    )
    model_count = models_result.scalar() or 0

    # Unique questions with responses
    questions_result = await db.execute(
        select(func.count(func.distinct(ResponseModel.question_id))).where(
            ResponseModel.evaluation_id == evaluation_id
        )
    )
    question_count = questions_result.scalar() or 0

    return {
        "evaluation_id": str(evaluation_id),
        "total_responses": total_responses,
        "scored_by_you": scored_by_user,
        "remaining_for_you": total_responses - scored_by_user,
        "percent_complete": (
            round(scored_by_user / total_responses * 100, 1)
            if total_responses > 0
            else 0
        ),
        "total_reviewers": total_reviewers,
        "model_count": model_count,
        "question_count": question_count,
    }
