"""
Transcripcion de notas manuscritas (imagenes exportadas de Samsung Notes).

Usa un proveedor con soporte de vision para leer la imagen, digitalizar
el contenido y devolver una version mejorada en formato Markdown,
preservando la estructura (titulos, listas, formulas, etc.).
"""

from pathlib import Path

from llm.base import LLMProvider

TRANSCRIPTION_SYSTEM_PROMPT = """\
Eres un asistente experto en digitalizar y mejorar apuntes universitarios \
manuscritos, convirtiendolos a Markdown limpio y bien estructurado.

Proceso:
1. Transcribe fielmente todo el contenido de la imagen.
2. Mejora esos apuntes para que sirvan como material de estudio:
   - Corrige errores evidentes de ortografia y gramatica.
   - Reorganiza en una jerarquia clara (encabezados, listas, tablas).
   - Expande abreviaturas y completa frases incompletas cuando el \
sentido sea inequivoco.
   - Aclara conceptos ambiguos o mal explicados con frases breves.

Reglas:
- No inventes datos, definiciones ni ejemplos que contradigan la imagen; \
solo aclara o reordena lo que ya esta.
- Si hay una palabra o simbolo ilegible, marcalo como [ilegible] en vez de adivinar.
- Cualquier aclaracion o ampliacion que agregues ponla en una cita con el \
prefijo "> Nota:" para distinguirla del apunte original.
- Formulas matematicas en LaTeX cuando corresponda.
- Para diagramas o esquemas usa bloques ```mermaid``` o una lista; no dibujes \
diagramas con caracteres ASCII (ocupan mucho y quedan mal).
- Empieza con un titulo de nivel 1 (#) que resuma el tema del apunte.
- No agregues comentarios sobre lo que hiciste; devuelve unicamente el Markdown.
"""

_MAX_TOKENS = 8000
_MAX_CONTINUATIONS = 3


def transcribe_image(provider: LLMProvider, image_path: Path) -> str:
    """Digitaliza y mejora una imagen de apuntes manuscritos a Markdown.

    Si el proveedor corta la respuesta por limite de tokens, se pide que
    continue desde donde se quedo y se van concatenando los fragmentos.
    """
    if not provider.supports_vision:
        raise ValueError(
            "El proveedor configurado para vision no soporta imagenes. "
            "Revisa LLM_PROVIDER_VISION en tu .env."
        )

    user_prompt = (
        "Digitaliza y mejora esta nota manuscrita, devolviendola en Markdown "
        "siguiendo el proceso y las reglas indicadas."
    )
    parts: list[str] = []
    for attempt in range(_MAX_CONTINUATIONS + 1):
        response = provider.generate_from_image(
            system_prompt=TRANSCRIPTION_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            image_path=str(image_path),
            max_tokens=_MAX_TOKENS,
        )
        parts.append(response.text.strip())
        if not response.truncated:
            break
        if attempt == _MAX_CONTINUATIONS:
            print(f"  Aviso: la transcripcion de {image_path.name} sigue incompleta "
                  f"tras {_MAX_CONTINUATIONS} continuaciones.")
            break
        so_far = "\n\n".join(parts)
        user_prompt = (
            "Ya transcribiste parte de esta nota (abajo). Continua EXACTAMENTE "
            "desde donde se corto, sin repetir lo ya escrito y sin volver a "
            "empezar. Devuelve solo la continuacion en Markdown.\n\n"
            "--- Transcripcion hasta ahora ---\n" + so_far
        )

    return "\n".join(parts)


def transcribe_folder(provider: LLMProvider, folder_path: Path) -> dict[Path, str]:
    """Digitaliza y mejora todas las imagenes de una carpeta (incluidas
    subcarpetas). Devuelve {ruta_imagen: markdown}, para poder guardar cada
    .md junto a su imagen de origen."""
    valid_extensions = {".png", ".jpg", ".jpeg", ".webp"}
    results: dict[Path, str] = {}
    if not folder_path.exists():
        return results

    for image_file in sorted(folder_path.rglob("*")):
        if image_file.is_file() and image_file.suffix.lower() in valid_extensions:
            results[image_file] = transcribe_image(provider, image_file)
    return results
