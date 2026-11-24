
"""add pgvector embeddings

Revision ID: 03cd34eb26a2
Revises: 561fecdf58c9
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = "03cd34eb26a2"
down_revision: Union[str, Sequence[str], None] = "561fecdf58c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add native 384-dimensional vector storage."""

    # Ensure the PostgreSQL pgvector extension exists.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Keep the existing JSONB embedding column during migration.
    op.add_column(
        "document_chunks",
        sa.Column(
            "embedding_vector",
            Vector(384),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Remove the new vector column."""

    op.drop_column(
        "document_chunks",
        "embedding_vector",
    )
