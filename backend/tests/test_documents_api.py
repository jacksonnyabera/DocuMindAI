import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.config import settings
from app.db.session import get_db, get_engine
from app.main import app
from app.models.organization import Organization
from app.models.user import User


@pytest.fixture
def api_context(tmp_path, monkeypatch):
    """Create an isolated API test environment using PostgreSQL."""

    monkeypatch.setattr(settings, "storage_dir", str(tmp_path))
    monkeypatch.setattr(settings, "max_upload_size", 1024)

    engine = get_engine()
    connection = engine.connect()
    transaction = connection.begin()

    db = Session(
        bind=connection,
        join_transaction_mode="create_savepoint",
        expire_on_commit=False,
    )

    organization = Organization(name="API Test Company")
    db.add(organization)
    db.flush()

    user = User(
        organization_id=organization.id,
        email=f"{uuid.uuid4()}@example.com",
        full_name="API Test User",
        password_hash="test-password-hash",
        role="member",
    )
    db.add(user)
    db.flush()
    db.commit()

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: user

    client = TestClient(app)

    yield {
        "client": client,
        "db": db,
        "user": user,
        "storage_dir": Path(tmp_path),
    }

    app.dependency_overrides.clear()
    db.close()
    transaction.rollback()
    connection.close()


def test_upload_valid_pdf(api_context):
    client = api_context["client"]

    response = client.post(
        "/documents/upload",
        files={
            "file": (
                "company-policy.pdf",
                b"%PDF-1.4\nExample PDF content",
                "application/pdf",
            )
        },
    )

    assert response.status_code == 201
    assert response.json()["filename"] == "company-policy.pdf"
    assert response.json()["status"] == "pending"

    saved_files = list(
        api_context["storage_dir"].rglob("*.pdf")
    )

    assert len(saved_files) == 1
    assert saved_files[0].read_bytes().startswith(b"%PDF-")


def test_upload_rejects_invalid_pdf_signature(api_context):
    client = api_context["client"]

    response = client.post(
        "/documents/upload",
        files={
            "file": (
                "fake.pdf",
                b"This is not a PDF",
                "application/pdf",
            )
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid PDF file signature."

    saved_files = list(
        api_context["storage_dir"].rglob("*.pdf")
    )

    assert saved_files == []


def test_upload_rejects_non_pdf_content_type(api_context):
    client = api_context["client"]

    response = client.post(
        "/documents/upload",
        files={
            "file": (
                "document.txt",
                b"Some text",
                "text/plain",
            )
        },
    )

    assert response.status_code == 415


def test_upload_rejects_file_over_size_limit(api_context):
    client = api_context["client"]

    response = client.post(
        "/documents/upload",
        files={
            "file": (
                "large.pdf",
                b"%PDF-1.4\n" + (b"A" * 2048),
                "application/pdf",
            )
        },
    )

    assert response.status_code == 413

    saved_files = list(
        api_context["storage_dir"].rglob("*.pdf")
    )

    assert saved_files == []
