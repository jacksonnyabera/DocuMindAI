import pymupdf

from app.document_processing.pipeline import process_pdf


def create_sample_pdf(path):
    document = pymupdf.open()

    page1 = document.new_page()
    page1.insert_text(
        (72, 72),
        "This is the first page of our DocuMind AI test document."
    )

    page2 = document.new_page()
    page2.insert_text(
        (72, 72),
        "This is the second page containing business information."
    )

    document.save(path)
    document.close()


def test_process_pdf(tmp_path):
    pdf_path = tmp_path / "business.pdf"
    create_sample_pdf(pdf_path)

    result = process_pdf(str(pdf_path))

    assert result["filename"] == "business.pdf"
    assert result["total_pages"] == 2
    assert result["total_chunks"] == 2


def test_chunks_preserve_page_numbers(tmp_path):
    pdf_path = tmp_path / "business.pdf"
    create_sample_pdf(pdf_path)

    result = process_pdf(str(pdf_path))

    assert result["chunks"][0]["page_number"] == 1
    assert result["chunks"][1]["page_number"] == 2


def test_chunks_preserve_source_filename(tmp_path):
    pdf_path = tmp_path / "business.pdf"
    create_sample_pdf(pdf_path)

    result = process_pdf(str(pdf_path))

    for chunk in result["chunks"]:
        assert chunk["filename"] == "business.pdf"


def test_chunk_content_is_not_empty(tmp_path):
    pdf_path = tmp_path / "business.pdf"
    create_sample_pdf(pdf_path)

    result = process_pdf(str(pdf_path))

    for chunk in result["chunks"]:
        assert chunk["text"].strip()


def test_custom_chunk_size(tmp_path):
    pdf_path = tmp_path / "business.pdf"
    create_sample_pdf(pdf_path)

    result = process_pdf(
        str(pdf_path),
        chunk_size=20,
        overlap=5,
    )

    assert result["total_chunks"] > 2

    for chunk in result["chunks"]:
        assert len(chunk["text"]) <= 20