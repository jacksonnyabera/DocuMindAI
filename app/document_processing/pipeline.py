from app.document_processing.extractor import extract_pdf
from app.document_processing.cleaner import clean_text
from app.document_processing.chunker import chunk_text


def process_pdf(
    file_path: str,
    chunk_size: int = 1000,
    overlap: int = 150,
) -> dict:
    """
    Extract, clean, and chunk a PDF while preserving source metadata.
    """

    document = extract_pdf(file_path)

    processed_chunks = []

    for page in document["pages"]:
        cleaned_text = clean_text(page["text"])

        if not cleaned_text:
            continue

        page_chunks = chunk_text(
            cleaned_text,
            chunk_size=chunk_size,
            overlap=overlap,
        )

        for chunk_index, chunk in enumerate(page_chunks):
            processed_chunks.append({
                "filename": document["filename"],
                "page_number": page["page_number"],
                "chunk_index": chunk_index,
                "text": chunk,
            })

    return {
        "filename": document["filename"],
        "total_pages": document["total_pages"],
        "total_chunks": len(processed_chunks),
        "chunks": processed_chunks,
    }