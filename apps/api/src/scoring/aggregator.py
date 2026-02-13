"""Score aggregation for evaluation reports."""

import logging
from collections import defaultdict
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Response as ResponseModel
from src.db.models import Score

logger = logging.getLogger(__name__)


class AggregatedReport:
    """Aggregated report data for an evaluation."""

    def __init__(self) -> None:
        self.model_averages: dict[str, dict[str, float]] = {}
        self.model_overall: dict[str, float] = {}
        self.dimension_averages: dict[str, dict[str, float]] = {}
        self.head_to_head: dict[str, dict[str, dict[str, float]]] = {}
        self.question_scores: dict[str, dict[str, dict[str, float]]] = {}
        self.total_responses: int = 0
        self.total_scores: int = 0
        self.reviewer_count: int = 0

    def to_dict(self) -> dict:
        return {
            "model_averages": self.model_averages,
            "model_overall": self.model_overall,
            "dimension_averages": self.dimension_averages,
            "head_to_head": self.head_to_head,
            "question_scores": self.question_scores,
            "total_responses": self.total_responses,
            "total_scores": self.total_scores,
            "reviewer_count": self.reviewer_count,
        }


async def aggregate_scores(
    db: AsyncSession,
    evaluation_id: UUID,
) -> AggregatedReport:
    """Aggregate all scores for an evaluation into report data."""
    report = AggregatedReport()

    # Fetch all responses with their scores
    responses_result = await db.execute(
        select(ResponseModel).where(
            ResponseModel.evaluation_id == evaluation_id
        )
    )
    responses = list(responses_result.scalars().all())
    report.total_responses = len(responses)

    if not responses:
        return report

    response_ids = [r.id for r in responses]
    response_map = {r.id: r for r in responses}

    # Fetch all scores for these responses
    scores_result = await db.execute(
        select(Score).where(Score.response_id.in_(response_ids))
    )
    scores = list(scores_result.scalars().all())
    report.total_scores = len(scores)

    if not scores:
        return report

    # Count unique reviewers
    reviewer_ids = {s.user_id for s in scores}
    report.reviewer_count = len(reviewer_ids)

    # Organize scores by model -> dimension -> values
    model_dim_scores: dict[str, dict[str, list[int]]] = defaultdict(
        lambda: defaultdict(list)
    )
    # Also by question -> model -> dimension -> values
    q_model_dim: dict[str, dict[str, dict[str, list[int]]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(list))
    )

    for score in scores:
        resp = response_map.get(score.response_id)
        if not resp:
            continue
        model_dim_scores[resp.model_name][score.dimension].append(
            score.value
        )
        q_model_dim[resp.question_id][resp.model_name][
            score.dimension
        ].append(score.value)

    # Per-model averages by dimension
    for model, dims in model_dim_scores.items():
        report.model_averages[model] = {}
        all_values: list[int] = []
        for dim, values in dims.items():
            avg = sum(values) / len(values)
            report.model_averages[model][dim] = round(avg, 2)
            all_values.extend(values)
        if all_values:
            report.model_overall[model] = round(
                sum(all_values) / len(all_values), 2
            )

    # Per-dimension averages by model
    all_dimensions = set()
    for dims in model_dim_scores.values():
        all_dimensions.update(dims.keys())

    for dim in all_dimensions:
        report.dimension_averages[dim] = {}
        for model, dims in model_dim_scores.items():
            if dim in dims:
                values = dims[dim]
                report.dimension_averages[dim][model] = round(
                    sum(values) / len(values), 2
                )

    # Head-to-head: for each pair of models, compare on each dimension
    models = list(model_dim_scores.keys())
    for i, model_a in enumerate(models):
        report.head_to_head[model_a] = {}
        for model_b in models[i + 1 :]:
            comparison: dict[str, float] = {}
            for dim in all_dimensions:
                a_vals = model_dim_scores[model_a].get(dim, [])
                b_vals = model_dim_scores[model_b].get(dim, [])
                if a_vals and b_vals:
                    a_avg = sum(a_vals) / len(a_vals)
                    b_avg = sum(b_vals) / len(b_vals)
                    comparison[dim] = round(a_avg - b_avg, 2)
            report.head_to_head[model_a][model_b] = comparison

    # Per-question scores
    for q_id, models_data in q_model_dim.items():
        report.question_scores[q_id] = {}
        for model, dims in models_data.items():
            report.question_scores[q_id][model] = {}
            for dim, values in dims.items():
                report.question_scores[q_id][model][dim] = round(
                    sum(values) / len(values), 2
                )

    return report
