import math
import uuid

from sqlalchemy.orm import Session

from app.document_processing.pipeline import process_pdf
from app.embeddings.base import EmbeddingProvider
from app.models.document import Document
from app.models.document_chunk import DocumentChunk


def ingest_document(
    db: Session,
    document_id: uuid.UUID,
    organization_id: uuid.UUID,
    embedding_provider: EmbeddingProvider,
) -> dict:
    """Process a PDF and persist its embedded chunks."""

    document = (
        db.query(Document)
        .filter(
            Document.id == document_id,
            Document.organization_id == organization_id,
        )
        .with_for_update()
        .first()
    )

    if document is None:
        raise LookupError("Document not found in this organization.")

    try:
        document.status = "processing"
        db.flush()

        processed = process_pdf(document.storage_path)
        chunks = processed["chunks"]

        if not chunks:
            raise ValueError("The PDF contains no extractable text.")

        texts = [chunk["text"] for chunk in chunks]
        embeddings = embedding_provider.embed_documents(texts)

        if len(embeddings) != len(chunks):
            raise ValueError(
                "The embedding provider returned an incorrect "
                "number of embeddings."
            )

        validated_embeddings = []

        for embedding in embeddings:
            if not isinstance(embedding, (list, tuple)):
                raise ValueError("Each embedding must be a list.")

            if len(embedding) != embedding_provider.dimensions:
                raise ValueError(
                    "Embedding dimensions do not match the provider."
                )

            vector = []

            for value in embedding:
                if (
                    isinstance(value, bool)
                    or not isinstance(value, (int, float))
                    or not math.isfinite(value)
                ):
                    raise ValueError(
                        "Embeddings must contain finite numeric values."
                    )

                vector.append(float(value))

            validated_embeddings.append(vector)

        db.query(DocumentChunk).filter(
            DocumentChunk.document_id == document.id,
            DocumentChunk.organization_id == organization_id,
        ).delete(synchronize_session=False)

        stored_chunks = [
            DocumentChunk(
                organization_id=organization_id,
                document_id=document.id,
                page_number=chunk["page_number"],
                chunk_index=chunk["chunk_index"],
                content=chunk["text"],
                embedding=embedding,
                metadata_json={
                    "filename": chunk["filename"],
                    "chunk_index": chunk["chunk_index"],
                },
            )
            for chunk, embedding in zip(
                chunks,
                validated_embeddings,
            )
        ]

        db.add_all(stored_chunks)

        document.total_pages = processed["total_pages"]
        document.total_chunks = len(stored_chunks)
        document.status = "ready"

        db.commit()

        return {
            "document_id": str(document.id),
            "filename": document.filename,
            "total_pages": document.total_pages,
            "total_chunks": document.total_chunks,
            "status": document.status,
        }

    except Exception:
        db.rollback()

        # Record failure in a fresh transaction after rollback.
        try:
            failed_document = (
                db.query(Document)
                .filter(
                    Document.id == document_id,
                    Document.organization_id == organization_id,
                )
                .with_for_update()
                .first()
            )

            if failed_document is not None:
                failed_document.status = "failed"
                db.commit()

        except Exception:
            db.rollback()

        raise
