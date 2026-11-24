"""Add worker process registry."""

from alembic import op
import sqlalchemy as sa


revision = "9a7c2e1b4d60"
down_revision = "df03ba86e311"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "worker_registry",
        sa.Column("worker_id", sa.String(length=100), nullable=False),
        sa.Column("hostname", sa.String(length=255), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="running",
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
        sa.Column("stopped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_job_id", sa.UUID(), nullable=True),
        sa.CheckConstraint(
            "status IN ('running', 'stopped')",
            name="ck_worker_registry_status",
        ),
        sa.ForeignKeyConstraint(
            ["current_job_id"],
            ["document_jobs.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("worker_id"),
    )

    op.create_index(
        "ix_worker_registry_last_heartbeat_at",
        "worker_registry",
        ["last_heartbeat_at"],
    )
    op.create_index(
        "ix_worker_registry_status",
        "worker_registry",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_worker_registry_status",
        table_name="worker_registry",
    )
    op.drop_index(
        "ix_worker_registry_last_heartbeat_at",
        table_name="worker_registry",
    )
    op.drop_table("worker_registry")
