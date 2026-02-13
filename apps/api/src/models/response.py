"""Pydantic schemas for LLM responses."""

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field


class ResponseSource(StrEnum):
    API = "api"
    IMPORT = "import"


class LLMResponseCreate(BaseModel):
    """Schema for creating/importing a response."""

    question_id: str
    model_name: str
    response_text: str
    source: ResponseSource = ResponseSource.API
    raw_metadata: dict = Field(default_factory=dict)


class LLMResponse(BaseModel):
    """Response schema for an LLM response."""

    id: UUID
    evaluation_id: UUID
    question_id: str
    model_name: str
    response_text: str
    source: ResponseSource
    raw_metadata: dict
    created_at: datetime

    model_config = {"from_attributes": True}
