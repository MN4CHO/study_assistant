"""
Pipeline principal del asistente de estudio.

Flujo (ver README.md para el diagrama completo):
1. Ingesta: detecta notas nuevas/modificadas en el vault de Obsidian
   (y transcribe notas manuscritas si hay imagenes pendientes).
2. Procesamiento LLM: por cada nota -> cuestionario.
3. Analisis de patrones: TF-IDF por certificacion -> prioridad de temas.
4. Salida estructurada: Q_/priorizacion_temas.md junto a las notas
   (output/ solo queda para sync_state.json y notas sueltas sin
   certificacion asociada).
"""

import argparse
import sys
from pathlib import Path

import config
from llm import get_provider
from ingestion.obsidian_reader import get_pending_notes, mark_notes_processed, read_vault
from ingestion.handwriting_reader import transcribe_folder
from processing.quiz_generator import generate_quiz
from analysis.topic_prioritizer import rank_notes_by_density, suggest_priorities
from sync.notion_sync import sync_tasks_to_notion


def build_providers():
    text_provider = get_provider(
        config.LLM_PROVIDER_TEXT,
        api_key=config.get_text_api_key(config.LLM_PROVIDER_TEXT),
        model=config.get_model_name(config.LLM_PROVIDER_TEXT),
    )
    vision_provider = get_provider(
        config.LLM_PROVIDER_VISION,
        api_key=config.get_text_api_key(config.LLM_PROVIDER_VISION),
        model=config.get_model_name(config.LLM_PROVIDER_VISION),
    )
    return text_provider, vision_provider


def process_handwritten_notes(vision_provider) -> None:
    """Paso 2: transcribe imagenes pendientes y las guarda como .md en el vault."""
    transcriptions = transcribe_folder(vision_provider, config.HANDWRITTEN_NOTES_PATH)
    if not transcriptions:
        return

    print(f"Transcribiendo {len(transcriptions)} nota(s) manuscrita(s)...")
    config.OBSIDIAN_VAULT_PATH.mkdir(parents=True, exist_ok=True)
    for name, markdown_text in transcriptions.items():
        dest = config.OBSIDIAN_VAULT_PATH / f"{name}_transcrita.md"
        dest.write_text(markdown_text, encoding="utf-8")
        print(f"  -> guardado: {dest.name}")


def process_note(text_provider, note) -> None:
    """Paso 3: aplica las tareas de procesamiento sobre una nota.

    El cuestionario generado se guarda junto al apunte original en el vault
    (no en output/), con prefijo Q_.
    """
    print(f"Procesando: {note.title}")
    note_dir = note.path.parent

    quiz = generate_quiz(text_provider, note.content, note.title)
    (note_dir / f"{config.CUESTIONARIO_PREFIX}{note.title}.md").write_text(quiz, encoding="utf-8")


def _group_notes_by_certification(notes: list) -> tuple[dict[str, list], list]:
    """Agrupa notas por certificacion, para no mezclar el vocabulario de
    una certificacion con otra en el analisis TF-IDF.

    Una nota pertenece a la certificacion X si su ruta es
    OBSIDIAN_VAULT_PATH/<CERTIFICATIONS_DIR_NAME>/X/... (sin importar
    cuantas subcarpetas de semana/tema haya debajo). Las notas que no
    caen bajo esa estructura van al segundo elemento devuelto (grupo
    "suelto", sin certificacion asociada).
    """
    cert_groups: dict[str, list] = {}
    ungrouped: list = []

    for note in notes:
        rel_parts = note.path.relative_to(config.OBSIDIAN_VAULT_PATH).parts
        if len(rel_parts) >= 3 and rel_parts[0] == config.CERTIFICATIONS_DIR_NAME:
            cert_name = rel_parts[1]
            cert_groups.setdefault(cert_name, []).append(note)
        else:
            ungrouped.append(note)

    return cert_groups, ungrouped


def _write_priorizacion_report(text_provider, cert_name: str, notes: list, report_path: Path) -> None:
    notes_content = {n.title: n.content for n in notes}
    scores = rank_notes_by_density(notes_content)
    recommendation = suggest_priorities(text_provider, cert_name, notes_content, scores)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(recommendation, encoding="utf-8")
    print(f"Reporte de priorizacion guardado en: {report_path}")


def run_pattern_analysis(text_provider) -> None:
    """Paso 4: analiza el vault para priorizar temas, agrupando por
    certificacion para no mezclar temas de una certificacion con otra."""
    all_notes = read_vault(config.OBSIDIAN_VAULT_PATH)
    if not all_notes:
        print("No hay notas en el vault para analizar patrones.")
        return

    cert_groups, ungrouped = _group_notes_by_certification(all_notes)

    for cert_name, cert_notes in cert_groups.items():
        report_path = (
            config.OBSIDIAN_VAULT_PATH / config.CERTIFICATIONS_DIR_NAME
            / cert_name / config.TEMAS_IMPORTANTES_DIR_NAME / config.PRIORIZACION_FILENAME
        )
        _write_priorizacion_report(text_provider, cert_name, cert_notes, report_path)

    if ungrouped:
        report_path = config.OUTPUT_PATH / config.PRIORIZACION_FILENAME
        _write_priorizacion_report(text_provider, "estas notas de estudio", ungrouped, report_path)


def main():
    parser = argparse.ArgumentParser(description="Pipeline del asistente de estudio")
    parser.add_argument("--skip-handwriting", action="store_true",
                         help="Omite el paso de transcripcion de notas manuscritas")
    parser.add_argument("--skip-analysis", action="store_true",
                         help="Omite el analisis de priorizacion de temas")
    parser.add_argument("--sync-notion", action="store_true",
                         help="Sincroniza Tareas/001_Tareas.md con la base de datos de Notion")
    args = parser.parse_args()

    text_provider, vision_provider = build_providers()
    config.OUTPUT_PATH.mkdir(parents=True, exist_ok=True)

    if not args.skip_handwriting:
        process_handwritten_notes(vision_provider)

    pending_notes = get_pending_notes(config.OBSIDIAN_VAULT_PATH, config.SYNC_STATE_FILE)
    if not pending_notes:
        print("No hay notas nuevas o modificadas desde la ultima corrida.")
    else:
        print(f"{len(pending_notes)} nota(s) nueva(s)/modificada(s) detectada(s).")
        for note in pending_notes:
            process_note(text_provider, note)
        mark_notes_processed(pending_notes, config.SYNC_STATE_FILE)

    if not args.skip_analysis:
        run_pattern_analysis(text_provider)

    if args.sync_notion:
        sync_tasks_to_notion(text_provider)

    print("\nPipeline completado. Resultados en:", config.OUTPUT_PATH)


if __name__ == "__main__":
    sys.exit(main())
