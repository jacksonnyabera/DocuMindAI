
from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Common interface for all language model providers."""

    @abstractmethod
    def generate_answer(self, question: str, context: str) -> str:
        """Generate an answer using the supplied question and evidence."""
        raise NotImplementedError
