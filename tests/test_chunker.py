
import pytest

from app.document_processing.chunker import chunk_text


def test_empty_document():
    assert chunk_text("") == []


def test_whitespace_document():
    assert chunk_text("   \n  ") == []


def test_short_document():
    text = "Hello, AI engineering!"
    assert chunk_text(text, 100, 10) == [text]


def test_long_document():
    text = "A" * 250
    chunks = chunk_text(text, 100, 20)

    assert len(chunks) == 4
    assert all(len(chunk) <= 100 for chunk in chunks)


def test_overlap():
    text = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    chunks = chunk_text(text, 10, 3)

    assert chunks[0][-3:] == chunks[1][:3]


def test_text_preservation():
    text = "ABCDEFGHIJKLMNOPQRSTUVWXYZ" * 10
    chunks = chunk_text(text, 30, 5)

    reconstructed = chunks[0] + "".join(
        chunk[5:] for chunk in chunks[1:]
    )

    assert reconstructed == text


@pytest.mark.parametrize(
    "chunk_size, overlap",
    [
        (0, 0),
        (-1, 0),
        (10, 10),
        (10, 11),
        (10, -1),
    ],
)
def test_invalid_parameters(chunk_size, overlap):
    with pytest.raises(ValueError):
        chunk_text("Hello world", chunk_size, overlap)


def test_invalid_text_type():
    with pytest.raises(TypeError):
        chunk_text(123)


def test_invalid_chunk_size_type():
    with pytest.raises(TypeError):
        chunk_text("Hello", 10.5, 2)


def test_invalid_overlap_type():
    with pytest.raises(TypeError):
        chunk_text("Hello", 10, 2.5)
