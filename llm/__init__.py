"""
Punto de entrada del paquete llm.

Uso:
    from llm import get_provider
    provider = get_provider("claude")   # o "deepseek" / "mock"
"""

from .base import LLMProvider, LLMResponse


def get_provider(name: str, api_key: str = None, model: str = None) -> LLMProvider:
    """
    Factory: devuelve una instancia lista para usar del proveedor pedido.

    name: "claude" | "deepseek" | "gemini" | "mock"
    """
    name = name.lower().strip()

    if name == "claude":
        from .claude_adapter import ClaudeProvider
        return ClaudeProvider(api_key=api_key, model=model or "claude-sonnet-5")

    if name == "deepseek":
        from .deepseek_adapter import DeepSeekProvider
        return DeepSeekProvider(api_key=api_key, model=model or "deepseek-chat")

    if name == "gemini":
        from .gemini_adapter import GeminiProvider
        return GeminiProvider(api_key=api_key, model=model or "gemini-2.5-flash")

    if name == "mock":
        from .mock_provider import MockProvider
        return MockProvider()

    raise ValueError(
        f"Proveedor '{name}' no reconocido. Usa 'claude', 'deepseek', 'gemini' o 'mock'."
    )


__all__ = ["LLMProvider", "LLMResponse", "get_provider"]
