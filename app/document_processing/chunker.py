def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 150) -> list[str]:
    """
    Split text into overlapping chunks.

    Args:
        text: Document text.
        chunk_size: Maximum characters per chunk.
        overlap: Number of characters shared between chunks.

    Returns:
        A list of text chunks.
    """

    if not isinstance(text, str):
        raise TypeError("text must be a string")

    if isinstance(chunk_size, bool) or not isinstance(chunk_size, int):
        raise TypeError("chunk_size must be an integer")

    if isinstance(overlap, bool) or not isinstance(overlap, int):
        raise TypeError("overlap must be an integer")

    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")

    if overlap < 0:
        raise ValueError("overlap cannot be negative")

    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    if not text.strip():
        return []

    chunks = []
    step = chunk_size - overlap

    for start in range(0, len(text), step):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])

    return chunks