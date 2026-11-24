
import uuid

import pytest
from sqlalchemy.orm import Session

from app.models.document import Document
from app.services import background_ingestion


def make_worker_session_factory(db_context):
    connection = db_context["connection"]

    def create_session():
        return Session(
            bind=connection,
            join_transaction_mode="create_savepoint",
            expire_on_commit=False,
        )

    return create_session


def test_provider_initialization_failure_marks_document_failed(
    db_context,
    monkeypatch,
):
    db = db_context["db"]
    document = db_context["document"]
    organization = db_context["organization"]

    monkeypatch.setattr(
        background_ingestion,
        "get_session_factory",
        lambda: make_worker_session_factory(db_context),
    )

    def fail_provider():
        raise RuntimeError("Embedding model initialization failed")

    monkeypatch.setattr(
        background_ingestion,
        "get_embedding_provider",
        fail_provider,
    )

    background_ingestion.process_document_in_background(
        document.id,
        organization.id,
    )

    db.expire_all()
    refreshed = db.get(Document, document.id)

    assert refreshed is not None
    assert refreshed.status == "failed"


def test_ingestion_failure_marks_document_failed(
    db_context,
    monkeypatch,
):
    db = db_context["db"]
    document = db_context["document"]
    organization = db_context["organization"]

    monkeypatch.setattr(
        background_ingestion,
        "get_session_factory",
        lambda: make_worker_session_factory(db_context),
    )

    monkeypatch.setattr(
        background_ingestion,
        "get_embedding_provider",
        lambda: object(),
    )

    def fail_ingestion(**kwargs):
        raise RuntimeError("Document ingestion failed")

    monkeypatch.setattr(
        background_ingestion,
        "ingest_document",
        fail_ingestion,
    )

    background_ingestion.process_document_in_background(
        document.id,
        organization.id,
    )

    db.expire_all()
    refreshed = db.get(Document, document.id)

    assert refreshed is not None
    assert refreshed.status == "failed"


def test_failure_does_not_overwrite_ready_document(
    db_context,
    monkeypatch,
):
    db = db_context["db"]
    document = db_context["document"]
    organization = db_context["organization"]

    document.status = "ready"
    db.commit()

    monkeypatch.setattr(
        background_ingestion,
        "get_session_factory",
        lambda: make_worker_session_factory(db_context),
    )

    def fail_provider():
        raise RuntimeError("Model initialization failed")

    monkeypatch.setattr(
        background_ingestion,
        "get_embedding_provider",
        fail_provider,
    )

    background_ingestion.process_document_in_background(
        document.id,
        organization.id,
    )

    db.expire_all()
    refreshed = db.get(Document, document.id)

    assert refreshed is not None
    assert refreshed.status == "ready"


def test_missing_document_does_not_crash_worker(
    db_context,
    monkeypatch,
):
    organization = db_context["organization"]

    monkeypatch.setattr(
        background_ingestion,
        "get_session_factory",
        lambda: make_worker_session_factory(db_context),
    )

    monkeypatch.setattr(
        background_ingestion,
        "get_embedding_provider",
        lambda: object(),
    )

    def fail_ingestion(**kwargs):
        raise LookupError("Document not found")

    monkeypatch.setattr(
        background_ingestion,
        "ingest_document",
        fail_ingestion,
    )

    background_ingestion.process_document_in_background(
        uuid.uuid4(),
        organization.id,
    )
