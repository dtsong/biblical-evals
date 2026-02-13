"""Report generation from aggregated scores."""

import logging
from pathlib import Path
from uuid import UUID

from jinja2 import Environment, FileSystemLoader
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.repository import get_evaluation
from src.scoring.aggregator import aggregate_scores
from src.scoring.engine import identify_strengths_weaknesses, rank_models

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent / "templates"


def _get_jinja_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=False,  # noqa: S701 — reports are server-rendered, not user input
    )


async def generate_report_data(
    db: AsyncSession,
    evaluation_id: UUID,
) -> dict:
    """Generate full report data for an evaluation."""
    evaluation = await get_evaluation(db, evaluation_id)
    if not evaluation:
        raise ValueError(f"Evaluation {evaluation_id} not found")

    report = await aggregate_scores(db, evaluation_id)
    rankings = rank_models(report)
    strengths = identify_strengths_weaknesses(report)

    return {
        "evaluation": {
            "id": str(evaluation.id),
            "name": evaluation.name,
            "perspective": evaluation.perspective,
            "review_mode": evaluation.review_mode,
            "model_list": evaluation.model_list,
        },
        "rankings": rankings,
        "strengths_weaknesses": strengths,
        **report.to_dict(),
    }


async def generate_markdown_report(
    db: AsyncSession,
    evaluation_id: UUID,
) -> str:
    """Generate a Markdown report for an evaluation."""
    data = await generate_report_data(db, evaluation_id)
    env = _get_jinja_env()
    template = env.get_template("report.md.j2")
    return template.render(**data)


async def generate_html_report(
    db: AsyncSession,
    evaluation_id: UUID,
) -> str:
    """Generate an HTML report for an evaluation."""
    data = await generate_report_data(db, evaluation_id)
    env = _get_jinja_env()
    template = env.get_template("report.html.j2")
    return template.render(**data)
