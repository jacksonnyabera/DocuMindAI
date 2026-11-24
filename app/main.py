import logging

from fastapi import FastAPI, HTTPException
from sqlalchemy import text

from starlette.middleware.body_limit import RequestBodyLimitMiddleware

from app.api.routes.auth import router as auth_router
from app.api.routes.documents import router as documents_router
from app.api.routes.search import router as search_router
from app.api.routes.chat import router as chat_router
from app.core.config import settings
from app.core.logging_config import configure_logging
from app.db.session import get_session_factory
from app.services.health_monitor import get_health_snapshot

configure_logging()

logger = logging.getLogger("documind.health")

app = FastAPI(
    title=settings.app_name,
    description="AI-powered document understanding and retrieval.",
    version="0.1.0",
)

app.add_middleware(
    RequestBodyLimitMiddleware,
    max_body_size=settings.max_upload_size + (64 * 1024),
)

app.include_router(auth_router)
app.include_router(documents_router)
app.include_router(search_router)
app.include_router(chat_router)


@app.get("/health")
def health_check():
    """Liveness check: confirms the API process is responding."""
    return {
        "status": "healthy",
        "application": settings.app_name,
    }


@app.get("/health/ready")
def readiness_check():
    """Readiness check: verifies database connectivity and reports aggregates."""
    try:
        session_factory = get_session_factory()

        with session_factory() as db:
            db.execute(text("SELECT 1"))
            snapshot = get_health_snapshot(db)

        return {
            "status": "ready",
            "application": settings.app_name,
            **snapshot,
        }

    except Exception as exc:
        logger.exception("Application readiness check failed.")

        raise HTTPException(
            status_code=503,
            detail="Application dependencies are unavailable.",
        ) from exc
