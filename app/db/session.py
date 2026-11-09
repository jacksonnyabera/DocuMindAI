from functools import lru_cache
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Create and cache the SQLAlchemy database engine."""

    if not settings.database_url:
        raise RuntimeError(
            "DATABASE_URL is not configured. "
            "Set it in your .env file before accessing the database."
        )

    return create_engine(
        settings.database_url,
        pool_pre_ping=True,
    )


def get_session_factory() -> sessionmaker:
    """Create a session factory."""

    return sessionmaker(
        bind=get_engine(),
        class_=Session,
        expire_on_commit=False,
    )


def get_db() -> Generator[Session, None, None]:
    """Provide a database session and close it after use."""

    db = get_session_factory()()

    try:
        yield db
    finally:
        db.close()