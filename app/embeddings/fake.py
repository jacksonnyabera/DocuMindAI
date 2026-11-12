
import hashlib
import re

from app.embeddings.base import EmbeddingProvider


class FakeEmbeddingProvider(EmbeddingProvider):
    """
    Deterministic test provider.

    This generates artificial embeddings for testing the ingestion
    pipeline. It does not understand meaning and is not suitable
    for production semantic search.
    """

    def __init__(self, dimensions: int = 16) -> None:
        if not isinstance(dimensions, int) or isinstance(dimensions, bool):
            raise ValueError("Dimensions must be an integer.")

        if dimensions < 1:
            raise ValueError("Dimensions must be at least 1.")

        self._dimensions = dimensions

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not isinstance(texts, list):
            raise TypeError("Texts must be a list.")

        return [self.embed_query(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        if not isinstance(text, str):
            raise TypeError("Text must be a string.")

        if not text.strip():
            raise ValueError("Text cannot be empty.")

        vector = [0.0] * self.dimensions
        tokens = re.findall(r"\w+", text.casefold())

        for token in tokens:
            digest = hashlib.blake2b(
                token.encode("utf-8"),
                digest_size=8,
            ).digest()

            index = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0

            vector[index] += sign

        magnitude = sum(value * value for value in vector) ** 0.5

        if magnitude > 0:
            vector = [value / magnitude for value in vector]

        return vector
