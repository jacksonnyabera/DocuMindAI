from fastapi import FastAPI

from app.api.routes.auth import router as auth_router
from app.api.routes.documents import router as documents_router
from app.core.config import settings


app = FastAPI(
    title=settings.app_name,
    description="AI-powered document understanding and retrieval.",
    version="0.1.0",
)

app.include_router(auth_router)
app.include_router(documents_router)


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "application": settings.app_name,
    }
