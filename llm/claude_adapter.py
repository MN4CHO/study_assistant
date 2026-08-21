"""
Adaptador para Claude (Anthropic API).

Requiere: pip install anthropic
Requiere variable de entorno: ANTHROPIC_API_KEY
"""

import base64
from pathlib import Path

from .base import LLMProvider, LLMResponse, call_with_retry

try:
    import anthropic
except ImportError:
    anthropic = None


class ClaudeProvider(LLMProvider):

    def __init__(self, api_key: str, model: str = "claude-sonnet-5"):
        if anthropic is None:
            raise ImportError(
                "Falta instalar el SDK de Anthropic: pip install anthropic"
            )
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    @property
    def supports_vision(self) -> bool:
        return True

    def generate_text(self, system_prompt: str, user_prompt: str,
                       max_tokens: int = 2000) -> LLMResponse:
        message = call_with_retry(lambda: self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        ))
        return LLMResponse(
            text=message.content[0].text,
            model=self.model,
            input_tokens=message.usage.input_tokens,
            output_tokens=message.usage.output_tokens,
        )

    def generate_from_image(self, system_prompt: str, user_prompt: str,
                             image_path: str, max_tokens: int = 2000) -> LLMResponse:
        image_bytes = Path(image_path).read_bytes()
        image_b64 = base64.standard_b64encode(image_bytes).decode("utf-8")
        media_type = _guess_media_type(image_path)

        message = call_with_retry(lambda: self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_b64,
                        },
                    },
                    {"type": "text", "text": user_prompt},
                ],
            }],
        ))
        return LLMResponse(
            text=message.content[0].text,
            model=self.model,
            input_tokens=message.usage.input_tokens,
            output_tokens=message.usage.output_tokens,
        )


def _guess_media_type(path: str) -> str:
    ext = Path(path).suffix.lower()
    return {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }.get(ext, "image/png")
