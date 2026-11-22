
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ChatRequest(BaseModel):
    """Validated request for document-grounded chat."""

    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1, max_length=2000)
    limit: int = Field(default=5, ge=1, le=20)

    @field_validator("question")
    @classmethod
    def clean_question(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Question cannot be empty.")

        return value


class ChatSource(BaseModel):
    """A document reference supporting an answer."""

    document_id: UUID
    filename: str
    page_number: int
    similarity_score: float = Field(ge=0.0, le=1.0)


class ChatResponse(BaseModel):
    """Answer and its supporting document references."""

    answer: str
    sources: list[ChatSource]
