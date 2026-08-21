"""
Ingestion de notas de Obsidian.

Responsabilidad unica: leer archivos .md del vault y detectar cuales
son nuevos o se modificaron desde la ultima corrida (para no reprocesar
todo el vault cada vez que se ejecuta el pipeline).
"""

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import config


@dataclass
class ObsidianNote:
    path: Path
    title: str
    content: str
    content_hash: str


def _hash_content(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def read_vault(vault_path: Path) -> list[ObsidianNote]:
    """Lee todos los archivos .md del vault (recursivo), excluyendo los
    generados por el propio pipeline (Q_*.md, priorizacion_temas.md) para no
    reprocesarlos como si fueran apuntes originales, y las notas que esten
    bajo config.EXCLUDED_DIR_NAME (no son contenido de estudio)."""
    notes = []
    for md_file in sorted(vault_path.rglob("*.md")):
        if md_file.name.startswith(config.GENERATED_PREFIXES):
            continue
        if md_file.name == config.PRIORIZACION_FILENAME:
            continue
        if md_file.relative_to(vault_path).parts[0] == config.EXCLUDED_DIR_NAME:
            continue
        content = md_file.read_text(encoding="utf-8")
        notes.append(ObsidianNote(
            path=md_file,
            title=md_file.stem,
            content=content,
            content_hash=_hash_content(content),
        ))
    return notes


def load_sync_state(state_file: Path) -> dict:
    """Carga el registro de que notas ya fueron procesadas (por hash)."""
    if state_file.exists():
        return json.loads(state_file.read_text(encoding="utf-8"))
    return {}


def save_sync_state(state_file: Path, state: dict) -> None:
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def get_pending_notes(vault_path: Path, state_file: Path) -> list[ObsidianNote]:
    """
    Devuelve solo las notas nuevas o modificadas desde la ultima corrida.
    Este es el paso clave de "deteccion de cambios" del pipeline.
    """
    all_notes = read_vault(vault_path)
    state = load_sync_state(state_file)

    pending = [
        note for note in all_notes
        if state.get(str(note.path)) != note.content_hash
    ]
    return pending


def mark_notes_processed(notes: list[ObsidianNote], state_file: Path) -> None:
    """Actualiza el registro de sincronizacion tras procesar exitosamente."""
    state = load_sync_state(state_file)
    for note in notes:
        state[str(note.path)] = note.content_hash
    save_sync_state(state_file, state)
