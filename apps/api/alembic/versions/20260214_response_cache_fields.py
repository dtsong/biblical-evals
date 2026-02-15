"""Add response caching fields.

Revision ID: 20260214_response_cache
Revises: 20260214_prompt_template_id
Create Date: 2026-02-14
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260214_response_cache"
down_revision = "20260214_prompt_template_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "evaluations",
        sa.Column(
            "use_cache",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )

    op.add_column(
        "responses",
        sa.Column("cache_source_response_id", sa.UUID(), nullable=True),
    )
    op.create_index(
        op.f("ix_responses_cache_source_response_id"),
        "responses",
        ["cache_source_response_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_responses_cache_source_response_id",
        "responses",
        "responses",
        ["cache_source_response_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_responses_cache_source_response_id",
        "responses",
        type_="foreignkey",
    )
    op.drop_index(op.f("ix_responses_cache_source_response_id"), table_name="responses")
    op.drop_column("responses", "cache_source_response_id")
    op.drop_column("evaluations", "use_cache")
