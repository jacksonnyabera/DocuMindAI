
from functools import lru_cache

from app.core.config import settings
from app.llm.base import LLMProvider
from app.llm.gemini_provider import GeminiProvider


@lru_cache(maxsize=1)
def get_llm_provider() -> LLMProvider:
    """Return the configured language model provider."""

    provider_name = settings.llm_provider.strip().lower()

    if provider_name == "gemini":
        if not settings.gemini_api_key.get_secret_value().strip():
            raise RuntimeError("The LLM provider is not configured.")

        return GeminiProvider(
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
        )

    raise RuntimeError("The configured LLM provider is not supported.")
