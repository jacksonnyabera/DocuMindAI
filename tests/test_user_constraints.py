
import uuid

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_engine
from app.models.organization import Organization
from app.models.user import User


@pytest.fixture
def db_session():
    engine = get_engine()
    connection = engine.connect()
    transaction = connection.begin()

    db = Session(
        bind=connection,
        join_transaction_mode="create_savepoint",
        expire_on_commit=False,
    )

    yield db

    db.close()
    transaction.rollback()
    connection.close()


def test_email_is_globally_unique_across_organizations(db_session):
    organization_a = Organization(name="Email Test Company A")
    organization_b = Organization(name="Email Test Company B")

    db_session.add_all([organization_a, organization_b])
    db_session.flush()

    user_a = User(
        organization_id=organization_a.id,
        email="Jackson@example.com",
        full_name="Test User A",
        password_hash="test-hash",
        role="owner",
    )

    db_session.add(user_a)
    db_session.flush()

    user_b = User(
        organization_id=organization_b.id,
        email=" jackson@example.com ",
        full_name="Test User B",
        password_hash="test-hash",
        role="owner",
    )

    db_session.add(user_b)

    with pytest.raises(IntegrityError):
        db_session.flush()

    db_session.rollback()
