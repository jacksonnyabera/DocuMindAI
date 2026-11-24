import uuid

import pytest
from sqlalchemy.orm import Session

from app.db.session import get_engine
from app.embeddings.fake import FakeEmbeddingProvider
from app.models.document import Document
from app.models.organization import Organization
from app.models.user import User
from app.models.document_chunk import DocumentChunk
from app.services import ingestion_service


@pytest.fixture
def db_context():
    """
    Use the development PostgreSQL database inside an outer
    transaction. Each test rolls back its database changes.
    """

    engine = get_engine()
    connection = engine.connect()
    transaction = connection.begin()

    db = Session(
        bind=connection,
        join_transaction_mode="create_savepoint",
        expire_on_commit=False,
    )

    organization = Organization(name="Ingestion Test Company")

    db.add(organization)
    db.flush()

    user = User(
        organization_id=organization.id,
        email=f"{uuid.uuid4()}@example.com",
        full_name="Test User",
        password_hash="test-password-hash",
        role="member",
    )

    db.add(user)
    db.flush()

    document = Document(
        organization_id=organization.id,
        uploaded_by=user.id,
        filename="test.pdf",
        file_type="application/pdf",
        storage_path="test-files/test.pdf",
        status="pending",
    )

    db.add(document)
    db.flush()

    db.commit()


    yield {
        "db": db,
        "organization": organization,
        "document": document,
    }

    db.close()
    transaction.rollback()
    connection.close()


def fake_processed_pdf():
    return {
        "filename": "test.pdf",
        "total_pages": 2,
        "total_chunks": 2,
        "chunks": [
            {
                "filename": "test.pdf",
                "page_number": 1,
                "chunk_index": 0,
                "text": "Artificial intelligence processes documents.",
            },
            {
                "filename": "test.pdf",
                "page_number": 2,
                "chunk_index": 0,
                "text": "Document retrieval uses embeddings.",
            },
        ],
    }


def test_successful_document_ingestion(
    db_context,
    monkeypatch,
):
    db = db_context["db"]
    document = db_context["document"]
    organization = db_context["organization"]

    monkeypatch.setattr(
        ingestion_service,
        "process_pdf",
        lambda path: fake_processed_pdf(),
    )

    result = ingestion_service.ingest_document(
        db=db,
        document_id=document.id,
        organization_id=organization.id,
        embedding_provider=FakeEmbeddingProvider(dimensions=384),
    )

    assert result["status"] == "ready"
    assert result["total_pages"] == 2
    assert result["total_chunks"] == 2

    saved_chunks = (
        db.query(DocumentChunk)
        .filter(
            DocumentChunk.document_id == document.id,
            DocumentChunk.organization_id == organization.id,
        )
        .all()
    )

    assert len(saved_chunks) == 2
    assert saved_chunks[0].embedding_vector is not None
    assert len(saved_chunks[0].embedding_vector) == 384
    assert saved_chunks[0].embedding is None
    assert saved_chunks[0].page_number == 1


def test_missing_document_is_rejected(
    db_context,
):
    db = db_context["db"]
    organization = db_context["organization"]

    with pytest.raises(LookupError):
        ingestion_service.ingest_document(
            db=db,
            document_id=uuid.uuid4(),
            organization_id=organization.id,
            embedding_provider=FakeEmbeddingProvider(),
        )


def test_other_organization_cannot_ingest_document(
    db_context,
):
    db = db_context["db"]
    document = db_context["document"]

    other_organization = Organization(
        name="Another Test Company",
    )

    db.add(other_organization)
    db.flush()

    with pytest.raises(LookupError):
        ingestion_service.ingest_document(
            db=db,
            document_id=document.id,
            organization_id=other_organization.id,
            embedding_provider=FakeEmbeddingProvider(),
        )


def test_invalid_embedding_rolls_back_ingestion(
    db_context,
    monkeypatch,
):
    db = db_context["db"]
    document = db_context["document"]
    organization = db_context["organization"]

    monkeypatch.setattr(
        ingestion_service,
        "process_pdf",
        lambda path: fake_processed_pdf(),
    )

    class InvalidEmbeddingProvider:
        dimensions = 16

        def embed_documents(self, texts):
            return [[1.0, 2.0] for _ in texts]

        def embed_query(self, text):
            return [1.0, 2.0]

    with pytest.raises(ValueError):
        ingestion_service.ingest_document(
            db=db,
            document_id=document.id,
            organization_id=organization.id,
            embedding_provider=InvalidEmbeddingProvider(),
        )

    db.expire_all()

    refreshed_document = db.get(Document, document.id)

    assert refreshed_document.status == "failed"

    saved_chunks = (
        db.query(DocumentChunk)
        .filter(
            DocumentChunk.document_id == document.id,
            DocumentChunk.organization_id == organization.id,
        )
        .all()
    )

    assert saved_chunks == []


def test_oversized_pdf_fails_without_generating_embeddings(
    db_context,
    monkeypatch,
):
    db = db_context["db"]
    document = db_context["document"]
    organization = db_context["organization"]

    monkeypatch.setattr(
        ingestion_service,
        "process_pdf",
        lambda path: (_ for _ in ()).throw(
            ValueError("PDF exceeds the maximum allowed page count of 100 pages.")
        ),
    )

    class TrackingEmbeddingProvider:
        dimensions = 384

        def embed_documents(self, texts):
            raise AssertionError(
                "Embeddings must not be generated for oversized PDFs."
            )

        def embed_query(self, text):
            raise NotImplementedError

    with pytest.raises(ValueError, match="maximum allowed page count"):
        ingestion_service.ingest_document(
            db=db,
            document_id=document.id,
            organization_id=organization.id,
            embedding_provider=TrackingEmbeddingProvider(),
        )

    db.expire_all()

    refreshed_document = db.get(Document, document.id)

    assert refreshed_document.status == "failed"

    saved_chunks = (
        db.query(DocumentChunk)
        .filter(
            DocumentChunk.document_id == document.id,
            DocumentChunk.organization_id == organization.id,
        )
        .all()
    )

    assert saved_chunks == []
