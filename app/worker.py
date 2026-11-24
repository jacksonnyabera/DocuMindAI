import logging
import socket
import time
import uuid

from sqlalchemy import select

from app.db.session import get_session_factory
from app.embeddings.provider import get_embedding_provider
from app.models.document import Document
from app.services.ingestion_service import ingest_document
from app.services.job_queue import (
    claim_next_job,
    mark_job_completed,
    retry_or_fail_job,
)

logger = logging.getLogger("documind.worker")

POLL_INTERVAL_SECONDS = 2


def process_one_job(worker_id: str) -> bool:
    """Claim and process one job. Return True when a job was claimed."""

    session_factory = get_session_factory()
    job = claim_next_job(session_factory, worker_id)

    if job is None:
        return False

    logger.info(
        "Claimed job %s for document %s (attempt %s/%s).",
        job["id"],
        job["document_id"],
        job["attempts"],
        job["max_attempts"],
    )

    try:
        with session_factory() as db:
            document = db.execute(
                select(Document).where(
                    Document.id == job["document_id"],
                    Document.organization_id == job["organization_id"],
                )
            ).scalar_one_or_none()

            if document is None:
                raise LookupError("Document no longer exists.")

            # Recovery after a crash between document commit and job completion.
            if document.status != "ready":
                provider = get_embedding_provider()

                ingest_document(
                    db=db,
                    document_id=job["document_id"],
                    organization_id=job["organization_id"],
                    embedding_provider=provider,
                )

        completed = mark_job_completed(
            session_factory,
            job["id"],
            worker_id,
        )

        if completed:
            logger.info("Completed job %s.", job["id"])
        else:
            logger.warning(
                "Job %s was processed but its lease is no longer owned "
                "by worker %s.",
                job["id"],
                worker_id,
            )

    except Exception as exc:
        logger.exception("Job %s failed.", job["id"])

        retry_or_fail_job(
            session_factory=session_factory,
            job=job,
            worker_id=worker_id,
            error=exc,
        )

    return True


def main() -> None:
    """Run the persistent document worker until interrupted."""

    worker_id = f"{socket.gethostname()}-{uuid.uuid4().hex[:12]}"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    logger.info("DocuMind worker started: %s", worker_id)

    try:
        while True:
            claimed = process_one_job(worker_id)

            if not claimed:
                time.sleep(POLL_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        logger.info("Worker shutdown requested.")

    finally:
        logger.info("Worker stopped: %s", worker_id)


if __name__ == "__main__":
    main()
