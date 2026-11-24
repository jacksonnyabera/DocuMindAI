from uuid import uuid4

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
def admin_api_context():
    engine = get_engine()
    connection = engine.connect()
    transaction = connection.begin()

    db = Session(
        bind=connection,
        join_transaction_mode="create_savepoint",
        expire_on_commit=False,
    )

    organization = Organization(name="Admin API Test Company")
    db.add(organization)
    db.flush()

    user = User(
        organization_id=organization.id,
        email=f"{uuid4()}@example.com",
        full_name="Admin API Test User",
        password_hash="test-password",
        role="owner",
    )
    db.add(user)
    db.commit()

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    client = TestClient(app)

    yield {
        "client": client,
        "db": db,
        "user": user,
    }

    app.dependency_overrides.clear()
    db.close()
    transaction.rollback()
    connection.close()


def test_operations_dashboard_requires_authentication(admin_api_context):
    response = admin_api_context["client"].get("/admin/operations")
    assert response.status_code == 401


def test_organization_owner_is_not_automatically_platform_admin(
    admin_api_context,
    monkeypatch,
):
    user = admin_api_context["user"]
    app.dependency_overrides[get_current_user] = lambda: user
    monkeypatch.setattr(settings, "platform_admin_emails", "")

    response = admin_api_context["client"].get("/admin/operations")
    assert response.status_code == 403


def test_allowlisted_platform_admin_can_view_operations(
    admin_api_context,
    monkeypatch,
):
    user = admin_api_context["user"]
    app.dependency_overrides[get_current_user] = lambda: user
    monkeypatch.setattr(
        settings,
        "platform_admin_emails",
        f"other@example.com, {user.email.upper()}",
    )

    response = admin_api_context["client"].get("/admin/operations")

    assert response.status_code == 200
    payload = response.json()

    assert "health" in payload
    assert "metrics" in payload
    assert "stuck_jobs" in payload
    assert "workers" in payload
    assert "recent_jobs" in payload
    assert payload["stuck_jobs"]["lease_timeout_seconds"] == 3600

    serialized = response.text.lower()
    assert "password_hash" not in serialized
    assert "last_error" not in serialized
