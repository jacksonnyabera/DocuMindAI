
from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    app_name: str = "DocuMind AI"
    environment: str = "development"
    debug: bool = False
    log_level: str = "INFO"

    database_url: str = ""

    storage_dir: str = "storage"
    max_upload_size: int = 10 * 1024 * 1024
    max_pdf_pages: int = 100
    max_pdf_text_chars: int = 1_000_000

    secret_key: SecretStr = SecretStr("")
    access_token_expire_minutes: int = 30

    # LLM configuration
    llm_provider: str = "gemini"
    gemini_api_key: SecretStr = SecretStr("")
    gemini_model: str = "gemini-2.5-flash"

    @model_validator(mode="after")
    def validate_production_security(self):
        """Reject missing or weak JWT secrets in production."""

        if self.environment.strip().lower() == "production":
            secret = self.secret_key.get_secret_value()

            if len(secret) < 32:
                raise ValueError(
                    "Production SECRET_KEY must contain "
                    "at least 32 characters."
                )

        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
