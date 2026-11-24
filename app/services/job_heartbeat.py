import logging
import threading
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import update

from app.models.document_job import DocumentJob

logger = logging.getLogger("documind.worker.heartbeat")

HEARTBEAT_INTERVAL_SECONDS = 60


class JobLeaseHeartbeat:
    """Keep a processing job's lease alive while its worker is active."""

    def __init__(
        self,
        session_factory: Any,
        job_id: Any,
        worker_id: str,
        interval_seconds: int = HEARTBEAT_INTERVAL_SECONDS,
    ) -> None:
        if interval_seconds <= 0:
            raise ValueError("Heartbeat interval must be greater than zero.")

        self.session_factory = session_factory
        self.job_id = job_id
        self.worker_id = worker_id
        self.interval_seconds = interval_seconds

        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._lease_lost = threading.Event()

    @property
    def lease_lost(self) -> bool:
        return self._lease_lost.is_set()

    def renew(self) -> bool:
        """Renew only if this worker still owns the processing job."""
        now = datetime.now(timezone.utc)

        try:
            with self.session_factory() as db:
                result = db.execute(
                    update(DocumentJob)
                    .where(
                        DocumentJob.id == self.job_id,
                        DocumentJob.status == "processing",
                        DocumentJob.locked_by == self.worker_id,
                    )
                    .values(
                        locked_at=now,
                        updated_at=now,
                    )
                )
                db.commit()

                renewed = result.rowcount == 1

            if not renewed:
                self._lease_lost.set()
                logger.warning(
                    "Worker %s no longer owns job %s; lease renewal stopped.",
                    self.worker_id,
                    self.job_id,
                )

            return renewed

        except Exception:
            logger.exception(
                "Could not renew lease for job %s.",
                self.job_id,
            )
            return False

    def _heartbeat_loop(self) -> None:
        while not self._stop_event.wait(self.interval_seconds):
            if not self.renew():
                # Do not continue sending updates after ownership is lost.
                if self.lease_lost:
                    return

    def __enter__(self) -> "JobLeaseHeartbeat":
        self._thread = threading.Thread(
            target=self._heartbeat_loop,
            name=f"job-heartbeat-{self.job_id}",
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
                    "Heartbeat thread did not stop cleanly for job %s.",
                    self.job_id,
                )
