"""Application configuration.

Every gameplay constant lives here and can be overridden via environment
variables (see .env.example at the repo root).
"""

from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(PROJECT_ROOT / ".env", PROJECT_ROOT / "backend" / ".env"),
        extra="ignore",
    )

    # Infrastructure
    database_url: str = "postgresql+asyncpg://game:game@localhost:5432/game"
    cors_origins: str = "http://localhost:3000"
    websocket_origins: str = "http://localhost:3000"
    websocket_allow_missing_origin: bool = True
    database_pool_size: int = 5
    database_pool_recycle_seconds: int = 300
    readiness_timeout_seconds: float = 3.0

    # Auth
    auth_mode: Literal["demo", "supabase"] = "demo"
    jwt_secret: str = "dev-secret-change-me-at-least-32-bytes"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 12 * 60
    supabase_url: str = ""
    supabase_publishable_key: str = ""
    supabase_auth_timeout_seconds: float = 5.0
    auth_identity_cache_seconds: int = 300

    # Gameplay
    turn_seconds: float = 15.0
    preview_seconds: float = 4.0
    intermission_seconds: float = 4.0
    rounds_to_win: int = 2
    max_answer_length: int = 60
    disconnect_forfeit_seconds: float = 60.0
    websocket_send_timeout_seconds: float = 2.0

    # Phase 2+
    invite_ttl_seconds: int = 90
    swap_question_cost_coins: int = 50
    fuzzy_matching_enabled: bool = False
    fuzzy_max_distance: int = 1
    fuzzy_min_length: int = 4

    @property
    def async_database_url(self) -> str:
        """Accept Supabase's standard Postgres URL in addition to SQLAlchemy's.

        Supabase's dashboard exposes ``postgresql://`` connection strings,
        while SQLAlchemy's async engine needs the explicit asyncpg driver.
        Keeping this conversion here lets Alembic and the application share
        one secret without asking the operator to hand-edit credentials.
        """

        url = self.database_url
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        # PostgreSQL tools call this option sslmode; asyncpg calls it ssl.
        return url.replace("sslmode=", "ssl=")

    @staticmethod
    def _origin_list(raw: str) -> list[str]:
        return [origin.strip().rstrip("/") for origin in raw.split(",") if origin.strip()]

    @property
    def cors_origin_list(self) -> list[str]:
        return self._origin_list(self.cors_origins)

    @property
    def websocket_origin_list(self) -> list[str]:
        return self._origin_list(self.websocket_origins)


settings = Settings()
