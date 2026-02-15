"""Typed schema for LLM call metadata stored on Response.raw_metadata.

This is intentionally provider-agnostic. Fields are optional when they depend on
provider support, but the overall shape is stable so evaluations are reproducible.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class GenerationParams(BaseModel):
    """Generation parameters used for a single LLM call."""

    temperature: float
    max_tokens: int
    top_p: float | None = None
    seed: int | None = None
    frequency_penalty: float | None = None
    presence_penalty: float | None = None


class LLMResponseRawMetadata(BaseModel):
    """Reproducibility metadata captured for each response."""

    # Requested model/provider
    model: str | None = None
    provider: str | None = None

    # Provider-reported identifiers
    model_version: str | None = None
    system_fingerprint: str | None = None
    provider_response_id: str | None = None

    # Exact content sent
    rendered_prompt: str

    generation_params: GenerationParams

    # Usage/cost
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    cost_usd: float | None = None
    latency_seconds: float | None = None

    # Timing (UTC)
    timestamp_request: datetime | None = None
    timestamp_response: datetime | None = None

    # Allow forward-compatible additions without losing strict typing.
    model_config = {"extra": "allow"}
