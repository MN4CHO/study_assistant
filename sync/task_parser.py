"""
Parsing de tareas en formato del plugin Tasks de Obsidian, desde
Tareas/001_Tareas.md, para sincronizarlas con una base de datos de Notion.

No dependemos del plugin Tasks en tiempo de ejecucion (Python no puede
llamarlo): el plugin solo le da al usuario, dentro de Obsidian, una UI y
una sintaxis estandar (checkboxes, fechas, prioridades). Este modulo
re-implementa el parseo de esa misma sintaxis en texto plano para poder
mapear cada tarea a las propiedades de la base de datos de Notion.

Formato de una linea de tarea:

    - [w] Repasar Normalizacion 🛫 2026-07-06 📅 2026-07-06 [hora:: 13:00-16:00] ⏫ #proyecto/Kaizen #contexto/University #energia/Extreme

- `[w]` etc.: caracter de estado, configurado igual en Settings > Tasks >
  Statuses de Obsidian para que el checkbox se vea consistente (ver STATUS_MAP).
- `🛫` fecha de inicio, `📅` fecha (due), ambas reconocidas nativamente por Tasks.
- `[hora:: HH:MM-HH:MM]`: rango horario del mismo dia (Tasks no maneja horas).
- `🔺⏫🔼🔽⏬`: prioridad, reconocida nativamente por Tasks.
- `#proyecto/...`, `#contexto/...`, `#energia/...`: tags jerarquicos; Tasks
  no les da significado especial, pero este parser si.
- Tras el primer sync, el script agrega `%%notion:<page_id>%%` al final de
  la linea (comentario invisible en Obsidian) para actualizar en vez de
  duplicar en la siguiente corrida.
"""

import re
from dataclasses import dataclass

TASK_LINE_RE = re.compile(r"^\s*-\s\[(?P<status>.)\]\s+(?P<rest>.*)$")

# Caracter de checkbox -> valor del select/status "Status" en Notion.
STATUS_MAP = {
    " ": "Inbox",
    "/": "En proceso",
    "w": "Esperando",
    "d": "Delegada",
    "x": "Completed",
}

# Emoji de prioridad de Tasks -> valor del select "Prioridad" en Notion.
PRIORITY_MAP = {
    "🔺": "Urgente",
    "⏫": "Alta",
    "🔼": "Media",
    "🔽": "Baja",
    "⏬": "Mínima",
}

DATE_START_RE = re.compile(r"🛫\s*(\d{4}-\d{2}-\d{2})")
DATE_DUE_RE = re.compile(r"📅\s*(\d{4}-\d{2}-\d{2})")
HORA_RE = re.compile(r"\[hora::\s*(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})\]")
TAG_RE = re.compile(r"#(proyecto|contexto|energia)/([^\s#]+)")
URL_RE = re.compile(r"\[[^\]]*\]\((https?://[^\s)]+)\)")
NOTION_ID_RE = re.compile(r"%%notion:([0-9a-fA-F-]+)%%")
PRIORITY_CHARS_RE = re.compile("|".join(re.escape(p) for p in PRIORITY_MAP))

_TITLE_CLEANUP_PATTERNS = (
    DATE_START_RE, DATE_DUE_RE, HORA_RE, TAG_RE, URL_RE, NOTION_ID_RE, PRIORITY_CHARS_RE,
)


@dataclass
class Task:
    line_no: int
    raw_line: str
    status_char: str
    title: str
    start_date: str | None = None
    due_date: str | None = None
    hora_inicio: str | None = None
    hora_fin: str | None = None
    priority: str | None = None
    proyecto: str | None = None
    contexto: str | None = None
    energia: str | None = None
    url: str | None = None
    notion_page_id: str | None = None

    @property
    def status(self) -> str:
        return STATUS_MAP.get(self.status_char, "Inbox")


def parse_tasks_file(text: str) -> list[Task]:
    """Parsea todas las lineas de tarea (checkboxes) de 001_Tareas.md."""
    tasks = []
    for i, line in enumerate(text.splitlines()):
        match = TASK_LINE_RE.match(line)
        if not match:
            continue
        rest = match.group("rest")

        tags = dict(TAG_RE.findall(rest))
        priority_match = PRIORITY_CHARS_RE.search(rest)
        start_match = DATE_START_RE.search(rest)
        due_match = DATE_DUE_RE.search(rest)
        hora_match = HORA_RE.search(rest)
        url_match = URL_RE.search(rest)
        notion_match = NOTION_ID_RE.search(rest)

        title = rest
        for pattern in _TITLE_CLEANUP_PATTERNS:
            title = pattern.sub("", title)
        title = " ".join(title.split())

        tasks.append(Task(
            line_no=i,
            raw_line=line,
            status_char=match.group("status"),
            title=title,
            start_date=start_match.group(1) if start_match else None,
            due_date=due_match.group(1) if due_match else None,
            hora_inicio=hora_match.group(1) if hora_match else None,
            hora_fin=hora_match.group(2) if hora_match else None,
            priority=PRIORITY_MAP.get(priority_match.group(0)) if priority_match else None,
            proyecto=tags.get("proyecto"),
            contexto=tags.get("contexto"),
            energia=tags.get("energia"),
            url=url_match.group(1) if url_match else None,
            notion_page_id=notion_match.group(1) if notion_match else None,
        ))
    return tasks


def set_notion_id(line: str, page_id: str) -> str:
    """Devuelve la linea con el marcador %%notion:<id>%% agregado (o
    reemplazado si ya tenia uno), para que la proxima corrida actualice esa
    misma pagina de Notion en vez de crear una duplicada."""
    line = NOTION_ID_RE.sub("", line).rstrip()
    return f"{line} %%notion:{page_id}%%"
