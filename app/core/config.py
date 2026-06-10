from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Bahamas AI Trading API"
    environment: str = "development"

    database_url: str = "postgresql+psycopg://bat:change-me-in-prod@localhost:5432/bahamas_ai_trading"
    secret_key: str = "dev-only-secret-change-me"
    fernet_key: str = ""  # required in production — encrypts KYC files at rest
    access_token_expire_minutes: int = 60

    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:5174"]
    upload_dir: str = "./uploads"
    support_email: str = "support@bahamasaitrading.com"

    max_upload_bytes: int = 10 * 1024 * 1024  # 10 MB
    allowed_mime_types: tuple[str, ...] = ("application/pdf", "image/jpeg", "image/png")


@lru_cache
def get_settings() -> Settings:
    return Settings()
