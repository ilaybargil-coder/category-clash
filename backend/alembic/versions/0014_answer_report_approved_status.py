"""rename accepted answer report status to approved

Revision ID: 0014_report_status
Revises: 0013_user_avatar
Create Date: 2026-07-21
"""

from alembic import op

revision = "0014_report_status"
down_revision = "0013_user_avatar"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_answer_reports_status", "answer_reports", type_="check")
    op.execute("UPDATE answer_reports SET status = 'approved' WHERE status = 'accepted'")
    op.create_check_constraint(
        "ck_answer_reports_status",
        "answer_reports",
        "status IN ('pending', 'approved', 'rejected')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_answer_reports_status", "answer_reports", type_="check")
    op.execute("UPDATE answer_reports SET status = 'accepted' WHERE status = 'approved'")
    op.create_check_constraint(
        "ck_answer_reports_status",
        "answer_reports",
        "status IN ('pending', 'accepted', 'rejected')",
    )
