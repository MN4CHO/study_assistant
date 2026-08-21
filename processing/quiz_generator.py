"""
Genera cuestionarios estilo examen a partir de una nota.
"""

from llm.base import LLMProvider

def _build_system_prompt(note_title: str) -> str:
    return f"""\
Crea una guía de preguntas y respuestas del tema {note_title}, optimizado para aplicar la técnica de repaso “Active Recall”.
Necesito que escribas la mayor cantidad de preguntas posibles en cada uno de los subtemas que puedan ser preguntas de examen.
Cada pregunta debe ir numerada y tener debajo su respuesta. Es importante que agrupes las preguntas por cada uno de los subtemas.
La información de cada respuesta debe estar organizada correctamente para facilitar el repaso.
Ve directo al contenido: no escribas ninguna introducción ni comentario antes de la guía.
"""


def generate_quiz(provider: LLMProvider, note_content: str, note_title: str = "") -> str:
    user_prompt = f"Tema: {note_title}\n\nContenido de la nota:\n\n{note_content}"
    response = provider.generate_text(
        system_prompt=_build_system_prompt(note_title),
        user_prompt=user_prompt,
        max_tokens=8000,
    )
    return response.text
