"""Pydantic schemas for scores and reviews."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ScoreDimension(BaseModel):
    """A single scoring dimension configuration."""

    name: str
    label: str
    description: str
    category: str = "quality"  # "quality" or "perspective"
    min_value: int = 1
    max_value: int = 5


class Score(BaseModel):
    """A single dimension score for a response."""

    dimension: str
    value: int = Field(ge=1, le=5)
    comment: str = ""


class ReviewSubmission(BaseModel):
    """Submit scores for a response."""

    response_id: UUID
    presentation_order: int = Field(ge=1)
    scores: list[Score]


class ScoreResponse(BaseModel):
    """Response schema for a stored score."""

    id: UUID
    response_id: UUID
    user_id: UUID
    dimension: str
    value: int
    comment: str
    presentation_order: int | None = None
    scored_at: datetime

    model_config = {"from_attributes": True}
