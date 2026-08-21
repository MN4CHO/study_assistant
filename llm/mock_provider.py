"""
Proveedor simulado, util para:
- Probar que el pipeline completo funciona sin gastar creditos de API.
- Desarrollo/depuracion rapida sin conexion a internet.

No usar este proveedor para la entrega final: los resultados no son
generados por un modelo real, son texto de relleno predecible.
"""

from .base import LLMProvider, LLMResponse


class MockProvider(LLMProvider):

    @property
    def supports_vision(self) -> bool:
        return True

    def generate_text(self, system_prompt: str, user_prompt: str,
                       max_tokens: int = 2000) -> LLMResponse:
        preview = user_prompt[:80].replace("\n", " ")
        text = f"[MOCK] Respuesta simulada para: '{preview}...'"

        return LLMResponse(
            text=text,
            model="mock-v0",
            input_tokens=len(user_prompt.split()),
            output_tokens=10,
        )

    def generate_from_image(self, system_prompt: str, user_prompt: str,
                             image_path: str, max_tokens: int = 2000) -> LLMResponse:
        return LLMResponse(
            text=f"[MOCK] Transcripcion simulada de la imagen: {image_path}",
            model="mock-v0",
            input_tokens=0,
            output_tokens=10,
        )
