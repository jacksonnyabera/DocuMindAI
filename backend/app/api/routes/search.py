
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.embeddings.provider import get_embedding_provider
from app.models.user import User
from app.schemas.search import SearchRequest, SearchResponse
from app.services.search_service import search_documents


router = APIRouter(tags=["Search"])


@router.post(
    "/search",
    response_model=SearchResponse,
)
def search_documents_endpoint(
    request: SearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Search documents belonging exclusively to the authenticated user's organization."""

    try:
        results = search_documents(
            db=db,
            organization_id=current_user.organization_id,
            question=request.question,
            embedding_provider=get_embedding_provider(),
            limit=request.limit,
        )

        return SearchResponse(
            results=results,
            total_results=len(results),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        )

    except RuntimeError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The search service is temporarily unavailable.",
        )
