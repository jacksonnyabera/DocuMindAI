import logging
import uuid

from sqlalchemy.orm import Session

from app.db.session import get_session_factory
from app.embeddings.provider import get_embedding_provider
from app.models.document import Document
from app.services.ingestion_service import ingest_document


logger = logging.getLogger(__name__)


def process_document_in_background(
    document_id: uuid.UUID,
    organization_id: uuid.UUID,
) -> None:
    """Process an uploaded document using an independent DB session."""

    db: Session | None = None

    try:
        db = get_session_factory()()

        embedding_provider = get_embedding_provider()

        ingest_document(
            db=db,
            document_id=document_id,
            organization_id=organization_id,
            embedding_provider=embedding_provider,
        )

        logger.info(
            "Document %s processed successfully.",
            document_id,
        )

    except Exception:
        logger.exception(
            "Background ingestion failed for document %s.",
            document_id,
        )

        if db is not None:
            try:
                db.rollback()

                failed_document = (
                    db.query(Document)
                    .filter(
                        Document.id == document_id,
                        Document.organization_id == organization_id,
                        Document.status.in_(("pending", "processing")),
                    )
                    .with_for_update()
                    .first()
                )

                if failed_document is not None:
                    failed_document.status = "failed"
                    db.commit()

            except Exception:
                db.rollback()
                logger.exception(
                    "Could not mark document %s as failed.",
                    document_id,
                )

    finally:
        if db is not None:
            db.close()
