
import hashlib
import re
import uuid


def _normalize_content(content: str) -> str:
    """Normalize text for deterministic duplicate detection."""
    return re.sub(r"\s+", " ", content).strip().casefold()


def _content_hash(content: str) -> str:
    """Generate a SHA-256 hash for normalized content."""
    normalized = _normalize_content(content)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def assemble_context(
    search_results: list[dict],
    min_similarity: float = 0.30,
) -> dict:
    """
    Filter and assemble retrieved document chunks into LLM-ready context.

    Higher-ranked duplicate chunks are retained first.
    Original source references are preserved.
    """

    if (
        isinstance(min_similarity, bool)
        or not isinstance(min_similarity, (int, float))
        or not 0.0 <= min_similarity <= 1.0
    ):
        raise ValueError("Similarity threshold must be between 0 and 1.")

    if not isinstance(search_results, list):
        raise ValueError("Search results must be a list.")

    evidence = []
    seen_hashes = set()

    # Search results are already ranked by similarity.
    for result in search_results:
        if not isinstance(result, dict):
            raise ValueError("Every search result must be a dictionary.")

        content = result.get("content")
        score = result.get("similarity_score")

        if not isinstance(content, str) or not content.strip():
            raise ValueError("Search result content must be a non-empty string.")

        if (
            isinstance(score, bool)
            or not isinstance(score, (int, float))
        ):
            raise ValueError("Similarity score must be numeric.")

        if not 0.0 <= score <= 1.0:
            raise ValueError("Similarity score must be between 0 and 1.")

        if score < min_similarity:
            continue

        document_id = result.get("document_id")
        filename = result.get("filename")
        page_number = result.get("page_number")

        try:
            document_id = str(uuid.UUID(str(document_id)))
        except (ValueError, TypeError, AttributeError):
            raise ValueError("Search result contains an invalid document ID.")

        if not isinstance(filename, str) or not filename.strip():
            raise ValueError("Search result filename must be non-empty.")

        if (
            isinstance(page_number, bool)
            or not isinstance(page_number, int)
            or page_number < 1
        ):
            raise ValueError("Page number must be a positive integer.")

        content = content.strip()
        content_hash = _content_hash(content)

        if content_hash in seen_hashes:
            continue

        seen_hashes.add(content_hash)

        evidence.append(
            {
                "document_id": document_id,
                "filename": filename,
                "page_number": page_number,
                "content": content,
                "similarity_score": float(score),
            }
        )

    context_parts = []

    for index, item in enumerate(evidence, start=1):
        context_parts.append(
            f"[Source {index}: {item['filename']}, "
            f"page {item['page_number']}]\n"
            f"{item['content']}"
        )

    return {
        "evidence": evidence,
        "context": "\n\n".join(context_parts),
    }
