
"""Enforce globally unique normalized user emails."""

from alembic import op


# revision identifiers
revision = "2d33dccc297c"
down_revision = "03cd34eb26a2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Prevent duplicate email identities across organizations."""

    op.execute(
        """
        CREATE UNIQUE INDEX uq_users_email_lower
        ON users (lower(trim(email)));
        """
    )


def downgrade() -> None:
    """Remove the global email uniqueness constraint."""

    op.execute(
        "DROP INDEX uq_users_email_lower;"
    )
