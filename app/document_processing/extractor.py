from pathlib import Path

import pymupdf as fitz 
from app.core.config import settings


def extract_pdf(file_path: str) -> dict:
    """
    Extract text from a PDF, preserving individual page numbers.
    """

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {file_path}")

    if not path.is_file():
        raise ValueError("The supplied path must be a file")

    if path.suffix.lower() != ".pdf":
        raise ValueError("Only PDF files are supported")

    pages = []

    try:
        with fitz.open(path) as document:

            if document.is_encrypted:
                raise ValueError("Encrypted PDFs are not supported")

            if len(document) > settings.max_pdf_pages:
                raise ValueError(
                     f"PDF exceeds the maximum allowed page count "
                     f"of {settings.max_pdf_pages} pages."
                )

            if len(document) == 0:
                raise ValueError("The PDF contains no pages")
                

            for page_number, page in enumerate(document, start=1):
                text = page.get_text("text").strip()

                pages.append({
                    "page_number": page_number,
                    "text": text,
                })

    except fitz.FileDataError as exc:
        raise ValueError("The supplied file is not a valid PDF") from exc

    if not any(page["text"] for page in pages):
        raise ValueError(
            "No extractable text found. This PDF may require OCR."
        )

    return {
        "filename": path.name,
        "total_pages": len(pages),
        "pages": pages,
    }