
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator


class SearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1, max_length=2000)
    limit: int = Field(default=5, ge=1, le=20)

    @field_validator("question")
    @classmethod
    def clean_question(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Search question cannot be empty.")

        return value


class SearchResult(BaseModel):
    document_id: UUID
    filename: str
    page_number: int
    content: str
    similarity_score: float = Field(ge=-1.0, le=1.0)


class SearchResponse(BaseModel):
    results: list[SearchResult]
    total_results: int
