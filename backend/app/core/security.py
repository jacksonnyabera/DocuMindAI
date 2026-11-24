
from pwdlib import PasswordHash


password_hasher = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """Securely hash a user's password."""

    if not isinstance(password, str):
        raise TypeError("Password must be a string.")

    if len(password) < 8:
        raise ValueError("Password must contain at least 8 characters.")

    return password_hasher.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    """Verify a password against its stored hash."""

    if not isinstance(plain_password, str):
        return False

    if not isinstance(hashed_password, str):
        return False

    return password_hasher.verify(
        plain_password,
        hashed_password,
    )
