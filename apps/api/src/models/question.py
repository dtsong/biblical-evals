"""Pydantic schemas for questions."""

from enum import StrEnum

from pydantic import BaseModel, Field


class QuestionType(StrEnum):
    THEOLOGICAL = "theological"
    FACTUAL = "factual"
    INTERPRETIVE = "interpretive"


class Question(BaseModel):
    """A single evaluation question."""

    id: str = Field(description="Unique question ID (e.g. SOT-001)")
    text: str
    type: QuestionType
    difficulty: str = Field(description="easy, intermediate, or advanced")
    scripture_references: list[str] = Field(default_factory=list)
    evaluation_notes: str = ""
    denominational_sensitivity: str = Field(
        default="low", description="low, medium, or high"
    )
    tags: list[str] = Field(default_factory=list)


class QuestionFileMetadata(BaseModel):
    """Metadata header for a question YAML file."""

    category: str
    subcategory: str


class QuestionFile(BaseModel):
    """Schema for a question YAML file."""

    metadata: QuestionFileMetadata
    questions: list[Question]
