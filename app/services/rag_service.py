
import uuid

from app.embeddings.base import EmbeddingProvider
from app.llm.base import LLMProvider
from app.services.context_service import assemble_context
from app.services.search_service import search_documents


def generate_rag_answer(
    db,
    organization_id: uuid.UUID,
    question: str,
    embedding_provider: EmbeddingProvider,
    llm_provider: LLMProvider,
    limit: int = 5,
    min_similarity: float = 0.30,
) -> dict:
    """
    Retrieve relevant evidence and generate an answer grounded in it.
    """

    search_results = search_documents(
        db=db,
        organization_id=organization_id,
        question=question,
        embedding_provider=embedding_provider,
        limit=limit,
    )

    assembled = assemble_context(
        search_results=search_results,
        min_similarity=min_similarity,
    )

    evidence = assembled["evidence"]

    # Never ask the LLM to answer without relevant evidence.
    if not evidence:
        return {
            "answer": (
                "I couldn't find enough relevant information "
                "in your uploaded documents to answer this question."
            ),
            "sources": [],
        }

    answer = llm_provider.generate_answer(
        question=question,
        context=assembled["context"],
    )

    sources = [
        {
            "document_id": item["document_id"],
            "filename": item["filename"],
            "page_number": item["page_number"],
            "similarity_score": item["similarity_score"],
        }
        for item in evidence
    ]

    return {
        "answer": answer,
        "sources": sources,
    }
