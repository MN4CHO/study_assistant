"""
Configuracion central del proyecto.

Carga variables desde un archivo .env (ver .env.example) para no
hardcodear API keys en el codigo ni subirlas por accidente a git.
"""

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv es opcional; si no esta, usa variables de entorno del sistema.

BASE_DIR = Path(__file__).resolve().parent

# --- Proveedor de LLM ---
# Puedes usar un proveedor distinto para texto y para imagenes (recomendado:
# Claude para transcribir notas manuscritas, DeepSeek para el resto, mas barato).
LLM_PROVIDER_TEXT = os.getenv("LLM_PROVIDER_TEXT", "mock")     # claude | deepseek | gemini | mock
LLM_PROVIDER_VISION = os.getenv("LLM_PROVIDER_VISION", "mock")  # claude | deepseek | gemini | mock

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-5")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")

# --- Rutas del proyecto ---
OBSIDIAN_VAULT_PATH = Path(os.getenv("OBSIDIAN_VAULT_PATH", BASE_DIR / "data" / "vault"))
HANDWRITTEN_NOTES_PATH = Path(os.getenv("HANDWRITTEN_NOTES_PATH", BASE_DIR / "data" / "handwritten"))
OUTPUT_PATH = Path(os.getenv("OUTPUT_PATH", BASE_DIR / "output"))
SYNC_STATE_FILE = OUTPUT_PATH / "sync_state.json"

# --- Prefijo de archivos generados por el pipeline ---
# Se guardan junto a cada apunte original en el vault. Centralizado aca
# porque tanto main.py (lo escribe) como ingestion/obsidian_reader.py
# (lo excluye al leer el vault, para no reprocesarlo) dependen del mismo valor.
CUESTIONARIO_PREFIX = "Q_"
GENERATED_PREFIXES = (CUESTIONARIO_PREFIX,)

# Nombre del reporte de priorizacion de temas (tambien excluido al leer el
# vault, por la misma razon que GENERATED_PREFIXES).
PRIORIZACION_FILENAME = "priorizacion_temas.md"

# --- Estructura de certificaciones dentro del vault ---
# Carpeta raiz (directamente bajo OBSIDIAN_VAULT_PATH) cuyas subcarpetas
# directas representan cada certificacion/materia (ej. Certificaciones/AIE,
# Certificaciones/EHE). El analisis de priorizacion de temas se agrupa por
# certificacion para no mezclar el vocabulario de una con otra.
CERTIFICATIONS_DIR_NAME = os.getenv("CERTIFICATIONS_DIR_NAME", "Certificaciones")

# Subcarpeta (dentro de cada certificacion) donde se guarda el reporte de
# priorizacion de temas de esa certificacion.
TEMAS_IMPORTANTES_DIR_NAME = os.getenv("TEMAS_IMPORTANTES_DIR_NAME", "Temas_importantes")

# Carpeta raiz (directamente bajo OBSIDIAN_VAULT_PATH) cuyas notas se excluyen
# por completo del pipeline (ni cuestionario ni analisis de temas), porque no
# son contenido de estudio (ej. la nota de recoleccion del plugin Tasks).
EXCLUDED_DIR_NAME = os.getenv("EXCLUDED_DIR_NAME", "Tareas")


def get_text_api_key(provider_name: str) -> str:
    return {
        "claude": ANTHROPIC_API_KEY,
        "deepseek": DEEPSEEK_API_KEY,
        "gemini": GEMINI_API_KEY,
    }.get(provider_name, "")


def get_model_name(provider_name: str) -> str:
    return {
        "claude": CLAUDE_MODEL,
        "deepseek": DEEPSEEK_MODEL,
        "gemini": GEMINI_MODEL,
    }.get(provider_name, "")
