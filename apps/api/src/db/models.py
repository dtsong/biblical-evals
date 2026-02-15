"""SQLAlchemy ORM models for biblical-evals."""

from datetime import datetime
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    """Application user (linked to auth provider via NextAuth.js)."""

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    auth_provider_id: Mapped[str] = mapped_column(
        String(128), unique=True, nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'reviewer'")
    )
    access_status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'not_requested'")
    )
    access_requested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    access_reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    access_reviewed_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    perspective: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Relationships
    evaluations: Mapped[list["Evaluation"]] = relationship(
        back_populates="creator", cascade="all, delete-orphan"
    )
    scores: Mapped[list["Score"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Evaluation(Base, TimestampMixin):
    """An evaluation run comparing multiple LLMs on a question set."""

    __tablename__ = "evaluations"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'created'")
    )
    perspective: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default=text("'multi_perspective'")
    )
    scoring_dimensions: Mapped[dict] = mapped_column(JSONB, nullable=False, default=[])
    model_list: Mapped[dict] = mapped_column(JSONB, nullable=False)
    prompt_template: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default=text("'default'")
    )
    use_cache: Mapped[bool] = mapped_column(
        sa.Boolean(), nullable=False, server_default=text("true")
    )
    review_mode: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'blind'")
    )
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)

    # Relationships
    creator: Mapped["User"] = relationship(back_populates="evaluations")
    responses: Mapped[list["Response"]] = relationship(
        back_populates="evaluation", cascade="all, delete-orphan"
    )


class Question(Base):
    """A question stored in the database (synced from YAML files)."""

    __tablename__ = "questions"

    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    difficulty: Mapped[str] = mapped_column(String(20), nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)

    # Relationships
    responses: Mapped[list["Response"]] = relationship(
        back_populates="question", cascade="all, delete-orphan"
    )


class Response(Base, TimestampMixin):
    """An LLM response to a question within an evaluation."""

    __tablename__ = "responses"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    evaluation_id: Mapped[UUID] = mapped_column(
        ForeignKey("evaluations.id"), nullable=False, index=True
    )
    question_id: Mapped[str] = mapped_column(
        ForeignKey("questions.id"), nullable=False, index=True
    )
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_template_id: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default=text("'default'")
    )
    cache_source_response_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("responses.id"), nullable=True, index=True
    )
    response_text: Mapped[str] = mapped_column(Text, nullable=False)
    response_length_words: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_length_chars: Mapped[int | None] = mapped_column(Integer, nullable=True)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_usd: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True)
    latency_seconds: Mapped[float | None] = mapped_column(Numeric(8, 3), nullable=True)
    source: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'api'")
    )
    raw_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Relationships
    evaluation: Mapped["Evaluation"] = relationship(back_populates="responses")
    question: Mapped["Question"] = relationship(back_populates="responses")
    scores: Mapped[list["Score"]] = relationship(
        back_populates="response", cascade="all, delete-orphan"
    )

    def compute_response_length(self) -> None:
        """Set word and character counts from response_text."""
        if self.response_text:
            self.response_length_chars = len(self.response_text)
            self.response_length_words = len(self.response_text.split())
        else:
            self.response_length_chars = 0
            self.response_length_words = 0


class Score(Base):
    """A human reviewer's score for a single dimension of a response."""

    __tablename__ = "scores"
    __table_args__ = (
        sa.UniqueConstraint(
            "response_id", "user_id", "dimension", name="uq_scores_response_user_dim"
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    response_id: Mapped[UUID] = mapped_column(
        ForeignKey("responses.id"), nullable=False, index=True
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    dimension: Mapped[str] = mapped_column(String(50), nullable=False)
    value: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("''")
    )
    presentation_order: Mapped[int | None] = mapped_column(Integer, nullable=True)
    scored_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    response: Mapped["Response"] = relationship(back_populates="scores")
    user: Mapped["User"] = relationship(back_populates="scores")
