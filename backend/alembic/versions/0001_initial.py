"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-07-16

"""

import sqlalchemy as sa

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(32), nullable=False),
        sa.Column("display_name", sa.String(64), nullable=False),
        sa.Column("password_hash", sa.String(128), nullable=False),
        sa.Column("coins", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("wins", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("losses", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    op.create_table(
        "questions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("text", sa.Text(), nullable=False, unique=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    op.create_table(
        "approved_answers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "question_id",
            sa.Integer(),
            sa.ForeignKey("questions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("canonical", sa.String(120), nullable=False),
        sa.Column("semantic_group", sa.String(120), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.UniqueConstraint("question_id", "canonical"),
    )
    op.create_index("ix_approved_answers_question_id", "approved_answers", ["question_id"])

    op.create_table(
        "answer_aliases",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "approved_answer_id",
            sa.Integer(),
            sa.ForeignKey("approved_answers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("alias", sa.String(120), nullable=False),
        sa.UniqueConstraint("approved_answer_id", "alias"),
    )
    op.create_index(
        "ix_answer_aliases_approved_answer_id", "answer_aliases", ["approved_answer_id"]
    )

    op.create_table(
        "matches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(12), nullable=False),
        sa.Column("player1_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("player2_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("winner_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("score_p1", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("score_p2", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="ACTIVE"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_matches_code", "matches", ["code"])

    op.create_table(
        "rounds",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "match_id",
            sa.Integer(),
            sa.ForeignKey("matches.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("round_no", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.Integer(), sa.ForeignKey("questions.id"), nullable=False),
        sa.Column("starter_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("winner_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("end_reason", sa.String(20), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_rounds_match_id", "rounds", ["match_id"])

    op.create_table(
        "submitted_answers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "round_id",
            sa.Integer(),
            sa.ForeignKey("rounds.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("raw_text", sa.String(200), nullable=False),
        sa.Column("normalized_text", sa.String(200), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column(
            "matched_answer_id",
            sa.Integer(),
            sa.ForeignKey("approved_answers.id"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_submitted_answers_round_id", "submitted_answers", ["round_id"])
    op.create_index(
        "ix_submitted_answers_normalized_text", "submitted_answers", ["normalized_text"]
    )


def downgrade() -> None:
    op.drop_table("submitted_answers")
    op.drop_table("rounds")
    op.drop_table("matches")
    op.drop_table("answer_aliases")
    op.drop_table("approved_answers")
    op.drop_table("questions")
    op.drop_table("users")
