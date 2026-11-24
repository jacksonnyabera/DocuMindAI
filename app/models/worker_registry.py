import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class WorkerRegistry(Base):
    """Tracks worker process identity and liveness."""

    __tablename__ = "worker_registry"

    __table_args__ = (
        CheckConstraint(
            "status IN ('running', 'stopped')",
            name="ck_worker_registry_status",
        ),
        Index("ix_worker_registry_last_heartbeat_at", "last_heartbeat_at"),
        Index("ix_worker_registry_status", "status"),
    )

    worker_id: Mapped[str] = mapped_column(
        String(100),
        primary_key=True,
    )

    hostname: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="running",
        server_default="running",
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    last_heartbeat_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    stopped_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    current_job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_jobs.id", ondelete="SET NULL"),
        nullable=True,
    )
