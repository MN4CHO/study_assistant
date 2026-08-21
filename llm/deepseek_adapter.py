"""
Adaptador para DeepSeek.

DeepSeek expone una API compatible con el formato de OpenAI, asi que
usamos el SDK de openai apuntando a la base_url de DeepSeek.

Requiere: pip install openai
Requiere variable de entorno: DEEPSEEK_API_KEY
"""

import base64
from pathlib import Path

from .base import LLMProvider, LLMResponse, call_with_retry

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

DEEPSEEK_BASE_URL = "https://api.deepseek.com"


class DeepSeekProvider(LLMProvider):

    def __init__(self, api_key: str, model: str = "deepseek-chat"):
        if OpenAI is None:
            raise ImportError(
                "Falta instalar el SDK de OpenAI (usado para hablar con DeepSeek): "
                "pip install openai"
            )
        self.client = OpenAI(api_key=api_key, base_url=DEEPSEEK_BASE_URL)
        self.model = model

    @property
    def supports_vision(self) -> bool:
        # Solo los modelos de vision de DeepSeek soportan imagenes.
        # Ajusta este flag segun el modelo configurado.
        return "vision" in self.model.lower() or "vl" in self.model.lower()

    def generate_text(self, system_prompt: str, user_prompt: str,
                       max_tokens: int = 2000) -> LLMResponse:
        completion = call_with_retry(lambda: self.client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        ))
        usage = completion.usage
        return LLMResponse(
            text=completion.choices[0].message.content,
            model=self.model,
            input_tokens=getattr(usage, "prompt_tokens", 0),
            output_tokens=getattr(usage, "completion_tokens", 0),
        )

    def generate_from_image(self, system_prompt: str, user_prompt: str,
                             image_path: str, max_tokens: int = 2000) -> LLMResponse:
        if not self.supports_vision:
            raise NotImplementedError(
                f"El modelo '{self.model}' configurado no soporta imagenes. "
                "Usa un modelo de vision de DeepSeek o cambia a ClaudeProvider."
            )
        image_bytes = Path(image_path).read_bytes()
        image_b64 = base64.standard_b64encode(image_bytes).decode("utf-8")

        completion = call_with_retry(lambda: self.client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{image_b64}"},
                        },
                    ],
                },
            ],
        ))
        usage = completion.usage
        return LLMResponse(
            text=completion.choices[0].message.content,
            model=self.model,
            input_tokens=getattr(usage, "prompt_tokens", 0),
            output_tokens=getattr(usage, "completion_tokens", 0),
        )
