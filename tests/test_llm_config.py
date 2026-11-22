
from pydantic import SecretStr

from app.core.config import Settings


def test_gemini_configuration_defaults():
    settings = Settings(_env_file=None)

    assert settings.llm_provider == "gemini"
    assert settings.gemini_model == "gemini-2.5-flash"
    assert settings.gemini_api_key.get_secret_value() == ""


def test_gemini_api_key_is_stored_as_secret():
    settings = Settings(
        _env_file=None,
        gemini_api_key="test-secret-key",
    )

    assert isinstance(settings.gemini_api_key, SecretStr)
    assert str(settings.gemini_api_key) == "**********"
    assert "test-secret-key" not in repr(settings)


def test_existing_database_configuration_is_preserved():
    settings = Settings(
        _env_file=None,
        database_url="postgresql://test",
        secret_key="test-jwt-secret",
    )

    assert settings.database_url == "postgresql://test"
    assert settings.secret_key == "test-jwt-secret"
