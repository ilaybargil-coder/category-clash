"""add friend requests and friendships

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-17
"""

import sqlalchemy as sa

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "friend_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sender_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("recipient_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "sender_id != recipient_id",
            name="ck_friend_requests_distinct_users",
        ),
    )
    op.create_index(
        "ix_friend_requests_recipient_id",
        "friend_requests",
        ["recipient_id"],
    )
    op.create_index(
        "ix_friend_requests_sender_id",
        "friend_requests",
        ["sender_id"],
    )

    op.create_table(
        "friendships",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_a_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("user_b_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "user_a_id < user_b_id",
            name="ck_friendships_normalized_pair",
        ),
        sa.UniqueConstraint(
            "user_a_id",
            "user_b_id",
            name="uq_friendships_user_pair",
        ),
    )


def downgrade() -> None:
    op.drop_table("friendships")
    op.drop_index("ix_friend_requests_sender_id", table_name="friend_requests")
    op.drop_index("ix_friend_requests_recipient_id", table_name="friend_requests")
    op.drop_table("friend_requests")
