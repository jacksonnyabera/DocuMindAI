from sentence_transformers import SentenceTransformer


class SentenceTransformerEmbeddingProvider:
    """
    Real semantic embedding provider using Sentence Transformers.

    Uses a multilingual model that produces normalized 384-dimensional
    vectors suitable for cosine similarity search.
    """

    MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

    def __init__(
        self,
        model_name: str = MODEL_NAME,
        device: str | None = None,
        batch_size: int = 32,
    ) -> None:
        if not isinstance(batch_size, int) or isinstance(batch_size, bool):
            raise ValueError("Batch size must be an integer.")

        if batch_size < 1:
            raise ValueError("Batch size must be at least 1.")

        self.batch_size = batch_size

        self.model = SentenceTransformer(
            model_name,
            device=device,
        )

        dimensions = self.model.get_sentence_embedding_dimension()

        if dimensions != 384:
            raise ValueError(
                f"Expected 384 embedding dimensions, got {dimensions}."
            )

        self._dimensions = dimensions

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not isinstance(texts, list):
            raise TypeError("Texts must be a list.")

        if not texts:
            return []

        for text in texts:
            if not isinstance(text, str):
                raise TypeError("Every document must be a string.")

            if not text.strip():
                raise ValueError("Document text cannot be empty.")

        embeddings = self.model.encode(
            texts,
            batch_size=self.batch_size,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )

        return embeddings.tolist()

    def embed_query(self, text: str) -> list[float]:
        if not isinstance(text, str):
            raise TypeError("Query must be a string.")

        if not text.strip():
            raise ValueError("Query cannot be empty.")

        embedding = self.model.encode(
            text,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )

        return embedding.tolist()
