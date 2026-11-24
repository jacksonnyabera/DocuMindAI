
import pytest

from app.embeddings.fake import FakeEmbeddingProvider


def test_embedding_has_expected_dimensions():
    provider = FakeEmbeddingProvider(dimensions=16)

    embedding = provider.embed_query("DocuMind AI")

    assert len(embedding) == 16


def test_embedding_values_are_floats():
    provider = FakeEmbeddingProvider()

    embedding = provider.embed_query("Document processing")

    assert all(isinstance(value, float) for value in embedding)


def test_same_text_produces_same_embedding():
    provider = FakeEmbeddingProvider()

    first = provider.embed_query("Artificial intelligence")
    second = provider.embed_query("Artificial intelligence")

    assert first == second


def test_document_embeddings_preserve_input_count():
    provider = FakeEmbeddingProvider()

    embeddings = provider.embed_documents([
        "First document",
        "Second document",
        "Third document",
    ])

    assert len(embeddings) == 3


def test_empty_query_is_rejected():
    provider = FakeEmbeddingProvider()

    with pytest.raises(ValueError):
        provider.embed_query("   ")


def test_invalid_dimensions_are_rejected():
    with pytest.raises(ValueError):
        FakeEmbeddingProvider(dimensions=0)


def test_non_integer_dimensions_are_rejected():
    with pytest.raises(ValueError):
        FakeEmbeddingProvider(dimensions=2.5)


def test_non_string_query_is_rejected():
    provider = FakeEmbeddingProvider()

    with pytest.raises(TypeError):
        provider.embed_query(123)
