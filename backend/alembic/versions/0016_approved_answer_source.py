"""add approved answer provenance and creation timestamp

Revision ID: 0016_approved_answer_source
Revises: 0015_rls_new_tables
Create Date: 2026-07-21
"""

import sqlalchemy as sa

from alembic import op

revision = "0016_approved_answer_source"
down_revision = "0015_rls_new_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "approved_answers",
        sa.Column("source", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "approved_answers",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("approved_answers", "created_at")
    op.drop_column("approved_answers", "source")
