
from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
from jwt.exceptions import InvalidTokenError

from app.core.config import settings


ALGORITHM = "HS256"


def create_access_token(
    user_id: UUID,
    organization_id: UUID,
) -> str:
    """Create a signed JWT access token."""

    secret = settings.secret_key.get_secret_value()

    if not secret:
        raise RuntimeError("SECRET_KEY is not configured.")

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(
        minutes=settings.access_token_expire_minutes
    )

    payload = {
        "sub": str(user_id),
        "org": str(organization_id),
        "exp": expires_at,
        "iat": now,
    }

    return jwt.encode(
        payload,
        secret,
        algorithm=ALGORITHM,
    )


def decode_access_token(token: str) -> dict:
    """Verify and decode a JWT access token."""

    secret = settings.secret_key.get_secret_value()

    if not secret:
        raise RuntimeError("SECRET_KEY is not configured.")

    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=[ALGORITHM],
            options={"require": ["sub", "org", "exp", "iat"]},
        )

        # Validate UUID claims before using them.
        UUID(payload["sub"])
        UUID(payload["org"])

        return payload

    except (
        InvalidTokenError,
        ValueError,
        TypeError,
        KeyError,
    ) as exc:
        raise ValueError("Invalid or expired access token.") from exc
