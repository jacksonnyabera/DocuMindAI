from functools import lru_cache

from app.embeddings.sentence_transformer import SentenceTransformerEmbeddingProvider

@lru_cache(maxsize=1)
def get_embedding_provider() -> SentenceTransformerEmbeddingProvider:
    """ Return one cached multilingual embedding provider per process.

    The model is loaded on the first call and reused for subsequent
    document ingestion and query embedding operations."""

    return SentenceTransformerEmbeddingProvider()
