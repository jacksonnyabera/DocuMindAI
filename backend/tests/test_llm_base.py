
import pytest

from app.llm.base import LLMProvider


def test_llm_provider_cannot_be_instantiated_directly():
    with pytest.raises(TypeError):
        LLMProvider()


def test_concrete_provider_can_generate_answer():
    class FakeLLMProvider(LLMProvider):
        def generate_answer(self, question: str, context: str) -> str:
            return f"Answer based on: {context}"

    provider = FakeLLMProvider()

    result = provider.generate_answer(
        question="What is the refund policy?",
        context="Customers can request refunds within 30 days.",
    )

    assert result == "Answer based on: Customers can request refunds within 30 days."


def test_provider_must_implement_generate_answer():
    class IncompleteProvider(LLMProvider):
        pass

    with pytest.raises(TypeError):
        IncompleteProvider()
