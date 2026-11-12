
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

    if not settings.secret_key:
        raise RuntimeError("SECRET_KEY is not configured.")

    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )

    payload = {
        "sub": str(user_id),
        "org": str(organization_id),
        "exp": expires_at,
        "iat": datetime.now(timezone.utc),
    }

    return jwt.encode(
        payload,
        settings.secret_key,
        algorithm=ALGORITHM,
    )


def decode_access_token(token: str) -> dict:
    """Verify and decode a JWT access token."""

    if not settings.secret_key:
        raise RuntimeError("SECRET_KEY is not configured.")

    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
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
