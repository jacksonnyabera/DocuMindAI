import logging
from datetime import datetime, timedelta, timezone
from typing import Any
import uuid

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.document_job import DocumentJob

logger = logging.getLogger(__name__)

# A worker has one hour to finish before another worker may reclaim its job.
JOB_LOCK_TIMEOUT_SECONDS = 3600
BASE_RETRY_DELAY_SECONDS = 30
MAX_RETRY_DELAY_SECONDS = 3600


def _accumulate_attempt_duration(job: DocumentJob, finished_at: datetime) -> None:
    """Accumulate execution time for the current attempt, excluding queue wait."""
    started_at = getattr(job, "attempt_started_at", None)
    if started_at is None:
        return

    elapsed_ms = max(
        0,
        int((finished_at - started_at).total_seconds() * 1000),
    )
    job.processing_duration_ms = (
        getattr(job, "processing_duration_ms", 0) + elapsed_ms
    )
    job.attempt_started_at = None


def claim_next_job(
    session_factory: Any,
    worker_id: str,
) -> dict | None:
    """Atomically claim one available job using PostgreSQL row locking."""

    now = datetime.now(timezone.utc)
    stale_before = now - timedelta(seconds=JOB_LOCK_TIMEOUT_SECONDS)

    with session_factory() as db:
        # Jobs that exhausted their attempts while a worker was unavailable
        # must not remain permanently stuck in processing.
        exhausted = db.execute(
            select(DocumentJob)
            .where(
                DocumentJob.attempts >= DocumentJob.max_attempts,
                or_(
                    and_(
                        DocumentJob.status == "pending",
                        DocumentJob.available_at <= now,
                    ),
                    and_(
                        DocumentJob.status == "processing",
                        DocumentJob.locked_at.is_not(None),
                        DocumentJob.locked_at <= stale_before,
                    ),
                ),
            )
            .with_for_update(skip_locked=True)
        ).scalars().all()

        for expired in exhausted:
            _accumulate_attempt_duration(expired, now)
            expired.finished_at = now
            expired.status = "failed"
            expired.locked_at = None
            expired.locked_by = None
            expired.last_error = "Maximum attempts exhausted."
            expired.updated_at = now

            document = db.execute(
                select(Document).where(
                    Document.id == expired.document_id,
                    Document.organization_id == expired.organization_id,
                )
            ).scalar_one_or_none()

            if document is not None and document.status != "ready":
                document.status = "failed"

        db.flush()

        statement = (
            select(DocumentJob)
            .where(
                DocumentJob.attempts < DocumentJob.max_attempts,
                or_(
                    and_(
                        DocumentJob.status == "pending",
                        DocumentJob.available_at <= now,
                    ),
                    and_(
                        DocumentJob.status == "processing",
                        DocumentJob.locked_at.is_not(None),
                        DocumentJob.locked_at <= stale_before,
                    ),
                ),
            )
            .order_by(
                DocumentJob.available_at.asc(),
                DocumentJob.created_at.asc(),
            )
            .with_for_update(skip_locked=True)
            .limit(1)
        )

        job = db.execute(statement).scalar_one_or_none()

        if job is None:
            db.commit()
            return None

        if job.status == "processing":
            _accumulate_attempt_duration(job, now)

        job.status = "processing"
        job.attempt_started_at = now
        job.finished_at = None
        job.attempts += 1
        job.locked_at = now
        job.locked_by = worker_id
        job.updated_at = now

        result = {
            "id": job.id,
            "document_id": job.document_id,
            "organization_id": job.organization_id,
            "attempts": job.attempts,
            "max_attempts": job.max_attempts,
        }

        db.commit()
        return result


def mark_job_completed(
    session_factory: Any,
    job_id: uuid.UUID,
    worker_id: str,
) -> bool:
    """Complete a job only if this worker still owns its lease."""

    with session_factory() as db:
        job = db.execute(
            select(DocumentJob)
            .where(
                DocumentJob.id == job_id,
                DocumentJob.status == "processing",
                DocumentJob.locked_by == worker_id,
            )
            .with_for_update()
        ).scalar_one_or_none()

        if job is None:
            db.rollback()
            return False

        now = datetime.now(timezone.utc)
        _accumulate_attempt_duration(job, now)
        job.status = "completed"
        job.finished_at = now
        job.locked_at = None
        job.locked_by = None
        job.last_error = None
        job.updated_at = now

        db.commit()
        return True


def retry_or_fail_job(
    session_factory: Any,
    job: dict,
    worker_id: str,
    error: Exception,
) -> bool:
    """Schedule a retry with bounded exponential backoff."""

    now = datetime.now(timezone.utc)

    with session_factory() as db:
        record = db.execute(
            select(DocumentJob)
            .where(
                DocumentJob.id == job["id"],
                DocumentJob.status == "processing",
                DocumentJob.locked_by == worker_id,
            )
            .with_for_update()
        ).scalar_one_or_none()

        if record is None:
            db.rollback()
            logger.warning(
                "Worker %s no longer owns job %s.",
                worker_id,
                job["id"],
            )
            return False

        _accumulate_attempt_duration(record, now)

        # Store the exception class, not its raw message, to avoid
        # accidentally persisting API keys or other sensitive details.
        record.last_error = type(error).__name__
        record.locked_at = None
        record.locked_by = None
        record.updated_at = now

        if record.attempts >= record.max_attempts:
            record.status = "failed"
            record.finished_at = now

            document = db.execute(
                select(Document).where(
                    Document.id == record.document_id,
                    Document.organization_id == record.organization_id,
                )
            ).scalar_one_or_none()

            if document is not None and document.status != "ready":
                document.status = "failed"
        else:
            delay = min(
                BASE_RETRY_DELAY_SECONDS * (2 ** (record.attempts - 1)),
                MAX_RETRY_DELAY_SECONDS,
            )
            record.status = "pending"
            record.finished_at = None
            record.available_at = now + timedelta(seconds=delay)

        db.commit()
        return True
