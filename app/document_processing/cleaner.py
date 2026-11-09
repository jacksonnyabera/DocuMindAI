import re
import unicodedata


def clean_text(text: str) -> str:
    """
    Clean extracted document text while preserving paragraph structure.
    """

    if not isinstance(text, str):
        raise TypeError("text must be a string")

    if not text.strip():
        return ""

    # Normalize Unicode characters.
    text = unicodedata.normalize("NFKC", text)

    # Remove null bytes and unwanted control characters.
    text = "".join(
        character
        for character in text
        if character in "\n\t" or unicodedata.category(character) != "Cc"
    )

    # Normalize Windows and old Mac line endings.
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Replace tabs with spaces.
    text = text.replace("\t", " ")

    # Remove repeated spaces within lines.
    text = re.sub(r"[ ]{2,}", " ", text)

    # Remove spaces at the beginning and end of lines.
    lines = [line.strip() for line in text.split("\n")]

    # Preserve paragraph boundaries while removing excessive blank lines.
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()