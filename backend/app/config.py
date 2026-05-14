"""Application configuration — Pydantic Settings."""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        protected_namespaces=(),   # allow model_artifacts_dir without warning
    )

    # --- Core ---
    app_name: str = "SmartCart AI"
    environment: str = Field(default="development")
    debug: bool = Field(default=False)
    sql_echo: bool = Field(default=False)

    # --- Database ---
    database_url: str

    # --- JWT ---
    jwt_secret_key: str = Field(min_length=32)
    jwt_algorithm: str = Field(default="HS256")
    jwt_access_token_expire_minutes: int = Field(default=15)
    jwt_refresh_token_expire_days: int = Field(default=7)

    # --- CORS ---
    # Comma-separated env var, parsed below. Production must be explicit; localhost
    # is fine in dev but not what we want serving production traffic.
    cors_allowed_origins: list[str] = Field(default=["http://localhost:5173"])

    # --- ML ---
    drl_inference_enabled: bool = Field(default=True)
    drl_training_trigger_threshold: int = Field(default=20)
    drl_active_model_refresh_seconds: int = Field(default=60)

    # --- Bcrypt ---
    bcrypt_rounds: int = Field(default=12)

    # --- ML artefact storage ---
    # Default: writeable directory in the working dir. On Render free tier the
    # filesystem is ephemeral — restarts wipe model_artifacts/. For MVP we
    # accept this; the trainer will rebuild on the next training cycle. For
    # production we'd point this at S3 or Render persistent disk.
    model_artifacts_dir: str = Field(default="model_artifacts")

    @field_validator("database_url")
    @classmethod
    def _validate_database_url(cls, v: str) -> str:
        # Pydantic v2 PostgresDsn accepts both 'postgresql://' and 'postgresql+psycopg2://'.
        # Neon emits the bare 'postgresql://' which SQLAlchemy needs to upgrade.
        if v.startswith("postgresql://"):
            v = v.replace("postgresql://", "postgresql+psycopg2://", 1)
        PostgresDsn(v)
        return v

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def _split_cors_origins(cls, v):
        """Accept comma-separated string OR list. Render's env vars are strings."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()