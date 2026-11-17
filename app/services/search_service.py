import math
import uuid

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.embeddings.base import EmbeddingProvider
from app.models.document import Document
from app.models.document_chunk import DocumentChunk


def search_documents(
    db: Session,
    organization_id: uuid.UUID,
    question: str,
    embedding_provider: EmbeddingProvider,
    limit: int = 5,
) -> list[dict]:
    """Retrieve the most relevant document chunks for an organization."""

    if not isinstance(question, str) or not question.strip():
        raise ValueError("Search question cannot be empty.")

    if not isinstance(limit, int) or isinstance(limit, bool):
        raise ValueError("Search limit must be an integer.")

    if not 1 <= limit <= 20:
        raise ValueError("Search limit must be between 1 and 20.")

    if embedding_provider.dimensions != 384:
        raise ValueError("Embedding provider must use 384 dimensions.")

    query_embedding = embedding_provider.embed_query(question.strip())

    if len(query_embedding) != 384:
        raise ValueError("Query embedding must contain 384 dimensions.")

    for value in query_embedding:
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
        ):
            raise ValueError("Query embedding contains invalid values.")

    distance = DocumentChunk.embedding_vector.cosine_distance(
        query_embedding
    )

    results = (
        db.query(
            DocumentChunk,
            Document.filename,
            distance.label("distance"),
        )
        .join(
            Document,
            and_(
                Document.id == DocumentChunk.document_id,
                Document.organization_id == DocumentChunk.organization_id,
            ),
        )
        .filter(
            DocumentChunk.organization_id == organization_id,
            Document.organization_id == organization_id,
            Document.status == "ready",
            DocumentChunk.embedding_vector.is_not(None),
        )
        .order_by(distance.asc())
        .limit(limit)
        .all()
    )

    return [
        {
            "document_id": str(chunk.document_id),
            "filename": filename,
            "page_number": chunk.page_number,
            "content": chunk.content,
            "similarity_score": 1.0 - float(chunk_distance),
        }
        for chunk, filename, chunk_distance in results
    ]
