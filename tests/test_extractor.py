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