from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

from app.services.job_queue import retry_or_fail_job


def make_job(attempts=1, max_attempts=3):
    return SimpleNamespace(
        id=uuid4(),
        document_id=uuid4(),
        organization_id=uuid4(),
        status="processing",
        attempts=attempts,
        max_attempts=max_attempts,
        available_at=datetime.now(timezone.utc),
        locked_at=datetime.now(timezone.utc),
        locked_by="worker-test",
        last_error=None,
        updated_at=None,
    )


def make_session(job):
    session_factory = MagicMock()
    db = session_factory.return_value.__enter__.return_value

    result = MagicMock()
    result.scalar_one_or_none.return_value = job
    db.execute.return_value = result

    return session_factory, db


def test_failed_job_is_returned_to_pending_for_retry():
    job_record = make_job(attempts=1)
    session_factory, db = make_session(job_record)

    before = datetime.now(timezone.utc)

    result = retry_or_fail_job(
        session_factory=session_factory,
        job={
            "id": job_record.id,
            "document_id": job_record.document_id,
            "organization_id": job_record.organization_id,
            "attempts": 1,
            "max_attempts": 3,
        },
        worker_id="worker-test",
        error=ValueError("Temporary processing failure"),
    )

    after = datetime.now(timezone.utc)

    assert result is True
    assert job_record.status == "pending"
    assert job_record.locked_at is None
    assert job_record.locked_by is None
    assert job_record.last_error == "ValueError"
    assert before + timedelta(seconds=29) <= job_record.available_at
    assert job_record.available_at <= after + timedelta(seconds=31)
    db.commit.assert_called_once()


def test_retry_delay_increases_with_attempt_number():
    for attempts, expected_delay in [(2, 60), (3, 120)]:
        job_record = make_job(attempts=attempts, max_attempts=5)
        session_factory, _ = make_session(job_record)

        before = datetime.now(timezone.utc)

        retry_or_fail_job(
            session_factory=session_factory,
            job={
                "id": job_record.id,
                "document_id": job_record.document_id,
                "organization_id": job_record.organization_id,
                "attempts": attempts,
                "max_attempts": 5,
            },
            worker_id="worker-test",
            error=RuntimeError("Temporary failure"),
        )

        expected = before + timedelta(seconds=expected_delay)

        assert job_record.status == "pending"
        assert abs((job_record.available_at - expected).total_seconds()) < 2


def test_worker_cannot_retry_job_after_lease_ownership_is_lost():
    session_factory, db = make_session(None)

    result = retry_or_fail_job(
        session_factory=session_factory,
        job={
            "id": uuid4(),
            "document_id": uuid4(),
            "organization_id": uuid4(),
            "attempts": 1,
            "max_attempts": 3,
        },
        worker_id="old-worker",
        error=RuntimeError("Processing failed"),
    )

    assert result is False
    db.commit.assert_not_called()


def test_retry_state_clears_previous_lock_information():
    job_record = make_job(attempts=2)
    session_factory, _ = make_session(job_record)

    retry_or_fail_job(
        session_factory=session_factory,
        job={
            "id": job_record.id,
            "document_id": job_record.document_id,
            "organization_id": job_record.organization_id,
            "attempts": 2,
            "max_attempts": 3,
        },
        worker_id="worker-test",
        error=RuntimeError("Temporary failure"),
    )

    assert job_record.status == "pending"
    assert job_record.locked_at is None
    assert job_record.locked_by is None
