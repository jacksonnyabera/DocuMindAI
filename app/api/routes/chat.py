
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.embeddings.provider import get_embedding_provider
from app.llm.provider import get_llm_provider
from app.models.user import User
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.rag_service import generate_rag_answer


router = APIRouter(tags=["Chat"])


@router.post(
    "/chat",
    response_model=ChatResponse,
)
def chat_endpoint(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Answer questions using documents belonging to the user's organization."""

    if not settings.secret_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication is not configured.",
        )

    try:
        result = generate_rag_answer(
            db=db,
            organization_id=current_user.organization_id,
            question=request.question,
            embedding_provider=get_embedding_provider(),
            llm_provider=get_llm_provider(),
            limit=request.limit,
        )

        return ChatResponse(**result)

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        )

    except RuntimeError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The chat service is temporarily unavailable.",
        )
