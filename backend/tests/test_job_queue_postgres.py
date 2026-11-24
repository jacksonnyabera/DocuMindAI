from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, delete
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

import app.models
from app.core.config import settings
from app.db.base import Base
from app.models import Document, DocumentJob, Organization, User
from app.services.job_queue import (
    claim_next_job,
    mark_job_completed,
)


@pytest.fixture(scope="module")
def postgres_session_factory():
    source_url = make_url(str(settings.database_url))

    if not source_url.database:
        pytest.fail("Could not determine configured database name.")

    test_database = f"{source_url.database}_test"

    if not test_database.endswith("_test"):
        pytest.fail("Integration tests require a dedicated test database.")

    engine = create_engine(
        source_url.set(database=test_database),
        pool_size=5,
        max_overflow=2,
    )

    try:
        with engine.begin() as connection:
            database_name = connection.exec_driver_sql(
                "SELECT current_database()"
            ).scalar_one()

            if database_name != test_database:
                pytest.fail("Connected to an unexpected database.")

            connection.exec_driver_sql(
                "CREATE EXTENSION IF NOT EXISTS vector"
            )

        Base.metadata.create_all(engine)

        yield sessionmaker(
            bind=engine,
            expire_on_commit=False,
        )

    finally:
        engine.dispose()


def create_test_job(session_factory, *, attempts=0, max_attempts=3):
    organization = Organization(name=f"Queue Test {uuid4().hex[:8]}")
    user = None
    document = None
    job = None

    with session_factory() as db:
        db.add(organization)
        db.flush()

        user = User(
            organization_id=organization.id,
            email=f"{uuid4().hex}@example.test",
            full_name="Queue Integration Test",
            password_hash="test-only-hash",
            role="member",
        )
        db.add(user)
        db.flush()

        document = Document(
            organization_id=organization.id,
            uploaded_by=user.id,
            filename="queue-test.pdf",
            file_type="application/pdf",
            storage_path="integration-tests/queue-test.pdf",
            status="pending",
        )
        db.add(document)
        db.flush()

        job = DocumentJob(
            organization_id=organization.id,
            document_id=document.id,
            status="pending",
            attempts=attempts,
            max_attempts=max_attempts,
        )
        db.add(job)
        db.commit()

        return {
            "organization_id": organization.id,
            "user_id": user.id,
            "document_id": document.id,
            "job_id": job.id,
        }


def cleanup_test_records(session_factory, records):
    with session_factory() as db:
        db.execute(
            delete(DocumentJob).where(
                DocumentJob.id == records["job_id"]
            )
        )
        db.execute(
            delete(Document).where(
                Document.id == records["document_id"]
            )
        )
        db.execute(
            delete(User).where(
                User.id == records["user_id"]
            )
        )
        db.execute(
            delete(Organization).where(
                Organization.id == records["organization_id"]
            )
        )
        db.commit()


def test_two_workers_cannot_claim_the_same_job(postgres_session_factory):
    factory = postgres_session_factory
    records = create_test_job(factory)
    barrier = Barrier(2)

    def worker_claim(worker_id):
        barrier.wait(timeout=10)
        return claim_next_job(factory, worker_id)

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(worker_claim, "integration-worker-a"),
                executor.submit(worker_claim, "integration-worker-b"),
            ]
            results = [future.result(timeout=20) for future in futures]

        claimed_jobs = [result for result in results if result is not None]

        assert len(claimed_jobs) == 1
        assert claimed_jobs[0]["id"] == records["job_id"]

        with factory() as db:
            stored_job = db.get(DocumentJob, records["job_id"])

            assert stored_job.status == "processing"
            assert stored_job.attempts == 1
            assert stored_job.locked_by in {
                "integration-worker-a",
                "integration-worker-b",
            }

    finally:
        cleanup_test_records(factory, records)


def test_expired_job_can_be_reclaimed(postgres_session_factory):
    factory = postgres_session_factory
    records = create_test_job(factory, attempts=1)

    expired_time = datetime.now(timezone.utc) - timedelta(hours=2)

    try:
        with factory() as db:
            job = db.get(DocumentJob, records["job_id"])
            job.status = "processing"
            job.locked_at = expired_time
            job.locked_by = "crashed-worker"
            db.commit()

        reclaimed = claim_next_job(factory, "replacement-worker")

        assert reclaimed is not None
        assert reclaimed["id"] == records["job_id"]
        assert reclaimed["attempts"] == 2

        with factory() as db:
            job = db.get(DocumentJob, records["job_id"])

            assert job.status == "processing"
            assert job.locked_by == "replacement-worker"
            assert job.attempts == 2
            assert job.locked_at > expired_time

    finally:
        cleanup_test_records(factory, records)


