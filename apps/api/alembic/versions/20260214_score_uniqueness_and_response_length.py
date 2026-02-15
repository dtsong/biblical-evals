"""Add score uniqueness constraint and response length columns.

Revision ID: 20260214_score_uq
Revises: 20260213_access
Create Date: 2026-02-14
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260214_score_uq"
down_revision = "20260213_access"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add response length columns
    op.add_column(
        "responses",
        sa.Column("response_length_words", sa.Integer(), nullable=True),
    )
    op.add_column(
        "responses",
        sa.Column("response_length_chars", sa.Integer(), nullable=True),
    )

    # Backfill response lengths from existing data
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            UPDATE responses
            SET response_length_chars = length(response_text),
                response_length_words = array_length(
                    string_to_array(trim(response_text), ' '), 1
                )
            WHERE response_length_chars IS NULL
            """
        )
    )

    # Add unique constraint on scores (response_id, user_id, dimension)
    # First, deduplicate any existing rows: keep the most recent score per tuple
    bind.execute(
        sa.text(
            """
            DELETE FROM scores
            WHERE id NOT IN (
                SELECT DISTINCT ON (response_id, user_id, dimension) id
                FROM scores
                ORDER BY response_id, user_id, dimension, scored_at DESC
            )
            """
        )
    )

    op.create_unique_constraint(
        "uq_scores_response_user_dim",
        "scores",
        ["response_id", "user_id", "dimension"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_scores_response_user_dim", "scores", type_="unique")
    op.drop_column("responses", "response_length_chars")
    op.drop_column("responses", "response_length_words")
