from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.document_job import DocumentJob
from app.models.worker_registry import WorkerRegistry

WORKER_STALE_TIMEOUT_SECONDS = 45

WORKER_STATUSES = ("running", "stopped")
JOB_STATUSES = ("pending", "processing", "completed", "failed")


def get_health_snapshot(db: Session) -> dict:
    """Return aggregate worker and background-job health statistics."""
    now = datetime.now(timezone.utc)
    stale_before = now - timedelta(
        seconds=WORKER_STALE_TIMEOUT_SECONDS
    )

    worker_counts = {
        "running": 0,
        "stale": 0,
        "stopped": 0,
    }

    worker_rows = db.execute(
        select(
            WorkerRegistry.status,
            func.count(WorkerRegistry.worker_id),
        ).group_by(WorkerRegistry.status)
    ).all()

    for status, count in worker_rows:
        if status == "stopped":
            worker_counts["stopped"] = count
        elif status == "running":
            worker_counts["running"] = count

    stale_count = db.execute(
        select(func.count(WorkerRegistry.worker_id)).where(
            WorkerRegistry.status == "running",
            WorkerRegistry.last_heartbeat_at < stale_before,
        )
    ).scalar_one()

    worker_counts["stale"] = stale_count
    worker_counts["running"] -= stale_count

    job_counts = {status: 0 for status in JOB_STATUSES}

    job_rows = db.execute(
        select(
            DocumentJob.status,
            func.count(DocumentJob.id),
        ).group_by(DocumentJob.status)
    ).all()

    for status, count in job_rows:
        if status in job_counts:
            job_counts[status] = count

    return {
        "workers": worker_counts,
        "jobs": job_counts,
        "worker_stale_after_seconds": WORKER_STALE_TIMEOUT_SECONDS,
        "checked_at": now.isoformat(),
    }
