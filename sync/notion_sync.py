"""
Orquestador de la sincronizacion Obsidian (Tareas/001_Tareas.md, formato
del plugin Tasks) -> Notion.

Flujo:
1. Parsea las tareas del archivo (sync.task_parser).
2. Para los campos que falten (sin tag/emoji explicito en la linea), le
   pide al LLM que elija entre las opciones reales de la base de Notion
   (nunca inventa un valor que no exista en el select) -> categoria de
   "Toma de decisiones".
3. Sube cada tarea a Notion: crea una pagina nueva o actualiza la
   existente, segun el marcador %%notion:<page_id>%% de la linea.
4. Reescribe 001_Tareas.md agregando ese marcador a las tareas nuevas,
   para que la proxima corrida actualice en vez de duplicar.
"""

import json

import config
from llm.base import LLMProvider
from .notion_client import NotionSync
from .task_parser import Task, parse_tasks_file, set_notion_id

_INFERABLE_FIELDS = {"prioridad": "priority", "contexto": "contexto", "energia": "energia"}


def _infer_missing_fields(provider: LLMProvider, notion: NotionSync, task: Task) -> None:
    """Completa con el LLM los campos select que la tarea no trae explicitos
    en el texto (sin tag #campo/valor), eligiendo solo entre las opciones
    reales de la base de Notion."""
    missing_options = {
        field: notion.get_select_options(field)
        for field, attr in _INFERABLE_FIELDS.items()
        if not getattr(task, attr)
    }
    missing_options = {field: opts for field, opts in missing_options.items() if opts}
    if not missing_options:
        return

    options_text = "\n".join(f"- {field}: {', '.join(opts)}" for field, opts in missing_options.items())
    system_prompt = f"""\
Eres un asistente que clasifica tareas de estudio. Para la tarea dada, \
elige el valor mas apropiado para cada uno de estos campos, ESTRICTAMENTE \
de entre las opciones listadas (nunca inventes un valor nuevo que no este \
en la lista):

{options_text}

Responde SOLO con un JSON valido, sin texto adicional ni markdown, con esta forma:
{{"{next(iter(missing_options))}": "valor elegido", ...}}
Usa exactamente estos nombres de campo: {', '.join(missing_options.keys())}.
"""
    response = provider.generate_text(system_prompt, f"Tarea: {task.title}", max_tokens=200)
    try:
        choices = json.loads(response.text.strip().strip("`"))
    except (json.JSONDecodeError, AttributeError):
        print(f"  Aviso: no se pudo interpretar la respuesta del LLM para '{task.title}', se deja sin clasificar.")
        return

    for field, value in choices.items():
        if field in missing_options and value in missing_options[field]:
            setattr(task, _INFERABLE_FIELDS[field], value)


def sync_tasks_to_notion(text_provider: LLMProvider) -> None:
    if not config.NOTION_API_KEY or not config.NOTION_DATABASE_ID:
        print("Notion no esta configurado (falta NOTION_API_KEY o NOTION_DATABASE_ID en .env), se omite la sincronizacion.")
        return
    if not config.TAREAS_FILE.exists():
        print(f"No existe {config.TAREAS_FILE}, no hay tareas que sincronizar.")
        return

    notion = NotionSync(config.NOTION_API_KEY, config.NOTION_DATABASE_ID, config.NOTION_PROPERTY_MAP)

    text = config.TAREAS_FILE.read_text(encoding="utf-8")
    tasks = parse_tasks_file(text)
    if not tasks:
        print("No hay tareas (checkboxes) en 001_Tareas.md.")
        return

    print(f"Sincronizando {len(tasks)} tarea(s) con Notion...")
    lines = text.splitlines()
    file_changed = False

    for task in tasks:
        _infer_missing_fields(text_provider, notion, task)
        page_id = notion.upsert_task(task)
        print(f"  -> {task.title} [{task.status}]")

        if not task.notion_page_id:
            lines[task.line_no] = set_notion_id(task.raw_line, page_id)
            file_changed = True

    if file_changed:
        config.TAREAS_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"{len(tasks)} tarea(s) sincronizada(s) con Notion.")
