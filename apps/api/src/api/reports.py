"""Reports API endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import HTMLResponse, PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.database import get_db
from src.db.repository import get_evaluation
from src.dependencies.auth import CurrentUser
from src.reporting.generator import (
    generate_html_report,
    generate_markdown_report,
    generate_report_data,
)

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


@router.get("/{evaluation_id}")
async def get_report(
    evaluation_id: UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Get report data as JSON for the frontend chart viewer."""
    evaluation = await get_evaluation(db, evaluation_id)
    if not evaluation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evaluation not found",
        )

    return await generate_report_data(db, evaluation_id)


@router.post("/{evaluation_id}/generate", response_model=None)
async def generate_report(
    evaluation_id: UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    format: str = Query(default="json", pattern="^(json|html|markdown)$"),
):
    """Generate a report in the specified format."""
    evaluation = await get_evaluation(db, evaluation_id)
    if not evaluation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evaluation not found",
        )

    if format == "html":
        html = await generate_html_report(db, evaluation_id)
        return HTMLResponse(content=html)
    elif format == "markdown":
        md = await generate_markdown_report(db, evaluation_id)
        return PlainTextResponse(content=md)
    else:
        return await generate_report_data(db, evaluation_id)
