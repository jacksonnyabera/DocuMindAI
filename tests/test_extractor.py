import pytest
import pymupdf

from app.document_processing.extractor import extract_pdf


@pytest.fixture
def sample_pdf(tmp_path):
    pdf_path = tmp_path / "sample.pdf"

    document = pymupdf.open()

    page1 = document.new_page()
    page1.insert_text((72, 72), "DocuMind AI test document")

    page2 = document.new_page()
    page2.insert_text((72, 72), "Second page of the document")

    document.save(pdf_path)
    document.close()

    return pdf_path


def test_extract_pdf(sample_pdf):
    result = extract_pdf(str(sample_pdf))

    assert result["filename"] == "sample.pdf"
    assert result["total_pages"] == 2
    assert len(result["pages"]) == 2


def test_extract_page_numbers(sample_pdf):
    result = extract_pdf(str(sample_pdf))

    assert result["pages"][0]["page_number"] == 1
    assert result["pages"][1]["page_number"] == 2


def test_extract_page_text(sample_pdf):
    result = extract_pdf(str(sample_pdf))

    assert "DocuMind AI test document" in result["pages"][0]["text"]
    assert "Second page of the document" in result["pages"][1]["text"]


def test_missing_pdf():
    with pytest.raises(FileNotFoundError):
        extract_pdf("missing.pdf")


def test_invalid_file_type(tmp_path):
    file_path = tmp_path / "document.txt"
    file_path.write_text("This is not a PDF")

    with pytest.raises(ValueError):
        extract_pdf(str(file_path))


def test_invalid_pdf_content(tmp_path):
    file_path = tmp_path / "broken.pdf"
    file_path.write_text("This is not a real PDF")

    with pytest.raises(ValueError):
        extract_pdf(str(file_path))


def test_empty_pdf(tmp_path):
    file_path = tmp_path / "empty.pdf"

    document = pymupdf.open()
    document.new_page()
    document.save(file_path)
    document.close()

    with pytest.raises(ValueError, match="OCR"):
        extract_pdf(str(file_path))


def test_extract_pdf_accepts_exactly_100_pages(tmp_path, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "max_pdf_pages", 100)

    pdf_path = tmp_path / "100_pages.pdf"
    document = pymupdf.open()

    for _ in range(100):
        page = document.new_page()
        page.insert_text((72, 72), "Test page content")

    document.save(pdf_path)
    document.close()

    result = extract_pdf(str(pdf_path))

    assert result["total_pages"] == 100


def test_extract_pdf_rejects_101_pages(tmp_path, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "max_pdf_pages", 100)

    pdf_path = tmp_path / "101_pages.pdf"
    document = pymupdf.open()

    for _ in range(101):
        page = document.new_page()
        page.insert_text((72, 72), "Test page content")

    document.save(pdf_path)
    document.close()

    with pytest.raises(ValueError, match="maximum allowed page count"):
        extract_pdf(str(pdf_path))

def test_extract_pdf_accepts_text_at_limit(sample_pdf, monkeypatch):
    from app.core.config import settings

    result = extract_pdf(str(sample_pdf))
    text_length = sum(len(page["text"]) for page in result["pages"])

    monkeypatch.setattr(settings, "max_pdf_text_chars", text_length)

    result = extract_pdf(str(sample_pdf))

    assert result["total_pages"] == 2


def test_extract_pdf_rejects_text_exceeding_limit(
    sample_pdf,
    monkeypatch,
):
    from app.core.config import settings

    monkeypatch.setattr(settings, "max_pdf_text_chars", 10)

    with pytest.raises(ValueError, match="maximum allowed extracted text"):
        extract_pdf(str(sample_pdf))
