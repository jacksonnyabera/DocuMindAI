import logging
import socket
import threading
from datetime import datetime, timedelta, timezone
from typing import Any
import uuid

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert

from app.models.worker_registry import WorkerRegistry

logger = logging.getLogger("documind.worker.registry")

WORKER_HEARTBEAT_INTERVAL_SECONDS = 15
WORKER_STALE_AFTER_SECONDS = 45


def register_worker(
    session_factory: Any,
    worker_id: str,
    hostname: str,
) -> None:
    """Register a worker or refresh its existing registry entry."""

    now = datetime.now(timezone.utc)

    statement = insert(WorkerRegistry).values(
        worker_id=worker_id,
        hostname=hostname,
        status="running",
        started_at=now,
        last_heartbeat_at=now,
        stopped_at=None,
        current_job_id=None,
    )

    statement = statement.on_conflict_do_update(
        index_elements=[WorkerRegistry.worker_id],
        set_={
            "hostname": statement.excluded.hostname,
            "status": "running",
            "started_at": now,
            "last_heartbeat_at": now,
            "stopped_at": None,
            "current_job_id": None,
        },
    )

    with session_factory() as db:
        db.execute(statement)
        db.commit()


def heartbeat_worker(
    session_factory: Any,
    worker_id: str,
    current_job_id: uuid.UUID | None = None,
) -> bool:
    """Update liveness and the currently processed job."""

    now = datetime.now(timezone.utc)

    with session_factory() as db:
        result = db.execute(
            update(WorkerRegistry)
            .where(
                WorkerRegistry.worker_id == worker_id,
                WorkerRegistry.status == "running",
            )
            .values(
                last_heartbeat_at=now,
                current_job_id=current_job_id,
                stopped_at=None,
            )
        )
        db.commit()
        return result.rowcount == 1


def stop_worker(session_factory: Any, worker_id: str) -> bool:
    """Mark a worker as stopped during graceful shutdown."""

    now = datetime.now(timezone.utc)

    with session_factory() as db:
        result = db.execute(
            update(WorkerRegistry)
            .where(
                WorkerRegistry.worker_id == worker_id,
                WorkerRegistry.status == "running",
            )
            .values(
                status="stopped",
                stopped_at=now,
                last_heartbeat_at=now,
                current_job_id=None,
            )
        )
        db.commit()
        return result.rowcount == 1


def get_stale_worker_ids(
    session_factory: Any,
    stale_after_seconds: int = WORKER_STALE_AFTER_SECONDS,
) -> list[str]:
    """Find workers whose last heartbeat is older than the timeout."""

    if stale_after_seconds <= 0:
        raise ValueError("Stale timeout must be greater than zero.")

    cutoff = datetime.now(timezone.utc) - timedelta(
        seconds=stale_after_seconds
    )

    with session_factory() as db:
        return list(
            db.execute(
                select(WorkerRegistry.worker_id).where(
                    WorkerRegistry.status == "running",
                    WorkerRegistry.last_heartbeat_at < cutoff,
                )
            ).scalars().all()
        )


class WorkerProcessHeartbeat:
    """Maintain process liveness independently of job lease heartbeats."""

    def __init__(
        self,
        session_factory: Any,
        worker_id: str,
        hostname: str | None = None,
        interval_seconds: int = WORKER_HEARTBEAT_INTERVAL_SECONDS,
    ) -> None:
        if interval_seconds <= 0:
            raise ValueError("Heartbeat interval must be greater than zero.")

        self.session_factory = session_factory
        self.worker_id = worker_id
        self.hostname = hostname or socket.gethostname()
        self.interval_seconds = interval_seconds

        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._job_lock = threading.Lock()
        self._current_job_id: uuid.UUID | None = None

    def set_current_job(self, job_id: uuid.UUID | None) -> None:
        with self._job_lock:
            self._current_job_id = job_id

    def _heartbeat_loop(self) -> None:
        while not self._stop_event.wait(self.interval_seconds):
            with self._job_lock:
                current_job_id = self._current_job_id

            try:
                updated = heartbeat_worker(
                    self.session_factory,
                    self.worker_id,
                    current_job_id,
                )

                if not updated:
                    logger.warning(
                        "Worker registry entry is missing or stopped: %s",
                        self.worker_id,
                    )
                    return

            except Exception:
                logger.exception(
                    "Could not update process heartbeat for worker %s.",
                    self.worker_id,
                )

    def __enter__(self) -> "WorkerProcessHeartbeat":
        register_worker(
            self.session_factory,
            self.worker_id,
            self.hostname,
        )

        self._thread = threading.Thread(
            target=self._heartbeat_loop,
            name=f"worker-process-heartbeat-{self.worker_id}",
            daemon=True,
        )
        self._thread.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self._stop_event.set()

        if self._thread is not None:
            self._thread.join(timeout=self.interval_seconds + 5)

            if self._thread.is_alive():
                logger.error(
                    "Worker heartbeat thread did not stop cleanly: %s",
                    self.worker_id,
                )

        try:
            stop_worker(self.session_factory, self.worker_id)
        except Exception:
            logger.exception(
                "Could not mark worker %s as stopped.",
                self.worker_id,
            )
