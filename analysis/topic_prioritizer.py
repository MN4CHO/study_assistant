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


def suggest_priorities(
    provider: LLMProvider,
    cert_name: str,
    notes_content: dict[str, str],
    topic_scores: list[TopicScore],
) -> str:
    """
    Le pasa al LLM el contenido completo de las notas (no solo una lista de
    terminos) y le pide que actue como experto en la certificacion: que
    identifique, con su propio conocimiento del dominio completo (no solo lo
    que aparece en las notas), que temas son mas importantes para la
    certificacion y cuales estan debiles o ausentes en las notas del
    estudiante. La densidad TF-IDF se pasa solo como señal de apoyo.
    """
    ranking_summary = "\n".join(
        f"- {ts.note_title}: terminos mas distintivos = "
        f"{', '.join(ts.top_terms) or '(sin datos suficientes)'}, densidad = {ts.score:.3f}"
        for ts in topic_scores
    )
    notes_text = "\n\n".join(
        f"### {title}\n{content}" for title, content in notes_content.items()
    )

    system_prompt = f"""\
Eres un experto certificado en "{cert_name}", con dominio completo de TODOS \
los temas que tipicamente cubre esta certificacion, no solo de lo que \
aparece en las notas de un estudiante en particular.

Vas a leer las notas de estudio completas de un estudiante para esta \
certificacion. Tu tarea, actuando como ese experto:

1. Identifica, usando tu propio conocimiento del dominio completo de la \
certificacion, cuales son los temas/subtemas MAS IMPORTANTES a los que el \
estudiante deberia prestar mas atencion (los que mas peso tienen en un \
examen o dominio real de la certificacion, no solo los mas mencionados).
2. Señala explicitamente que temas estan debiles, superficiales o \
directamente ausentes en las notas, comparado con lo que un experto \
esperaria que el estudiante domine.
3. Da una lista priorizada (mas importante primero) de en que enfocar el \
estudio, con 1-3 oraciones de justificacion por cada tema.

Usa la densidad de conceptos (calculada automaticamente via TF-IDF) solo \
como señal de apoyo, no como criterio principal: un tema puede ser critico \
para la certificacion aunque aparezca poco en las notas (senal de que esta \
descuidado), y viceversa.

Señal de densidad de conceptos por nota:
{ranking_summary}
"""
    user_prompt = f"Notas completas del estudiante para esta certificacion:\n\n{notes_text}"

    response = provider.generate_text(system_prompt, user_prompt, max_tokens=6000)
    return response.text


def _spanish_stopwords() -> list[str]:
    return [
        "de", "la", "el", "en", "y", "a", "los", "las", "un", "una", "que",
        "se", "no", "es", "por", "con", "para", "su", "al", "lo", "como",
        "mas", "pero", "sus", "le", "ya", "o", "este", "sí", "porque",
        "esta", "entre", "cuando", "muy", "sin", "sobre", "también",
        "me", "hasta", "donde", "quien", "desde", "todo", "nos",
    ]
