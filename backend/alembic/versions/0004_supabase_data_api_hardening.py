"""harden public tables against direct Supabase Data API access

Revision ID: 0004
Revises: 0003
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = (
    "users",
    "questions",
    "approved_answers",
    "answer_aliases",
    "matches",
    "rounds",
    "submitted_answers",
)


def upgrade() -> None:
    # The backend connects directly as the database owner, so it continues to
    # work. With no RLS policies, Supabase's anon/authenticated Data API roles
    # cannot read or mutate these server-owned tables.
    for table in TABLES:
        op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')

    # These roles exist on Supabase but not in a plain local PostgreSQL setup.
    # Conditional blocks keep the same migration chain portable.
    for role in ("anon", "authenticated"):
        op.execute(
            f"""
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{role}') THEN
                    REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM {role};
                    REVOKE USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public FROM {role};
                    ALTER DEFAULT PRIVILEGES IN SCHEMA public
                        REVOKE ALL PRIVILEGES ON TABLES FROM {role};
                    ALTER DEFAULT PRIVILEGES IN SCHEMA public
                        REVOKE USAGE, SELECT ON SEQUENCES FROM {role};
                END IF;
            END
            $$
            """
        )


def downgrade() -> None:
    # Do not restore broad Data API grants automatically. If this migration is
    # downgraded, access should still be granted explicitly and deliberately.
    for table in TABLES:
        op.execute(f'ALTER TABLE "{table}" DISABLE ROW LEVEL SECURITY')
