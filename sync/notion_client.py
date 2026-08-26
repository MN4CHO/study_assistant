"""
Cliente delgado sobre el SDK oficial de Notion (notion-client), para
crear/actualizar paginas en la base de datos de Notion a partir de una
Task parseada de Obsidian.

No asumimos los tipos exactos de cada propiedad (mas alla de lo que se ve
en pantalla, la base puede tener 11+ propiedades adicionales): se lee el
esquema real via API y se construye el payload segun el tipo que Notion
reporte para cada propiedad. Si una propiedad no soporta el tipo de valor
que tenemos (ej. "Proyecto" resulta ser una relation en vez de texto), se
omite con un aviso en vez de fallar toda la sincronizacion.

Notion separo cada base de datos en una o mas "data sources" (API version
2025-09-03): el esquema de propiedades y el parent al crear una pagina
viven en el data source, no en la base en si (`databases.retrieve` ya no
devuelve "properties"). Aca asumimos el caso comun de una sola fuente de
datos por base; si hay varias, se usa la primera y se avisa.
"""

from notion_client import Client

from .task_parser import Task

# Tipos de propiedad de Notion que sabemos construir automaticamente a
# partir de los datos que extraemos de una tarea de Obsidian.
_SUPPORTED_TYPES = ("title", "rich_text", "select", "status", "multi_select", "url", "date")
_SELECT_LIKE_TYPES = ("select", "status", "multi_select")


class NotionSync:

    def __init__(self, api_key: str, database_id: str, property_names: dict[str, str]):
        self.client = Client(auth=api_key)
        self.database_id = database_id
        self.property_names = property_names
        self._data_source_id: str | None = None
        self._schema: dict | None = None
        self._warned: set[str] = set()

    def _get_data_source_id(self) -> str:
        if self._data_source_id is None:
            db = self.client.databases.retrieve(database_id=self.database_id)
            sources = db.get("data_sources") or []
            if not sources:
                raise RuntimeError(
                    f"La base de datos de Notion {self.database_id} no tiene ninguna fuente de datos."
                )
            if len(sources) > 1:
                self._warn_once(
                    "multi-source",
                    f"la base tiene {len(sources)} fuentes de datos, se usa la primera "
                    f"('{sources[0]['name']}').",
                )
            self._data_source_id = sources[0]["id"]
        return self._data_source_id

    def _get_schema(self) -> dict:
        if self._schema is None:
            data_source = self.client.data_sources.retrieve(data_source_id=self._get_data_source_id())
            self._schema = data_source["properties"]
        return self._schema

    def _title_property_name(self) -> str:
        for name, prop in self._get_schema().items():
            if prop["type"] == "title":
                return name
        raise RuntimeError("La base de datos de Notion no tiene ninguna propiedad de tipo 'title'.")

    def get_select_options(self, logical_field: str) -> list[str]:
        """Opciones validas (segun el esquema real de Notion) para un campo
        select/status/multi_select, ej. get_select_options('prioridad'). Se
        usa tanto para no mandar valores invalidos como para que el LLM
        elija entre opciones reales en vez de inventar una."""
        prop_name = self.property_names.get(logical_field)
        prop = self._get_schema().get(prop_name) if prop_name else None
        if not prop or prop["type"] not in _SELECT_LIKE_TYPES:
            return []
        return [o["name"] for o in prop[prop["type"]]["options"]]

    def upsert_task(self, task: Task) -> str:
        """Crea la pagina si la tarea no tiene notion_page_id, o la
        actualiza si ya lo tiene. Devuelve el page_id resultante."""
        schema = self._get_schema()
        properties = {self._title_property_name(): _value_for_type("title", task.title)}

        field_values = {
            "status": (self.property_names.get("status"), task.status),
            "fecha": (self.property_names.get("fecha"), self._fecha_value(task)),
            "prioridad": (self.property_names.get("prioridad"), task.priority),
            "contexto": (self.property_names.get("contexto"), task.contexto),
            "energia": (self.property_names.get("energia"), task.energia),
            "proyecto": (self.property_names.get("proyecto"), task.proyecto),
            "url": (self.property_names.get("url"), task.url),
        }

        for logical_field, (prop_name, value) in field_values.items():
            if value is None or not prop_name:
                continue
            prop = schema.get(prop_name)
            if prop is None:
                self._warn_once(f"missing:{prop_name}",
                                 f"la propiedad '{prop_name}' no existe en la base de Notion, se omite.")
                continue
            if prop["type"] not in _SUPPORTED_TYPES:
                self._warn_once(f"type:{prop_name}",
                                 f"la propiedad '{prop_name}' es de tipo '{prop['type']}' "
                                 f"(no soportado automaticamente), se omite el campo '{logical_field}'.")
                continue
            properties[prop_name] = _value_for_type(prop["type"], value)

        if task.notion_page_id:
            page = self.client.pages.update(page_id=task.notion_page_id, properties=properties)
        else:
            parent = {"type": "data_source_id", "data_source_id": self._get_data_source_id()}
            page = self.client.pages.create(parent=parent, properties=properties)
        return page["id"]

    def _fecha_value(self, task: Task) -> dict | None:
        if not task.due_date:
            return None
        value = {"start": _iso_datetime(task.due_date, task.hora_inicio)}
        if task.hora_fin:
            value["end"] = _iso_datetime(task.due_date, task.hora_fin)
        return value

    def _warn_once(self, key: str, message: str) -> None:
        if key in self._warned:
            return
        self._warned.add(key)
        print(f"  Aviso: {message}")


def _value_for_type(prop_type: str, value) -> dict:
    if prop_type == "title":
        return {"title": [{"text": {"content": str(value)}}]}
    if prop_type == "rich_text":
        return {"rich_text": [{"text": {"content": str(value)}}]}
    if prop_type == "select":
        return {"select": {"name": value}}
    if prop_type == "status":
        return {"status": {"name": value}}
    if prop_type == "multi_select":
        values = value if isinstance(value, list) else [value]
        return {"multi_select": [{"name": v} for v in values]}
    if prop_type == "url":
        return {"url": value}
    if prop_type == "date":
        return {"date": value}
    raise ValueError(f"Tipo de propiedad no soportado: {prop_type}")


def _iso_datetime(date: str, time: str | None) -> str:
    return f"{date}T{time}:00" if time else date
