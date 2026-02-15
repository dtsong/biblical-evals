"""Add presentation_order to scores for deterministic blind review.

Revision ID: 20260214_presentation
Revises: 20260214_cost
Create Date: 2026-02-14
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260214_presentation"
down_revision = "20260214_cost"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "scores",
        sa.Column("presentation_order", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("scores", "presentation_order")
