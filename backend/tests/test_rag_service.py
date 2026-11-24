
import uuid

from app.services import rag_service


class FakeLLMProvider:
    def __init__(self):
        self.called = False
        self.received_question = None
        self.received_context = None

    def generate_answer(self, question, context):
        self.called = True
        self.received_question = question
        self.received_context = context

        return "Customers can request refunds within 30 days."


def test_rag_service_generates_answer_from_evidence(monkeypatch):
    document_id = str(uuid.uuid4())
    organization_id = uuid.uuid4()

    search_results = [
        {
            "document_id": document_id,
            "filename": "refund_policy.pdf",
            "page_number": 2,
            "content": "Customers can request refunds within 30 days.",
            "similarity_score": 0.85,
        }
    ]

    def fake_search_documents(**kwargs):
        assert kwargs["organization_id"] == organization_id
        assert kwargs["question"] == "What is the refund policy?"
        return search_results

    monkeypatch.setattr(
        rag_service,
        "search_documents",
        fake_search_documents,
    )

    llm = FakeLLMProvider()

    result = rag_service.generate_rag_answer(
        db=object(),
        organization_id=organization_id,
        question="What is the refund policy?",
        embedding_provider=object(),
        llm_provider=llm,
    )

    assert result["answer"] == (
        "Customers can request refunds within 30 days."
    )

    assert len(result["sources"]) == 1
    assert result["sources"][0]["document_id"] == document_id
    assert result["sources"][0]["filename"] == "refund_policy.pdf"
    assert result["sources"][0]["page_number"] == 2

    assert llm.called is True
    assert llm.received_question == "What is the refund policy?"
    assert "30 days" in llm.received_context


def test_rag_service_does_not_call_llm_without_evidence(monkeypatch):
    monkeypatch.setattr(
        rag_service,
        "search_documents",
        lambda **kwargs: [],
    )

    llm = FakeLLMProvider()

    result = rag_service.generate_rag_answer(
        db=object(),
        organization_id=uuid.uuid4(),
        question="What is the refund policy?",
        embedding_provider=object(),
        llm_provider=llm,
    )

    assert llm.called is False
    assert result["sources"] == []
    assert "couldn't find enough relevant information" in result["answer"]


def test_rag_service_does_not_call_llm_for_low_relevance(
    monkeypatch,
):
    monkeypatch.setattr(
        rag_service,
        "search_documents",
        lambda **kwargs: [
            {
                "document_id": str(uuid.uuid4()),
                "filename": "unrelated.pdf",
                "page_number": 1,
                "content": "This document discusses gardening.",
                "similarity_score": 0.10,
            }
        ],
    )

    llm = FakeLLMProvider()

    result = rag_service.generate_rag_answer(
        db=object(),
        organization_id=uuid.uuid4(),
        question="What is the refund policy?",
        embedding_provider=object(),
        llm_provider=llm,
    )

    assert llm.called is False
    assert result["sources"] == []
    assert "couldn't find enough relevant information" in result["answer"]
