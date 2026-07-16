"""link game profiles to Supabase Auth identities

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-16
"""

import sqlalchemy as sa

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("auth_user_id", sa.Uuid(), nullable=True))
    op.create_index("ix_users_auth_user_id", "users", ["auth_user_id"], unique=True)
    op.alter_column(
        "users",
        "password_hash",
        existing_type=sa.String(length=128),
        nullable=True,
    )


def downgrade() -> None:
    # Supabase-managed profiles do not have local password hashes. Preserve
    # downgrade validity without manufacturing a usable password.
    op.execute("UPDATE users SET password_hash = '' WHERE password_hash IS NULL")
    op.alter_column(
        "users",
        "password_hash",
        existing_type=sa.String(length=128),
        nullable=False,
    )
    op.drop_index("ix_users_auth_user_id", table_name="users")
    op.drop_column("users", "auth_user_id")
