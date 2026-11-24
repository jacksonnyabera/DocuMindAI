"""Add worker process registry.

Revision ID: b71c4e8a2d90
Revises: 9a7c2e1b4d60
Create Date: 2026-11-24
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "b71c4e8a2d90"
down_revision: Union[str, Sequence[str], None] = "9a7c2e1b4d60"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "worker_processes",
        sa.Column("worker_id", sa.String(length=128), nullable=False),
        sa.Column("hostname", sa.String(length=255), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "last_heartbeat_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "stopped_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "current_job_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.CheckConstraint(
            "status IN ('running', 'stopped')",
            name="ck_worker_processes_status",
        ),
        sa.ForeignKeyConstraint(
            ["current_job_id"],
            ["document_jobs.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("worker_id"),
    )

    op.create_index(
        "ix_worker_processes_status_heartbeat",
        "worker_processes",
        ["status", "last_heartbeat_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_worker_processes_status_heartbeat",
        table_name="worker_processes",
    )
    op.drop_table("worker_processes")
