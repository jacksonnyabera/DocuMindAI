import uuid

import pytest
from sqlalchemy.orm import Session

from app.db.session import get_engine
from app.models.organization import Organization
from app.models.user import User
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.services.search_service import search_documents


class FixedEmbeddingProvider:
    """Return the same valid vector for every search question."""

    dimensions = 384

    def embed_query(self, text: str) -> list[float]:
        return [1.0] + [0.0] * 383

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[1.0] + [0.0] * 383 for _ in texts]


@pytest.fixture
def search_context():
    engine = get_engine()
    connection = engine.connect()
    transaction = connection.begin()

    db = Session(
        bind=connection,
        join_transaction_mode="create_savepoint",
        expire_on_commit=False,
    )

    organization_a = Organization(name="Company A")
    organization_b = Organization(name="Company B")

    db.add_all([organization_a, organization_b])
    db.flush()

    user_a = User(
        organization_id=organization_a.id,
        email=f"{uuid.uuid4()}@example.com",
        full_name="Company A User",
        password_hash="test-password",
        role="member",
    )

    user_b = User(
        organization_id=organization_b.id,
        email=f"{uuid.uuid4()}@example.com",
        full_name="Company B User",
        password_hash="test-password",
        role="member",
    )

    db.add_all([user_a, user_b])
    db.flush()

    document_a = Document(
        organization_id=organization_a.id,
        uploaded_by=user_a.id,
        filename="company-a.pdf",
        file_type="application/pdf",
        storage_path="company-a.pdf",
        status="ready",
    )

    document_b = Document(
        organization_id=organization_b.id,
        uploaded_by=user_b.id,
        filename="company-b.pdf",
        file_type="application/pdf",
        storage_path="company-b.pdf",
        status="ready",
    )

    pending_document = Document(
        organization_id=organization_a.id,
        uploaded_by=user_a.id,
        filename="pending.pdf",
        file_type="application/pdf",
        storage_path="pending.pdf",
        status="pending",
    )

    db.add_all([document_a, document_b, pending_document])
    db.flush()

    identical_vector = [1.0] + [0.0] * 383

    chunks = [
        DocumentChunk(
            organization_id=organization_a.id,
            document_id=document_a.id,
            page_number=1,
            chunk_index=0,
            content="Company A confidential information.",
            embedding_vector=identical_vector,
        ),
        DocumentChunk(
            organization_id=organization_b.id,
            document_id=document_b.id,
            page_number=1,
            chunk_index=0,
            content="Company B confidential information.",
            embedding_vector=identical_vector,
        ),
        DocumentChunk(
            organization_id=organization_a.id,
            document_id=pending_document.id,
            page_number=1,
            chunk_index=0,
            content="Incomplete document information.",
            embedding_vector=identical_vector,
        ),
    ]

    db.add_all(chunks)
    db.commit()

    yield {
        "db": db,
        "organization_a": organization_a,
        "organization_b": organization_b,
    }

    db.close()
    transaction.rollback()
    connection.close()


def test_search_isolates_organizations_and_excludes_pending_documents(
    search_context,
):
    db = search_context["db"]
    organization_a = search_context["organization_a"]

    results = search_documents(
        db=db,
        organization_id=organization_a.id,
        question="Find confidential information",
        embedding_provider=FixedEmbeddingProvider(),
        limit=5,
    )

    assert len(results) == 1

    assert results[0]["filename"] == "company-a.pdf"
    assert results[0]["content"] == "Company A confidential information."
    assert results[0]["similarity_score"] == pytest.approx(1.0)

    assert all(
        result["filename"] != "company-b.pdf"
        for result in results
    )

    assert all(
        result["filename"] != "pending.pdf"
        for result in results
    )
