"""
Identificacion de patrones: analiza el conjunto de notas para detectar
que temas/conceptos son mas recurrentes (senal cuantitativa de
"importancia"), y opcionalmente cruza eso con el criterio del LLM.

Esto es lo que hace que la "priorizacion de temas" no sea solo
"le pregunte a la IA que es importante" (subjetivo), sino que tenga
una base de datos real detras.
"""

from dataclasses import dataclass

from sklearn.feature_extraction.text import TfidfVectorizer

from llm.base import LLMProvider


@dataclass
class TopicScore:
    note_title: str
    top_terms: list[str]
    score: float  # promedio de los pesos TF-IDF de los terminos principales


def rank_notes_by_density(notes_content: dict[str, str], top_n_terms: int = 5) -> list[TopicScore]:
    """
    Calcula, para cada nota, sus terminos mas distintivos via TF-IDF
    (terminos que aparecen mucho en esa nota mas no tanto en las demas,
    lo cual suele senalar conceptos centrales del tema).
    """
    titles = list(notes_content.keys())
    documents = list(notes_content.values())

    if len(documents) < 2:
        # TF-IDF necesita comparar contra un corpus; con 1 sola nota no aporta señal real.
        return [TopicScore(note_title=t, top_terms=[], score=0.0) for t in titles]

    vectorizer = TfidfVectorizer(max_features=500, stop_words=_spanish_stopwords())
    matrix = vectorizer.fit_transform(documents)
    feature_names = vectorizer.get_feature_names_out()

    scores = []
    for i, title in enumerate(titles):
        row = matrix[i].toarray().flatten()
        top_indices = row.argsort()[-top_n_terms:][::-1]
        top_terms = [feature_names[idx] for idx in top_indices if row[idx] > 0]
        avg_score = float(row[top_indices].mean()) if len(top_indices) else 0.0
        scores.append(TopicScore(note_title=title, top_terms=top_terms, score=avg_score))

    return sorted(scores, key=lambda s: s.score, reverse=True)


def suggest_priorities(provider: LLMProvider, topic_scores: list[TopicScore]) -> str:
    """
    Combina la señal cuantitativa (TF-IDF) con el criterio del LLM para
    generar una recomendacion final en lenguaje natural sobre que
    temas profundizar primero.
    """
    ranking_summary = "\n".join(
        f"- {ts.note_title}: terminos clave = {', '.join(ts.top_terms) or '(sin datos suficientes)'}, "
        f"densidad = {ts.score:.3f}"
        for ts in topic_scores
    )

    system_prompt = """\
Eres un asistente de estudio que ayuda a un estudiante universitario a \
priorizar que temas repasar primero, basandote en un analisis de \
densidad de conceptos de sus propias notas (ya calculado).

Usa el ranking cuantitativo como base, pero puedes ajustar el orden si \
detectas que un tema con menor densidad es un prerequisito conceptual \
de otros temas mas densos. Explica brevemente el porque de cada \
prioridad (1-2 oraciones por tema).
"""
    user_prompt = f"Ranking de densidad de conceptos por nota:\n\n{ranking_summary}"

    response = provider.generate_text(system_prompt, user_prompt, max_tokens=1200)
    return response.text


def _spanish_stopwords() -> list[str]:
    return [
        "de", "la", "el", "en", "y", "a", "los", "las", "un", "una", "que",
        "se", "no", "es", "por", "con", "para", "su", "al", "lo", "como",
        "mas", "pero", "sus", "le", "ya", "o", "este", "sí", "porque",
        "esta", "entre", "cuando", "muy", "sin", "sobre", "también",
        "me", "hasta", "donde", "quien", "desde", "todo", "nos",
    ]
