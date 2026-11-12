import uuid

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.tokens import ALGORITHM
from app.db.session import get_db
from app.models.user import User


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Authenticate a request using its JWT access token."""

    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not settings.secret_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication is not configured.",
        )

    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[ALGORITHM],
            options={"require": ["sub", "org", "exp", "iat"]},
        )

        user_id = uuid.UUID(payload["sub"])
        organization_id = uuid.UUID(payload["org"])

    except (InvalidTokenError, ValueError, TypeError, KeyError):
        raise credentials_error

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
