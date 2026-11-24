
import uuid

import pytest
from sqlalchemy.orm import Session

from app.db.session import get_engine
from app.models.document import Document
from app.models.organization import Organization
from app.models.user import User


@pytest.fixture
def db_context():
    engine = get_engine()
    connection = engine.connect()
    transaction = connection.begin()

    db = Session(
        bind=connection,
        join_transaction_mode="create_savepoint",
        expire_on_commit=False,
    )

    organization = Organization(name="Background Test Company")
    db.add(organization)
    db.flush()

    user = User(
        organization_id=organization.id,
        email=f"{uuid.uuid4()}@example.com",
        full_name="Background Test User",
        password_hash="test-password-hash",
        role="member",
    )
    db.add(user)
    db.flush()

    document = Document(
        organization_id=organization.id,
        uploaded_by=user.id,
        filename="background-test.pdf",
        file_type="application/pdf",
        storage_path="test-files/background-test.pdf",
        status="pending",
    )
    db.add(document)
    db.flush()
    db.commit()

    yield {
        "db": db,
        "connection": connection,
        "organization": organization,
        "user": user,
        "document": document,
    }

    db.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def db(db_context):
    return db_context["db"]


@pytest.fixture
def document(db_context):
    return db_context["document"]


@pytest.fixture
def organization(db_context):
    return db_context["organization"]


@pytest.fixture
def user(db_context):
    return db_context["user"]
