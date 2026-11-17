
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.api.routes import search as search_routes
from app.db.session import get_db, get_engine
from app.main import app
from app.models.organization import Organization
from app.models.user import User


@pytest.fixture
def search_api_context():
    engine = get_engine()
    connection = engine.connect()
    transaction = connection.begin()

    db = Session(
        bind=connection,
        join_transaction_mode="create_savepoint",
        expire_on_commit=False,
    )

    organization = Organization(name="Search API Test Company")
    db.add(organization)
    db.flush()

    user = User(
        organization_id=organization.id,
        email=f"{uuid.uuid4()}@example.com",
        full_name="Search API Test User",
        password_hash="test-password",
        role="member",
    )

    db.add(user)
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
    }

    app.dependency_overrides.clear()
    db.close()
    transaction.rollback()
    connection.close()


def test_search_uses_authenticated_organization(
    search_api_context,
    monkeypatch,
):
    user = search_api_context["user"]
    client = search_api_context["client"]

    captured = {}

    def fake_search_documents(**kwargs):
        captured.update(kwargs)
        return []

    monkeypatch.setattr(
        search_routes,
        "get_embedding_provider",
        lambda: object(),
    )

    monkeypatch.setattr(
        search_routes,
        "search_documents",
        fake_search_documents,
    )

    response = client.post(
        "/search",
        json={
            "question": "Find company policies",
            "limit": 5,
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "results": [],
        "total_results": 0,
    }

    assert captured["organization_id"] == user.organization_id
    assert captured["question"] == "Find company policies"
    assert captured["limit"] == 5


def test_search_rejects_client_supplied_organization_id(
    search_api_context,
):
    client = search_api_context["client"]

    response = client.post(
        "/search",
        json={
            "question": "Find company policies",
            "organization_id": str(uuid.uuid4()),
        },
    )

    assert response.status_code == 422


def test_search_rejects_invalid_limit(search_api_context):
    client = search_api_context["client"]

    response = client.post(
        "/search",
        json={
            "question": "Find company policies",
            "limit": 0,
        },
    )

    assert response.status_code == 422


def test_search_requires_authentication():
    client = TestClient(app)

    response = client.post(
        "/search",
        json={
            "question": "Find company policies",
        },
    )

    assert response.status_code == 401
