"""Add cost tracking columns to responses table.

Revision ID: 20260214_cost
Revises: 20260214_score_uq
Create Date: 2026-02-14
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260214_cost"
down_revision = "20260214_score_uq"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "responses",
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
    )
    op.add_column(
        "responses",
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
    )
    op.add_column(
        "responses",
        sa.Column("cost_usd", sa.Numeric(10, 6), nullable=True),
    )
    op.add_column(
        "responses",
        sa.Column("latency_seconds", sa.Numeric(8, 3), nullable=True),
    )

    # Backfill from raw_metadata JSONB
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            UPDATE responses
            SET prompt_tokens = (raw_metadata->>'prompt_tokens')::integer,
                completion_tokens = (raw_metadata->>'completion_tokens')::integer,
                cost_usd = (raw_metadata->>'cost_usd')::numeric(10,6),
                latency_seconds = (raw_metadata->>'latency_seconds')::numeric(8,3)
            WHERE raw_metadata IS NOT NULL
              AND prompt_tokens IS NULL
            """
        )
    )


def downgrade() -> None:
    op.drop_column("responses", "latency_seconds")
    op.drop_column("responses", "cost_usd")
    op.drop_column("responses", "completion_tokens")
    op.drop_column("responses", "prompt_tokens")
