from types import SimpleNamespace
from unittest.mock import MagicMock

from app.services.job_queue import retry_or_fail_job


def test_job_becomes_failed_after_maximum_attempts():
    job = SimpleNamespace(
        id="job-123",
        document_id="document-123",
        organization_id="org-123",
        status="processing",
        attempts=3,
        max_attempts=3,
        locked_at="locked",
        locked_by="worker-test",
        last_error=None,
        updated_at=None,
    )

    document = SimpleNamespace(status="processing")

    session_factory = MagicMock()
    db = session_factory.return_value.__enter__.return_value

    job_result = MagicMock()
    job_result.scalar_one_or_none.return_value = job

    document_result = MagicMock()
    document_result.scalar_one_or_none.return_value = document

    db.execute.side_effect = [job_result, document_result]

    result = retry_or_fail_job(
        session_factory=session_factory,
        job={
            "id": job.id,
            "document_id": job.document_id,
            "organization_id": job.organization_id,
            "attempts": 3,
            "max_attempts": 3,
        },
        worker_id="worker-test",
        error=RuntimeError("Permanent processing failure"),
    )

    assert result is True
    assert job.status == "failed"
    assert job.locked_at is None
    assert job.locked_by is None
    assert job.last_error == "RuntimeError"
    assert document.status == "failed"
    db.commit.assert_called_once()


def test_failed_job_does_not_overwrite_ready_document():
    job = SimpleNamespace(
        id="job-456",
        document_id="document-456",
        organization_id="org-456",
        status="processing",
        attempts=3,
        max_attempts=3,
        locked_at="locked",
        locked_by="worker-test",
        last_error=None,
        updated_at=None,
    )

    document = SimpleNamespace(status="ready")

    session_factory = MagicMock()
    db = session_factory.return_value.__enter__.return_value

    job_result = MagicMock()
    job_result.scalar_one_or_none.return_value = job

    document_result = MagicMock()
    document_result.scalar_one_or_none.return_value = document

    db.execute.side_effect = [job_result, document_result]

    result = retry_or_fail_job(
        session_factory=session_factory,
        job={
            "id": job.id,
            "document_id": job.document_id,
            "organization_id": job.organization_id,
            "attempts": 3,
            "max_attempts": 3,
        },
        worker_id="worker-test",
        error=RuntimeError("Late worker failure"),
    )

    assert result is True
    assert job.status == "failed"
    assert document.status == "ready"
    db.commit.assert_called_once()
