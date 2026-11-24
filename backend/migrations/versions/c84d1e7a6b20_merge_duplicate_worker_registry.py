"""Merge duplicate worker process registry into original registry.

Revision ID: c84d1e7a6b20
Revises: b71c4e8a2d90
"""

from alembic import op


revision = "c84d1e7a6b20"
down_revision = "b71c4e8a2d90"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Preserve records from the temporary duplicate table.
    op.execute(
        """
        INSERT INTO worker_registry (
            worker_id,
            hostname,
            status,
            started_at,
            last_heartbeat_at,
            stopped_at,
            current_job_id
        )
        SELECT
            worker_id,
            hostname,
            status,
            started_at,
            last_heartbeat_at,
            stopped_at,
            current_job_id
        FROM worker_processes
        ON CONFLICT (worker_id) DO UPDATE SET
            hostname = EXCLUDED.hostname,
            status = EXCLUDED.status,
            started_at = LEAST(
                worker_registry.started_at,
                EXCLUDED.started_at
            ),
            last_heartbeat_at = GREATEST(
                worker_registry.last_heartbeat_at,
                EXCLUDED.last_heartbeat_at
            ),
            stopped_at = EXCLUDED.stopped_at,
            current_job_id = COALESCE(
                EXCLUDED.current_job_id,
                worker_registry.current_job_id
            )
        """
    )

    op.drop_table("worker_processes")


def downgrade() -> None:
    # Recreate the duplicate table empty; the original registry is untouched.
    op.create_table(
        "worker_processes",
        op.inline_literal("worker_id") if False else
        __import__("sqlalchemy").Column(
            "worker_id",
            __import__("sqlalchemy").String(length=128),
            primary_key=True,
        ),
        __import__("sqlalchemy").Column(
            "hostname",
            __import__("sqlalchemy").String(length=255),
            nullable=False,
        ),
        __import__("sqlalchemy").Column(
            "status",
            __import__("sqlalchemy").String(length=20),
            nullable=False,
        ),
        __import__("sqlalchemy").Column(
            "started_at",
            __import__("sqlalchemy").DateTime(timezone=True),
            server_default=__import__("sqlalchemy").text("now()"),
            nullable=False,
        ),
        __import__("sqlalchemy").Column(
            "last_heartbeat_at",
            __import__("sqlalchemy").DateTime(timezone=True),
            server_default=__import__("sqlalchemy").text("now()"),
            nullable=False,
        ),
        __import__("sqlalchemy").Column(
            "stopped_at",
            __import__("sqlalchemy").DateTime(timezone=True),
            nullable=True,
        ),
        __import__("sqlalchemy").Column(
            "current_job_id",
            __import__("sqlalchemy").UUID(),
            __import__("sqlalchemy").ForeignKey(
                "document_jobs.id",
                ondelete="SET NULL",
            ),
            nullable=True,
        ),
        __import__("sqlalchemy").CheckConstraint(
            "status IN ('running', 'stopped')",
            name="ck_worker_processes_status",
        ),
    )
    op.create_index(
        "ix_worker_processes_status_heartbeat",
        "worker_processes",
        ["status", "last_heartbeat_at"],
    )
