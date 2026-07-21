"""add user avatar

Revision ID: 0013_user_avatar
Revises: 0012_served_questions
Create Date: 2026-07-21
"""

import sqlalchemy as sa

from alembic import op

revision = "0013_user_avatar"
down_revision = "0012_served_questions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("avatar", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "avatar")
