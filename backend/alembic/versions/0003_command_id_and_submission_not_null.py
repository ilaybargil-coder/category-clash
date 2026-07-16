"""add command id and require submission ids

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-16

"""

import sqlalchemy as sa

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Rows created before protocol v1 did not have submission ids. Give those
    # immutable legacy rows deterministic ids before enforcing NOT NULL.
    op.execute(
        "UPDATE submitted_answers "
        "SET submission_id = md5('legacy-submission:' || id::text) "
        "WHERE submission_id IS NULL"
    )
    op.alter_column(
        "submitted_answers",
        "submission_id",
        existing_type=sa.String(32),
        nullable=False,
    )
    op.add_column(
        "submitted_answers",
        sa.Column("client_command_id", sa.String(36), nullable=True),
    )
    op.create_index(
        "ix_submitted_answers_client_command_id",
        "submitted_answers",
        ["client_command_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_submitted_answers_client_command_id",
        table_name="submitted_answers",
    )
    op.drop_column("submitted_answers", "client_command_id")
    op.alter_column(
        "submitted_answers",
        "submission_id",
        existing_type=sa.String(32),
        nullable=True,
    )
