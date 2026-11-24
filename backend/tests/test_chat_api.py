
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.api.routes import chat as chat_routes
from app.db.session import get_db, get_engine
from app.main import app
from app.models.organization import Organization
from app.models.user import User


@pytest.fixture
def chat_api_context():
    engine = get_engine()
    connection = engine.connect()
    transaction = connection.begin()

    db = Session(
        bind=connection,
        join_transaction_mode="create_savepoint",
        expire_on_commit=False,
    )

    organization = Organization(name="Chat API Test Company")
    db.add(organization)
    db.flush()

    user = User(
        organization_id=organization.id,
        email=f"{uuid.uuid4()}@example.com",
        full_name="Chat API Test User",
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


def test_chat_uses_authenticated_organization(
    chat_api_context,
    monkeypatch,
):
    user = chat_api_context["user"]
    client = chat_api_context["client"]

    captured = {}

    def fake_generate_rag_answer(**kwargs):
        captured.update(kwargs)

        return {
            "answer": "Employees receive 21 days of annual leave.",
            "sources": [
                {
                    "document_id": str(uuid.uuid4()),
                    "filename": "HR Policy.pdf",
                    "page_number": 3,
                    "similarity_score": 0.87,
                }
            ],
        }

    monkeypatch.setattr(
        chat_routes,
        "get_embedding_provider",
        lambda: object(),
    )

    monkeypatch.setattr(
        chat_routes,
        "get_llm_provider",
        lambda: object(),
    )

    monkeypatch.setattr(
        chat_routes,
        "generate_rag_answer",
        fake_generate_rag_answer,
    )

    response = client.post(
        "/chat",
        json={
            "question": "How many annual leave days do employees receive?",
            "limit": 5,
        },
    )

    assert response.status_code == 200
    assert response.json()["answer"] == (
        "Employees receive 21 days of annual leave."
    )
    assert len(response.json()["sources"]) == 1

    assert captured["organization_id"] == user.organization_id
    assert captured["question"] == (
        "How many annual leave days do employees receive?"
    )
    assert captured["limit"] == 5


def test_chat_rejects_client_supplied_organization_id(
    chat_api_context,
):
    client = chat_api_context["client"]

    response = client.post(
        "/chat",
        json={
            "question": "What is our leave policy?",
            "organization_id": str(uuid.uuid4()),
        },
    )

    assert response.status_code == 422


def test_chat_rejects_invalid_limit(chat_api_context):
    client = chat_api_context["client"]

    response = client.post(
        "/chat",
        json={
            "question": "What is our leave policy?",
            "limit": 0,
        },
    )

    assert response.status_code == 422


def test_chat_rejects_empty_question(chat_api_context):
    client = chat_api_context["client"]

    response = client.post(
        "/chat",
        json={
            "question": "   ",
        },
    )

    assert response.status_code == 422


def test_chat_requires_authentication():
    client = TestClient(app)

    response = client.post(
        "/chat",
        json={
            "question": "What is our leave policy?",
        },
    )

    assert response.status_code == 401


def test_chat_hides_provider_configuration_errors(
    chat_api_context,
    monkeypatch,
):
    client = chat_api_context["client"]

    monkeypatch.setattr(
        chat_routes,
        "get_embedding_provider",
        lambda: object(),
    )

    def fail_provider():
        raise RuntimeError("Sensitive internal configuration detail")

    monkeypatch.setattr(
        chat_routes,
        "get_llm_provider",
        fail_provider,
    )

    response = client.post(
        "/chat",
        json={
            "question": "What is our leave policy?",
        },
    )

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "The chat service is temporarily unavailable."
    )
    assert "Sensitive internal configuration detail" not in response.text
