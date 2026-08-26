"""
Adaptador para Gemini (Google Gen AI SDK).

Requiere: pip install google-genai
Requiere variable de entorno: GEMINI_API_KEY
(se obtiene gratis en https://aistudio.google.com/apikey)

Nota: los modelos "Flash" tienen capa gratuita (con limite de solicitudes
por minuto); los modelos "Pro" son solo de pago. Por eso el default aqui
es un modelo Flash.
"""

from pathlib import Path

from .base import LLMProvider, LLMResponse, call_with_retry

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None


class GeminiProvider(LLMProvider):

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        if genai is None:
            raise ImportError(
                "Falta instalar el SDK de Google: pip install google-genai"
            )
        self.client = genai.Client(api_key=api_key)
        self.model = model

    @property
    def supports_vision(self) -> bool:
        # Los modelos Flash y Pro de Gemini soportan imagenes de forma nativa.
        return True

    def generate_text(self, system_prompt: str, user_prompt: str,
                       max_tokens: int = 2000) -> LLMResponse:
        response = call_with_retry(lambda: self.client.models.generate_content(
            model=self.model,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                # Los modelos Gemini "piensan" antes de responder, y esos tokens
                # de razonamiento se descuentan del mismo max_output_tokens (no
                # todos los modelos permiten desactivar el thinking). Por eso
                # pedimos mas margen del que ocuparia solo el texto visible, para
                # que la respuesta no se corte a mitad de camino.
                max_output_tokens=max(max_tokens, 4000),
            ),
        ))
        usage = response.usage_metadata
        return LLMResponse(
            text=response.text,
            model=self.model,
            input_tokens=getattr(usage, "prompt_token_count", 0) or 0,
            output_tokens=getattr(usage, "candidates_token_count", 0) or 0,
        )

    def generate_from_image(self, system_prompt: str, user_prompt: str,
                             image_path: str, max_tokens: int = 2000) -> LLMResponse:
        image_bytes = Path(image_path).read_bytes()
        mime_type = _guess_mime_type(image_path)

        image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)

        response = call_with_retry(lambda: self.client.models.generate_content(
            model=self.model,
            contents=[image_part, user_prompt],
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                max_output_tokens=max(max_tokens, 4000),
            ),
        ))
        usage = response.usage_metadata
        return LLMResponse(
            text=response.text,
            model=self.model,
            input_tokens=getattr(usage, "prompt_token_count", 0) or 0,
            output_tokens=getattr(usage, "candidates_token_count", 0) or 0,
        )


def _guess_mime_type(path: str) -> str:
    ext = Path(path).suffix.lower()
    return {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }.get(ext, "image/png")
