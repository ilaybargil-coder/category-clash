"""add submission_id to submitted_answers

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-16

"""

import sqlalchemy as sa

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "submitted_answers",
        sa.Column("submission_id", sa.String(32), nullable=True),
    )
    op.create_index(
        "ix_submitted_answers_submission_id",
        "submitted_answers",
        ["submission_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_submitted_answers_submission_id", table_name="submitted_answers")
    op.drop_column("submitted_answers", "submission_id")