def test_old_worker_cannot_complete_reclaimed_job(postgres_session_factory):
    factory = postgres_session_factory
    records = create_test_job(factory, attempts=1)

    try:
        with factory() as db:
            job = db.get(DocumentJob, records["job_id"])
            job.status = "processing"
            job.locked_at = (
                datetime.now(timezone.utc) - timedelta(hours=2)
            )
            job.locked_by = "old-worker"
            db.commit()

        reclaimed = claim_next_job(factory, "new-worker")

        assert reclaimed is not None

        old_worker_result = mark_job_completed(
            factory,
            records["job_id"],
            "old-worker",
        )

        assert old_worker_result is False

        new_worker_result = mark_job_completed(
            factory,
            records["job_id"],
            "new-worker",
        )

        assert new_worker_result is True

        with factory() as db:
            job = db.get(DocumentJob, records["job_id"])

            assert job.status == "completed"
            assert job.locked_by is None
            assert job.locked_at is None

    finally:
        cleanup_test_records(factory, records)
from datetime import datetime, timedelta, timezone

from app.services.job_queue import retry_or_fail_job


def test_completed_job_records_processing_duration(postgres_session_factory):
    factory = postgres_session_factory
    records = create_test_job(factory)
    worker_id = "metrics-completion-worker"

    try:
        started_at = datetime.now(timezone.utc) - timedelta(seconds=5)

        with factory() as db:
            job = db.get(DocumentJob, records["job_id"])
            job.status = "processing"
            job.locked_by = worker_id
            job.locked_at = started_at
            job.attempt_started_at = started_at
            db.commit()

        assert mark_job_completed(factory, records["job_id"], worker_id)

        with factory() as db:
            job = db.get(DocumentJob, records["job_id"])
            assert job.status == "completed"
            assert job.finished_at is not None
            assert job.attempt_started_at is None
            assert job.processing_duration_ms >= 5000
            assert job.locked_by is None
    finally:
        cleanup_test_records(factory, records)


def test_retry_accumulates_processing_time_without_finishing_job(
    postgres_session_factory,
):
    factory = postgres_session_factory
    records = create_test_job(factory, attempts=1, max_attempts=3)
    worker_id = "metrics-retry-worker"

    try:
        started_at = datetime.now(timezone.utc) - timedelta(seconds=4)

        with factory() as db:
            job = db.get(DocumentJob, records["job_id"])
            job.status = "processing"
            job.attempts = 1
            job.locked_by = worker_id
            job.locked_at = started_at
            job.attempt_started_at = started_at
            db.commit()

        result = retry_or_fail_job(
            factory,
            {"id": records["job_id"]},
            worker_id,
            RuntimeError("Temporary processing failure"),
        )
        assert result is True

        with factory() as db:
            job = db.get(DocumentJob, records["job_id"])
            assert job.status == "pending"
            assert job.finished_at is None
            assert job.attempt_started_at is None
            assert job.processing_duration_ms >= 4000
            assert job.available_at > datetime.now(timezone.utc)
            assert job.last_error == "RuntimeError"
    finally:
        cleanup_test_records(factory, records)


def test_terminal_failure_records_finished_at_and_duration(
    postgres_session_factory,
):
    factory = postgres_session_factory
    records = create_test_job(factory, attempts=2, max_attempts=3)
    worker_id = "metrics-failure-worker"

    try:
        started_at = datetime.now(timezone.utc) - timedelta(seconds=3)

        with factory() as db:
            job = db.get(DocumentJob, records["job_id"])
            job.status = "processing"
            job.attempts = 3
            job.locked_by = worker_id
            job.locked_at = started_at
            job.attempt_started_at = started_at
            db.commit()

        result = retry_or_fail_job(
            factory,
            {"id": records["job_id"]},
            worker_id,
            RuntimeError("Final processing failure"),
        )
        assert result is True

        with factory() as db:
            job = db.get(DocumentJob, records["job_id"])
            assert job.status == "failed"
            assert job.finished_at is not None
            assert job.attempt_started_at is None
            assert job.processing_duration_ms >= 3000
            assert job.locked_by is None
    finally:
        cleanup_test_records(factory, records)


def test_stale_job_reclaim_accumulates_abandoned_attempt_duration(
    postgres_session_factory,
):
    factory = postgres_session_factory
    records = create_test_job(factory, attempts=1, max_attempts=3)

    try:
        now = datetime.now(timezone.utc)
        original_started_at = now - timedelta(seconds=25)
        stale_lock_time = now - timedelta(hours=2)

        with factory() as db:
            job = db.get(DocumentJob, records["job_id"])
            job.status = "processing"
            job.attempts = 1
            job.locked_by = "crashed-worker"
            job.locked_at = stale_lock_time
            job.attempt_started_at = original_started_at
            db.commit()

        reclaimed = claim_next_job(factory, "replacement-worker")

        assert reclaimed is not None
        assert reclaimed["id"] == records["job_id"]
        assert reclaimed["attempts"] == 2

        with factory() as db:
            job = db.get(DocumentJob, records["job_id"])
            assert job.status == "processing"
            assert job.locked_by == "replacement-worker"
            assert job.attempts == 2
            assert job.processing_duration_ms >= 25000
            assert job.attempt_started_at >= original_started_at
            assert job.attempt_started_at > stale_lock_time
            assert job.finished_at is None
    finally:
        cleanup_test_records(factory, records)
