import logging
import socket
import time
import uuid

from sqlalchemy import select

from app.core.logging_config import configure_logging
from app.db.session import get_session_factory
from app.embeddings.provider import get_embedding_provider
from app.models.document import Document
from app.services.ingestion_service import ingest_document
from app.services.job_heartbeat import JobLeaseHeartbeat
from app.services.job_queue import (
    claim_next_job,
    mark_job_completed,
    retry_or_fail_job,
)

logger = logging.getLogger("documind.worker")

POLL_INTERVAL_SECONDS = 2
ERROR_BACKOFF_SECONDS = 5


def process_one_job(worker_id: str) -> bool:
    session_factory = get_session_factory()
    job = claim_next_job(session_factory, worker_id)

    if job is None:
        return False

    job_id = job["id"]
    document_id = job["document_id"]
    organization_id = job["organization_id"]

    logger.info(
        "Claimed job %s for document %s (attempt %s/%s).",
        job_id,
        document_id,
        job["attempts"],
        job["max_attempts"],
    )

    try:
        with JobLeaseHeartbeat(
            session_factory=session_factory,
            job_id=job_id,
            worker_id=worker_id,
        ):
            with session_factory() as db:
                document = db.execute(
                    select(Document).where(
                        Document.id == document_id,
                        Document.organization_id == organization_id,
                    )
                ).scalar_one_or_none()

                if document is None:
                    raise LookupError(
                        f"Document {document_id} was not found."
                    )

                if document.status != "ready":
                    embedding_provider = get_embedding_provider()

                    ingest_document(
                        db=db,
                        document_id=document_id,
                        organization_id=organization_id,
                        embedding_provider=embedding_provider,
                    )

        completed = mark_job_completed(
            session_factory=session_factory,
            job_id=job_id,
            worker_id=worker_id,
        )

        if completed:
            logger.info("Completed job %s.", job_id)
        else:
            logger.warning(
                "Job %s was processed, but this worker no longer owns its lease.",
                job_id,
            )

    except Exception as exc:
        logger.exception("Job %s failed during processing.", job_id)

        try:
            retry_or_fail_job(
                session_factory=session_factory,
                job=job,
                worker_id=worker_id,
                error=exc,
            )
        except Exception:
            logger.exception(
                "Could not record retry or failure state for job %s. "
                "Lease recovery will handle it if necessary.",
                job_id,
            )

    return True


def main() -> None:
    worker_id = f"{socket.gethostname()}-{uuid.uuid4().hex[:12]}"

    configure_logging()

    logger.info("DocuMind worker started: %s", worker_id)

    try:
        while True:
            try:
                claimed = process_one_job(worker_id)

                if not claimed:
                    time.sleep(POLL_INTERVAL_SECONDS)

            except KeyboardInterrupt:
                raise
            except Exception:
                logger.exception(
                    "Worker loop encountered an unexpected error."
                )
                time.sleep(ERROR_BACKOFF_SECONDS)

    except KeyboardInterrupt:
        logger.info("Worker shutdown requested.")

    finally:
        logger.info("DocuMind worker stopped: %s", worker_id)


if __name__ == "__main__":
    main()
