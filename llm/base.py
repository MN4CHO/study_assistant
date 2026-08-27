"""
Interfaz abstracta para proveedores de LLM.

Patron Adapter: el resto del pipeline (ingestion, processing, analysis)
solo conoce esta interfaz, nunca los detalles de Claude o DeepSeek.
Esto permite cambiar de proveedor cambiando una linea de configuracion,
sin tocar el resto del codigo.
"""

import random
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass

# Codigos HTTP que indican un problema transitorio del lado del proveedor
# (sobrecarga, rate limit) y que vale la pena reintentar. Cualquier otro
# codigo (401, 400, etc.) es un error real que no se arregla reintentando.
_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


def _status_code_of(exc: Exception) -> int | None:
    # Los distintos SDKs (google-genai, anthropic, openai) exponen el codigo
    # HTTP en atributos con nombres distintos.
    return getattr(exc, "code", None) or getattr(exc, "status_code", None)


def call_with_retry(fn, max_attempts: int = 4, base_delay: float = 5.0):
    """Llama a fn() reintentando con backoff exponencial si el proveedor
    devuelve un error transitorio (sobrecarga/rate limit). Cualquier otro
    error se relanza de inmediato, sin reintentar."""
    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except Exception as exc:
            status_code = _status_code_of(exc)
            if status_code not in _RETRYABLE_STATUS_CODES or attempt == max_attempts:
                raise
            delay = base_delay * (2 ** (attempt - 1)) + random.uniform(0, 1)
            print(f"  Aviso: error {status_code} del proveedor (intento {attempt}/{max_attempts}), "
                  f"reintentando en {delay:.0f}s...")
            time.sleep(delay)


@dataclass
class LLMResponse:
    """Resultado normalizado de cualquier proveedor."""
    text: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    # True si el proveedor corto la respuesta por limite de tokens (quedo incompleta).
    truncated: bool = False


class LLMProvider(ABC):
    """Contrato que debe implementar cada adaptador de proveedor."""

    @abstractmethod
    def generate_text(self, system_prompt: str, user_prompt: str,
                       max_tokens: int = 2000) -> LLMResponse:
        """Genera texto a partir de un prompt (sin imagen)."""
        raise NotImplementedError

    @abstractmethod
    def generate_from_image(self, system_prompt: str, user_prompt: str,
                             image_path: str, max_tokens: int = 2000) -> LLMResponse:
        """Genera texto a partir de un prompt + una imagen (para OCR de notas manuscritas)."""
        raise NotImplementedError

    @property
    @abstractmethod
    def supports_vision(self) -> bool:
        """Indica si este proveedor puede procesar imagenes."""
        raise NotImplementedError
