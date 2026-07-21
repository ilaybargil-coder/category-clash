"""backfill XP and remove retired demo users

Revision ID: 0011_backfill_xp
Revises: 0010
Create Date: 2026-07-21
"""

from alembic import op

revision = "0011_backfill_xp"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE users SET xp = wins * 30 + losses * 10")

    op.execute(
        """
        WITH demo_user_ids AS (
            SELECT id FROM users WHERE username IN ('dana', 'omer')
        )
        DELETE FROM answer_reports
        WHERE reporter_user_id IN (SELECT id FROM demo_user_ids)
        """
    )
    op.execute(
        """
        WITH demo_user_ids AS (
            SELECT id FROM users WHERE username IN ('dana', 'omer')
        )
        DELETE FROM daily_results
        WHERE user_id IN (SELECT id FROM demo_user_ids)
        """
    )
    op.execute(
        """
        WITH demo_user_ids AS (
            SELECT id FROM users WHERE username IN ('dana', 'omer')
        )
        DELETE FROM friend_requests
        WHERE sender_id IN (SELECT id FROM demo_user_ids)
           OR recipient_id IN (SELECT id FROM demo_user_ids)
        """
    )
    op.execute(
        """
        WITH demo_user_ids AS (
            SELECT id FROM users WHERE username IN ('dana', 'omer')
        )
        DELETE FROM friendships
        WHERE user_a_id IN (SELECT id FROM demo_user_ids)
           OR user_b_id IN (SELECT id FROM demo_user_ids)
        """
    )
    op.execute(
        """
        WITH demo_user_ids AS (
            SELECT id FROM users WHERE username IN ('dana', 'omer')
        ),
        demo_match_ids AS (
            SELECT id
            FROM matches
            WHERE player1_id IN (SELECT id FROM demo_user_ids)
               OR player2_id IN (SELECT id FROM demo_user_ids)
               OR winner_id IN (SELECT id FROM demo_user_ids)
        ),
        demo_round_ids AS (
            SELECT id
            FROM rounds
            WHERE match_id IN (SELECT id FROM demo_match_ids)
               OR starter_user_id IN (SELECT id FROM demo_user_ids)
               OR winner_user_id IN (SELECT id FROM demo_user_ids)
        )
        DELETE FROM submitted_answers
        WHERE user_id IN (SELECT id FROM demo_user_ids)
           OR round_id IN (SELECT id FROM demo_round_ids)
        """
    )
    op.execute(
        """
        WITH demo_user_ids AS (
            SELECT id FROM users WHERE username IN ('dana', 'omer')
        ),
        demo_match_ids AS (
            SELECT id
            FROM matches
            WHERE player1_id IN (SELECT id FROM demo_user_ids)
               OR player2_id IN (SELECT id FROM demo_user_ids)
               OR winner_id IN (SELECT id FROM demo_user_ids)
        )
        DELETE FROM rounds
        WHERE match_id IN (SELECT id FROM demo_match_ids)
           OR starter_user_id IN (SELECT id FROM demo_user_ids)
           OR winner_user_id IN (SELECT id FROM demo_user_ids)
        """
    )
    op.execute(
        """
        WITH demo_user_ids AS (
            SELECT id FROM users WHERE username IN ('dana', 'omer')
        )
        DELETE FROM matches
        WHERE player1_id IN (SELECT id FROM demo_user_ids)
           OR player2_id IN (SELECT id FROM demo_user_ids)
           OR winner_id IN (SELECT id FROM demo_user_ids)
        """
    )
    op.execute("DELETE FROM users WHERE username IN ('dana', 'omer')")


def downgrade() -> None:
    pass
