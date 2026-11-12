
import logging
import uuid

from app.core.config import settings
from app.db.session import get_session_factory
from app.embeddings.fake import FakeEmbeddingProvider
from app.services.ingestion_service import ingest_document


logger = logging.getLogger(__name__)


def process_document_in_background(
    document_id: uuid.UUID,
    organization_id: uuid.UUID,
) -> None:
    """Process an uploaded document using an independent DB session."""

    db = get_session_factory()()

    try:
        if settings.environment != "development":
            raise RuntimeError(
                "A production embedding provider has not been configured."
            )

        ingest_document(
            db=db,
            document_id=document_id,
            organization_id=organization_id,
            embedding_provider=FakeEmbeddingProvider(dimensions=16),
        )

        logger.info("Document %s processed successfully.", document_id)

    except Exception:
        logger.exception(
            "Background ingestion failed for document %s.",
            document_id,
        )

    finally:
        db.close()
