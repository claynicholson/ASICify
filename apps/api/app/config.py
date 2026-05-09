"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    database_url: str = "postgresql+asyncpg://asicify:asicify@localhost:5432/asicify"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # R2 / S3
    r2_account_id: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket: str = "asicify-artifacts"
    r2_endpoint: str = ""
    r2_public_url: str = ""

    # Clerk
    clerk_jwt_key: str = ""
    clerk_secret_key: str = ""
    clerk_issuer: str = ""

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]

    # Modal
    modal_token_id: str = ""
    modal_token_secret: str = ""

    # Feature flags
    enable_hardware_aware_ft: bool = False

    # Misc
    environment: str = "development"
    log_level: str = "INFO"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
