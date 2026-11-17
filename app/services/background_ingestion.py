
import logging
import uuid

from app.db.session import get_session_factory
from app.embeddings.provider import get_embedding_provider
from app.services.ingestion_service import ingest_document


logger = logging.getLogger(__name__)


def process_document_in_background(
    document_id: uuid.UUID,
    organization_id: uuid.UUID,
) -> None:
    """Process an uploaded document using an independent DB session."""

    db = get_session_factory()()

    try:
        embedding_provider = get_embedding_provider()

        ingest_document(
            db=db,
            document_id=document_id,
            organization_id=organization_id,
            embedding_provider=embedding_provider,
        )

        logger.info("Document %s processed successfully.", document_id)

    except Exception:
        logger.exception(
            "Background ingestion failed for document %s.",
            document_id,
        )

    finally:
        db.close()
