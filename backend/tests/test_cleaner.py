import pytest

from app.document_processing.cleaner import clean_text


def test_empty_text():
    assert clean_text("") == ""


def test_whitespace_only():
    assert clean_text("   \n  \t ") == ""


def test_remove_extra_spaces():
    assert clean_text("Hello     world") == "Hello world"


def test_normalize_line_endings():
    assert clean_text("Hello\r\nWorld") == "Hello\nWorld"


def test_preserve_paragraphs():
    text = "First paragraph.\n\nSecond paragraph."

    assert clean_text(text) == text


def test_remove_excessive_blank_lines():
    text = "First paragraph.\n\n\n\nSecond paragraph."

    assert clean_text(text) == "First paragraph.\n\nSecond paragraph."


def test_remove_control_characters():
    text = "Hello\x00World"

    assert clean_text(text) == "HelloWorld"


def test_remove_leading_and_trailing_spaces():
    text = "   Hello world   "

    assert clean_text(text) == "Hello world"


def test_normalize_unicode():
    text = "ＡＩ"

    assert clean_text(text) == "AI"


def test_invalid_input():
    with pytest.raises(TypeError):
        clean_text(123)