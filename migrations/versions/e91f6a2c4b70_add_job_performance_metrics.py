"""add job performance metrics

Revision ID: e91f6a2c4b70
Revises: c84d1e7a6b20
"""

from alembic import op
import sqlalchemy as sa


revision = "e91f6a2c4b70"
down_revision = "c84d1e7a6b20"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "document_jobs",
        sa.Column(
            "attempt_started_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    op.add_column(
        "document_jobs",
        sa.Column(
            "finished_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    op.add_column(
        "document_jobs",
        sa.Column(
            "processing_duration_ms",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )

    # Best-effort timestamps for jobs that existed before this migration.
    op.execute("""
        UPDATE document_jobs
        SET attempt_started_at = locked_at
        WHERE status = 'processing'
          AND locked_at IS NOT NULL
    """)

    op.execute("""
        UPDATE document_jobs
        SET finished_at = updated_at
        WHERE status IN ('completed', 'failed')
    """)


def downgrade() -> None:
    op.drop_column("document_jobs", "processing_duration_ms")
    op.drop_column("document_jobs", "finished_at")
    op.drop_column("document_jobs", "attempt_started_at")