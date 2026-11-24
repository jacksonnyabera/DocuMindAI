import uuid

import pytest

from app.services.context_service import assemble_context


@pytest.fixture
def sample_results():
    document_id = str(uuid.uuid4())

    return [
        {
            "document_id": document_id,
            "filename": "company_policy.pdf",
            "page_number": 1,
            "content": "Employees are entitled to annual leave.",
            "similarity_score": 0.90,
        },
        {
            "document_id": document_id,
            "filename": "company_policy.pdf",
            "page_number": 1,
            "content": "  Employees are entitled to annual leave.  ",
            "similarity_score": 0.85,
        },
        {
            "document_id": document_id,
            "filename": "company_policy.pdf",
            "page_number": 2,
            "content": "Employees must submit leave requests in advance.",
            "similarity_score": 0.82,
        },
        {
            "document_id": document_id,
            "filename": "company_policy.pdf",
            "page_number": 3,
            "content": "The office has a parking facility.",
            "similarity_score": 0.20,
        },
    ]


def test_assemble_context_removes_exact_duplicates(sample_results):
    result = assemble_context(
        search_results=sample_results,
        min_similarity=0.30,
    )

    assert len(result["evidence"]) == 2


def test_assemble_context_preserves_distinct_evidence(sample_results):
    result = assemble_context(
        search_results=sample_results,
        min_similarity=0.30,
    )

    contents = [item["content"] for item in result["evidence"]]

    assert "Employees are entitled to annual leave." in contents
    assert "Employees must submit leave requests in advance." in contents


def test_assemble_context_preserves_source_references(sample_results):
    result = assemble_context(
        search_results=sample_results,
        min_similarity=0.30,
    )

    first = result["evidence"][0]

    assert first["document_id"] == sample_results[0]["document_id"]
    assert first["filename"] == "company_policy.pdf"
    assert first["page_number"] == 1


def test_assemble_context_excludes_low_relevance_results(sample_results):
    result = assemble_context(
        search_results=sample_results,
        min_similarity=0.30,
    )

    assert all(
        item["similarity_score"] >= 0.30
        for item in result["evidence"]
    )


def test_assemble_context_returns_combined_context(sample_results):
    result = assemble_context(
        search_results=sample_results,
        min_similarity=0.30,
    )

    assert isinstance(result["context"], str)
    assert "annual leave" in result["context"]
    assert "submit leave requests" in result["context"]


def test_assemble_context_rejects_invalid_threshold(sample_results):
    with pytest.raises(ValueError):
        assemble_context(
            search_results=sample_results,
            min_similarity=1.5,
        )


def test_assemble_context_handles_empty_results():
    result = assemble_context(search_results=[])

    assert result["evidence"] == []
    assert result["context"] == ""
