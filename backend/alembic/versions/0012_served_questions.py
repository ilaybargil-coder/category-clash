"""add per-player served question history

Revision ID: 0012_served_questions
Revises: 0011_backfill_xp
Create Date: 2026-07-21
"""

import sqlalchemy as sa

from alembic import op

revision = "0012_served_questions"
down_revision = "0011_backfill_xp"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "served_questions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "question_id",
            sa.Integer(),
            sa.ForeignKey("questions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "served_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_served_questions_user_id", "served_questions", ["user_id"])
    op.create_index("ix_served_questions_served_at", "served_questions", ["served_at"])


def downgrade() -> None:
    op.drop_index("ix_served_questions_served_at", table_name="served_questions")
    op.drop_index("ix_served_questions_user_id", table_name="served_questions")
    op.drop_table("served_questions")
