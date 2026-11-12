
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    app_name: str = "DocuMind AI"
    environment: str = "development"
    debug: bool = False

    database_url: str = ""

    storage_dir: str = "storage"
    max_upload_size: int = 10 * 1024 * 1024

    secret_key: str = ""
    access_token_expire_minutes: int = 30

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
