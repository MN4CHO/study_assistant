"""
Transcripcion de notas manuscritas (imagenes exportadas de Samsung Notes).

Usa un proveedor con soporte de vision para leer la imagen y devolver
texto en formato Markdown, preservando la estructura (titulos, listas,
formulas, etc.) lo mejor posible.
"""

from pathlib import Path

from llm.base import LLMProvider

TRANSCRIPTION_SYSTEM_PROMPT = """\
Eres un asistente experto en transcribir apuntes universitarios manuscritos \
a texto Markdown limpio y bien estructurado.

Reglas:
- Transcribe fielmente el contenido; no inventes ni completes informacion \
que no este en la imagen.
- Si hay una palabra o simbolo ilegible, marcalo como [ilegible] en vez de adivinar.
- Preserva la jerarquia visual: titulos como encabezados Markdown, listas \
como listas, formulas matematicas en formato LaTeX cuando corresponda.
- No agregues comentarios tuyos ni expliques lo que hiciste, devuelve \
unicamente el Markdown transcrito.
"""


def transcribe_image(provider: LLMProvider, image_path: Path) -> str:
    """Transcribe una imagen de apuntes manuscritos a Markdown."""
    if not provider.supports_vision:
        raise ValueError(
            "El proveedor configurado para vision no soporta imagenes. "
            "Revisa LLM_PROVIDER_VISION en tu .env."
        )

    response = provider.generate_from_image(
        system_prompt=TRANSCRIPTION_SYSTEM_PROMPT,
        user_prompt="Transcribe esta nota manuscrita a Markdown siguiendo las reglas indicadas.",
        image_path=str(image_path),
        max_tokens=3000,
    )
    return response.text


def transcribe_folder(provider: LLMProvider, folder_path: Path) -> dict[str, str]:
    """Transcribe todas las imagenes de una carpeta. Devuelve {nombre_archivo: markdown}."""
    valid_extensions = {".png", ".jpg", ".jpeg", ".webp"}
    results = {}
    if not folder_path.exists():
        return results

    for image_file in sorted(folder_path.iterdir()):
        if image_file.suffix.lower() in valid_extensions:
            results[image_file.stem] = transcribe_image(provider, image_file)
    return results
