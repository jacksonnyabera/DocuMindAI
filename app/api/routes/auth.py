from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password, verify_password
from app.core.tokens import create_access_token
from app.db.session import get_db
from app.models.organization import Organization
from app.models.user import User
from app.schemas.auth import RegisterRequest, TokenResponse


router = APIRouter(prefix="/auth", tags=["Authentication"])


def create_token_response(user: User) -> dict:
    token = create_access_token(
        user_id=user.id,
        organization_id=user.organization_id,
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": settings.access_token_expire_minutes * 60,
        "user_id": str(user.id),
        "organization_id": str(user.organization_id),
        "full_name": user.full_name,
        "email": user.email,
        "role": user.role,
    }


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    payload: RegisterRequest,
    db: Session = Depends(get_db),
):
    """Register a company and its first owner account."""

    if not settings.secret_key:
        raise HTTPException(
            status_code=500,
            detail="Authentication is not configured.",
        )

    existing_user = (
        db.query(User)
        .filter(func.lower(User.email) == payload.email)
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    organization = Organization(
        name=payload.organization_name,
    )

    try:
        db.add(organization)
        db.flush()

        user = User(
            organization_id=organization.id,
            email=payload.email,
            full_name=payload.full_name,
            password_hash=hash_password(payload.password),
            role="owner",
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        return create_token_response(user)

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    except Exception:
        db.rollback()
        raise


@router.post(
    "/login",
    response_model=TokenResponse,
)
def login(
    credentials: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Authenticate a user and return an access token."""

    if not settings.secret_key:
        raise HTTPException(
            status_code=500,
            detail="Authentication is not configured.",
        )

    email = credentials.username.strip().lower()

    user = (
        db.query(User)
        .filter(func.lower(User.email) == email)
        .first()
    )

    if user is None or not verify_password(
        credentials.password,
        user.password_hash,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return create_token_response(user)
