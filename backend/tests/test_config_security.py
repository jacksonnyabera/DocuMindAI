
import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_production_rejects_missing_jwt_secret():
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            environment="production",
            secret_key="",
        )


def test_production_rejects_short_jwt_secret():
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            environment="production",
            secret_key="short-secret",
        )


def test_production_accepts_strong_jwt_secret():
    settings = Settings(
        _env_file=None,
        environment="production",
        secret_key="a" * 64,
    )

    assert settings.secret_key.get_secret_value() == "a" * 64


def test_development_allows_empty_jwt_secret():
    settings = Settings(
        _env_file=None,
        environment="development",
        secret_key="",
    )

    assert settings.secret_key.get_secret_value() == ""
