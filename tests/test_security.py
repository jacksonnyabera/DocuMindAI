
import pytest

from app.core.security import hash_password, verify_password


def test_password_is_hashed():
    password = "StrongPassword123!"

    hashed = hash_password(password)

    assert hashed != password
    assert hashed.startswith("$argon2")


def test_correct_password_is_verified():
    password = "StrongPassword123!"
    hashed = hash_password(password)

    assert verify_password(password, hashed) is True


def test_wrong_password_is_rejected():
    hashed = hash_password("StrongPassword123!")

    assert verify_password("WrongPassword123!", hashed) is False


def test_same_password_produces_different_hashes():
    password = "StrongPassword123!"

    first_hash = hash_password(password)
    second_hash = hash_password(password)

    assert first_hash != second_hash


def test_short_password_is_rejected():
    with pytest.raises(ValueError):
        hash_password("short")


def test_non_string_password_is_rejected():
    with pytest.raises(TypeError):
        hash_password(None)
