from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.tokens import decode_access_token
from app.db.session import get_db
from app.models.user import User


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the authenticated user from a verified access token."""

    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(token)
    except RuntimeError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication is not configured.",
        )
    except ValueError:
        raise credentials_error

    user_id = payload["sub"]
    organization_id = payload["org"]

    user = (
        db.query(User)
        .filter(
            User.id == user_id,
            User.organization_id == organization_id,
        )
        .first()
    )

    if user is None:
        raise credentials_error

    return user


def _configured_platform_admin_emails() -> set[str]:
    """Return normalized platform-admin email addresses."""

    return {
        email.strip().lower()
        for email in settings.platform_admin_emails.split(",")
        if email.strip()
    }


def require_platform_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Require explicit platform-admin allowlist membership.

    Organization roles such as owner and member do not grant platform access.
    An empty allowlist denies access to everyone.
    """

    allowed_emails = _configured_platform_admin_emails()
    user_email = current_user.email.strip().lower()

    if not allowed_emails or user_email not in allowed_emails:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform administrator access required.",
        )

    return current_user
