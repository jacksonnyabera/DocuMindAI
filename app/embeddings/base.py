
from typing import Protocol


class EmbeddingProvider(Protocol):
    """Interface that all embedding providers must implement."""

    @property
    def dimensions(self) -> int:
        """Return the number of values in each embedding."""
        ...

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple document chunks."""
        ...

    def embed_query(self, text: str) -> list[float]:
        """Generate an embedding for a search query."""
        ...
