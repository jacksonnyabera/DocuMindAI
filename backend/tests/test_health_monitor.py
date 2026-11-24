import uuid
from datetime import datetime, timedelta, timezone

from app.models.document import Document
from app.models.document_job import DocumentJob
from app.models.worker_registry import WorkerRegistry
from app.services.health_monitor import get_health_snapshot


def test_health_snapshot_counts_worker_states(db_context):
    db = db_context["db"]
    now = datetime.now(timezone.utc)

    db.add_all([
        WorkerRegistry(
            worker_id=f"active-{uuid.uuid4().hex}",
            hostname="worker-active",
            status="running",
            last_heartbeat_at=now,
        ),
        WorkerRegistry(
            worker_id=f"stale-{uuid.uuid4().hex}",
            hostname="worker-stale",
            status="running",
            last_heartbeat_at=now - timedelta(minutes=5),
        ),
        WorkerRegistry(
            worker_id=f"stopped-{uuid.uuid4().hex}",
            hostname="worker-stopped",
            status="stopped",
            last_heartbeat_at=now,
        ),
    ])
    db.flush()

    snapshot = get_health_snapshot(db)

    assert snapshot["workers"]["running"] == 1
    assert snapshot["workers"]["stale"] == 1
    assert snapshot["workers"]["stopped"] == 1


def test_health_snapshot_counts_job_states(db_context):
    db = db_context["db"]
    organization = db_context["organization"]
    user = db_context["user"]

    baseline = get_health_snapshot(db)["jobs"]

    statuses = ("pending", "processing", "completed", "failed")

    for status in statuses:
        document = Document(
            organization_id=organization.id,
            uploaded_by=user.id,
            filename=f"health-test-{uuid.uuid4().hex}.pdf",
            file_type="application/pdf",
            storage_path=f"health-tests/{uuid.uuid4().hex}.pdf",
        )
        db.add(document)
        db.flush()

        db.add(
            DocumentJob(
                organization_id=organization.id,
                document_id=document.id,
                status=status,
            )
        )

    db.flush()

    snapshot = get_health_snapshot(db)

    for status in statuses:
        assert snapshot["jobs"][status] == baseline[status] + 1


def test_health_snapshot_returns_consistent_counts_when_no_records_are_added(db):
    first = get_health_snapshot(db)
    second = get_health_snapshot(db)

    assert first["workers"] == second["workers"]
    assert first["jobs"] == second["jobs"]

    assert set(first["workers"]) == {
        "running",
        "stale",
        "stopped",
    }

    assert set(first["jobs"]) == {
        "pending",
        "processing",
        "completed",
        "failed",
    }
