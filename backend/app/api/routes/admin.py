from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.api.dependencies import require_platform_admin
from app.db.session import get_db
from app.models.document_job import DocumentJob
from app.models.user import User
from app.models.worker_registry import WorkerRegistry
from app.services.health_monitor import get_health_snapshot
from app.services.job_queue import JOB_LOCK_TIMEOUT_SECONDS


router = APIRouter(
    prefix="/admin",
    tags=["Platform Administration"],
)


@router.get("/operations")
def get_operations_dashboard(
    _: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
):
    """Return operational metrics without exposing customer document data."""

    now = datetime.now(timezone.utc)
    stale_before = now - timedelta(seconds=JOB_LOCK_TIMEOUT_SECONDS)

    health = get_health_snapshot(db)

    completed_count = (
        db.query(func.count(DocumentJob.id))
        .filter(DocumentJob.status == "completed")
        .scalar()
        or 0
    )
    failed_count = (
        db.query(func.count(DocumentJob.id))
        .filter(DocumentJob.status == "failed")
        .scalar()
        or 0
    )

    retry_count = (
        db.query(
            func.coalesce(
                func.sum(
                    case(
                        (
                            DocumentJob.attempts > 1,
                            DocumentJob.attempts - 1,
                        ),
                        else_=0,
                    )
                ),
                0,
            )
        ).scalar()
        or 0
    )

    average_duration_ms = (
        db.query(func.avg(DocumentJob.processing_duration_ms))
        .filter(
            DocumentJob.status.in_(("completed", "failed")),
            DocumentJob.processing_duration_ms > 0,
        )
        .scalar()
        or 0
    )

    total_duration_ms = (
        db.query(
            func.coalesce(
                func.sum(DocumentJob.processing_duration_ms),
                0,
            )
        ).scalar()
        or 0
    )

    terminal_count = completed_count + failed_count
    failure_rate_percent = (
        round((failed_count / terminal_count) * 100, 2)
        if terminal_count
        else 0.0
    )

    stuck_jobs_count = (
        db.query(func.count(DocumentJob.id))
        .filter(
            DocumentJob.status == "processing",
            DocumentJob.locked_at.isnot(None),
            DocumentJob.locked_at < stale_before,
        )
        .scalar()
        or 0
    )

    recent_jobs = (
        db.query(DocumentJob)
        .order_by(DocumentJob.updated_at.desc())
        .limit(20)
        .all()
    )

    workers = (
        db.query(WorkerRegistry)
        .order_by(WorkerRegistry.last_heartbeat_at.desc())
        .limit(100)
        .all()
    )

    return {
        "checked_at": now.isoformat(),
        "health": health,
        "metrics": {
            "completed_jobs": completed_count,
            "failed_jobs": failed_count,
            "terminal_jobs": terminal_count,
            "retry_attempts": int(retry_count),
            "failure_rate_percent": failure_rate_percent,
            "average_terminal_processing_duration_ms": round(
                float(average_duration_ms)
            ),
            "total_processing_duration_ms": int(total_duration_ms),
        },
        "stuck_jobs": {
            "count": stuck_jobs_count,
            "lease_timeout_seconds": JOB_LOCK_TIMEOUT_SECONDS,
        },
        "workers": [
            {
                "worker_id": worker.worker_id,
                "hostname": worker.hostname,
                "status": worker.status,
                "started_at": worker.started_at,
                "last_heartbeat_at": worker.last_heartbeat_at,
                "stopped_at": worker.stopped_at,
                "current_job_id": worker.current_job_id,
            }
            for worker in workers
        ],
        "recent_jobs": [
            {
                "job_id": str(job.id),
                "status": job.status,
                "attempts": job.attempts,
                "max_attempts": job.max_attempts,
                "processing_duration_ms": job.processing_duration_ms,
                "created_at": job.created_at,
                "updated_at": job.updated_at,
                "finished_at": job.finished_at,
            }
            for job in recent_jobs
        ],
    }
