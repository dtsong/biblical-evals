"""Add prompt_template_id column to responses.

Revision ID: 20260214_prompt_template_id
Revises: 20260214_presentation
Create Date: 2026-02-14
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260214_prompt_template_id"
down_revision = "20260214_presentation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "responses",
        sa.Column(
            "prompt_template_id",
            sa.String(length=50),
            nullable=False,
            server_default=sa.text("'default'"),
        ),
    )

    # Backfill existing rows defensively.
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            UPDATE responses
            SET prompt_template_id = 'default'
            WHERE prompt_template_id IS NULL
            """
        )
    )


def downgrade() -> None:
    op.drop_column("responses", "prompt_template_id")
