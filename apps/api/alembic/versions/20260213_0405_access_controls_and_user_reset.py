"""Add access controls and reset non-admin users.

Revision ID: 20260213_access
Revises:
Create Date: 2026-02-13 04:05:00
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260213_access"
down_revision = None
branch_labels = None
depends_on = None

ADMIN_EMAILS = ["xdtsong@gmail.com", "daniel@appraisehq.ai"]
PRIMARY_ADMIN_EMAIL = "xdtsong@gmail.com"


def _find_user_id_by_email(bind: sa.Connection, email: str):
    result = bind.execute(
        sa.text("SELECT id FROM users WHERE lower(email) = :email LIMIT 1"),
        {"email": email.lower()},
    )
    return result.scalar_one_or_none()


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "access_status",
            sa.String(length=20),
            nullable=False,
            server_default="not_requested",
        ),
    )
    op.add_column(
        "users",
        sa.Column("access_requested_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("access_reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("access_reviewed_by", sa.UUID(), nullable=True),
    )
    op.create_index(
        op.f("ix_users_access_reviewed_by"),
        "users",
        ["access_reviewed_by"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_users_access_reviewed_by_users",
        "users",
        "users",
        ["access_reviewed_by"],
        ["id"],
    )

    bind = op.get_bind()
    now = datetime.now(timezone.utc)

    for email in ADMIN_EMAILS:
        existing_id = _find_user_id_by_email(bind, email)
        if existing_id is None:
            new_id = uuid4()
            bind.execute(
                sa.text(
                    """
                    INSERT INTO users (
                        id,
                        auth_provider_id,
                        email,
                        display_name,
                        role,
                        access_status,
                        access_requested_at,
                        access_reviewed_at,
                        access_reviewed_by
                    ) VALUES (
                        :id,
                        :auth_provider_id,
                        :email,
                        :display_name,
                        'admin',
                        'approved',
                        :now,
                        :now,
                        :id
                    )
                    """
                ),
                {
                    "id": new_id,
                    "auth_provider_id": f"bootstrap-admin:{email}",
                    "email": email,
                    "display_name": email,
                    "now": now,
                },
            )

    primary_admin_id = _find_user_id_by_email(bind, PRIMARY_ADMIN_EMAIL)
    if primary_admin_id is None:
        raise RuntimeError("Primary admin user was not created")

    bind.execute(
        sa.text(
            """
            UPDATE users
            SET
              role = 'admin',
              access_status = 'approved',
              access_requested_at = COALESCE(access_requested_at, :now),
              access_reviewed_at = :now,
              access_reviewed_by = id
            WHERE lower(email) IN :admin_emails
            """
        ).bindparams(sa.bindparam("admin_emails", expanding=True)),
        {"admin_emails": [email.lower() for email in ADMIN_EMAILS], "now": now},
    )

    non_admin_ids = [
        row[0]
        for row in bind.execute(
            sa.text(
                "SELECT id FROM users WHERE lower(email) NOT IN :admin_emails"
            ).bindparams(sa.bindparam("admin_emails", expanding=True)),
            {"admin_emails": [email.lower() for email in ADMIN_EMAILS]},
        ).all()
    ]

    if non_admin_ids:
        bind.execute(
            sa.text(
                "UPDATE evaluations SET created_by = :admin_id WHERE created_by IN :ids"
            ).bindparams(sa.bindparam("ids", expanding=True)),
            {"admin_id": primary_admin_id, "ids": non_admin_ids},
        )
        bind.execute(
            sa.text(
                "UPDATE scores SET user_id = :admin_id WHERE user_id IN :ids"
            ).bindparams(sa.bindparam("ids", expanding=True)),
            {"admin_id": primary_admin_id, "ids": non_admin_ids},
        )
        bind.execute(
            sa.text("DELETE FROM users WHERE id IN :ids").bindparams(
                sa.bindparam("ids", expanding=True)
            ),
            {"ids": non_admin_ids},
        )


def downgrade() -> None:
    op.drop_constraint("fk_users_access_reviewed_by_users", "users", type_="foreignkey")
    op.drop_index(op.f("ix_users_access_reviewed_by"), table_name="users")
    op.drop_column("users", "access_reviewed_by")
    op.drop_column("users", "access_reviewed_at")
    op.drop_column("users", "access_requested_at")
    op.drop_column("users", "access_status")
