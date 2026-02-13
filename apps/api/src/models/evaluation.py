"""Pydantic schemas for evaluations."""

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field


class EvaluationStatus(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    COLLECTING = "collecting"
    REVIEWING = "reviewing"
    COMPLETE = "complete"


class ReviewMode(StrEnum):
    BLIND = "blind"
    LABELED = "labeled"


class EvaluationCreate(BaseModel):
    """Request schema for creating an evaluation run."""

    name: str = Field(min_length=1, max_length=255)
    perspective: str = Field(default="multi_perspective")
    scoring_dimensions: list[str] = Field(default_factory=list)
    model_list: list[str] = Field(min_length=1)
    prompt_template: str = Field(default="default")
    review_mode: ReviewMode = ReviewMode.BLIND


class EvaluationResponse(BaseModel):
    """Response schema for an evaluation run."""

    id: UUID
    name: str
    status: EvaluationStatus
    perspective: str
    scoring_dimensions: list[str]
    model_list: list[str]
    prompt_template: str
    review_mode: ReviewMode
    created_by: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
