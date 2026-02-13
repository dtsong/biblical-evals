"""Scoring engine utilities."""

from src.scoring.aggregator import AggregatedReport


def identify_strengths_weaknesses(
    report: AggregatedReport,
) -> dict[str, dict[str, list[str]]]:
    """Identify each model's strongest and weakest dimensions."""
    results: dict[str, dict[str, list[str]]] = {}

    for model, dims in report.model_averages.items():
        if not dims:
            continue
        sorted_dims = sorted(dims.items(), key=lambda x: x[1])
        results[model] = {
            "strengths": [d for d, _ in sorted_dims[-2:]],
            "weaknesses": [d for d, _ in sorted_dims[:2]],
        }

    return results


def rank_models(report: AggregatedReport) -> list[dict]:
    """Rank models by overall average score."""
    ranked = sorted(
        report.model_overall.items(),
        key=lambda x: x[1],
        reverse=True,
    )
    return [
        {"rank": i + 1, "model": model, "overall_score": score}
        for i, (model, score) in enumerate(ranked)
    ]
