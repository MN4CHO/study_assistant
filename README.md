# Asistente de Estudio con IA

Pipeline que toma tus apuntes de Obsidian y Samsung Notes (S-Pen), y genera
automaticamente: cuestionarios tipo examen, y recomendaciones de que temas
priorizar.

Proyecto para CyberMinds EPN Summer Camp 2026.

## 1. Instalacion

```bash
pip install -r requirements.txt --break-system-packages
cp .env.example .env
```

Edita `.env` con tus API keys reales y elige tu proveedor:

```
LLM_PROVIDER_TEXT=gemini       # gemini (gratis) | claude | deepseek
LLM_PROVIDER_VISION=claude     # recomendado: claude (mejor para OCR de escritura a mano)
GEMINI_API_KEY=tu_key_aqui       # gratis en https://aistudio.google.com/apikey
ANTHROPIC_API_KEY=tu_key_aqui
```

**Proveedores disponibles:**

| Proveedor | Costo | Cuando usarlo |
|---|---|---|
| `gemini` | Gratis (modelos Flash, con limite de solicitudes/minuto) | Desarrollo, pruebas, y uso normal de bajo volumen |
| `claude` | De pago (prepago, ~centavos por nota) | Transcripcion de notas manuscritas (mejor precision en vision) |
| `deepseek` | De pago (prepago, el mas barato de los dos pagos) | Alternativa de pago si necesitas mas calidad que Gemini gratis |
| `mock` | Gratis siempre | Probar que el pipeline corre sin usar ninguna API real |

Puedes mezclar proveedores: por ejemplo, `gemini` para todo el procesamiento de texto \
(gratis) y `claude` solo para la transcripcion de imagenes (donde la precision importa mas).

Mientras configuras tus keys, puedes dejar `LLM_PROVIDER_TEXT=mock` y
`LLM_PROVIDER_VISION=mock` para probar que el pipeline corre sin gastar
creditos (usa texto de relleno, no un modelo real).

## 2. Preparar tus datos

- **Obsidian**: apunta `OBSIDIAN_VAULT_PATH` en `.env` a la carpeta de tu
  vault real (o copia tus `.md` a `data/vault/`).
- **Samsung Notes**: exporta tus notas manuscritas como imagen (PNG/JPG)
  y colocalas en `data/handwritten/` (o configura `HANDWRITTEN_NOTES_PATH`).

## 3. Ejecutar

```bash
python3 main.py
```

Flags disponibles:
- `--skip-handwriting`: omite la transcripcion de imagenes.
- `--skip-analysis`: omite el analisis de priorizacion de temas.
- `--sync-notion`: sincroniza `Tareas/001_Tareas.md` con tu base de datos de Notion (ver seccion 7).

El cuestionario (`Q_<NombreApunte>.md`) queda junto al apunte original en el
vault. El reporte de priorizacion (`priorizacion_temas.md`) queda junto a
cada certificacion (o en `output/` si la nota no pertenece a ninguna).

## 4. Arquitectura del pipeline

```
Obsidian (.md) ----\
                     >---> [1. Ingesta] ---> [2. Deteccion de cambios]
Samsung Notes (img)-/                                |
                                                       v
                                    [3. Procesamiento LLM] (por nota)
                                                       |
                                                  cuestionario
                                                       |
                                                       v
                                   [4. Analisis de patrones] (TF-IDF,
                                    por certificacion) --> priorizacion de temas
                                                       |
                                                       v
                                       [5. Salida estructurada] (junto a las notas)
```

## 5. Estructura del codigo

```
study_assistant/
├── config.py                  # configuracion via .env
├── main.py                    # orquestador del pipeline
├── llm/                        # capa de abstraccion (patron Adapter)
│   ├── base.py                 # interfaz LLMProvider
│   ├── claude_adapter.py
│   ├── deepseek_adapter.py
│   └── mock_provider.py        # para pruebas sin costo
├── ingestion/
│   ├── obsidian_reader.py      # lee vault + detecta cambios
│   └── handwriting_reader.py   # transcribe imagenes via LLM multimodal
├── processing/
│   └── quiz_generator.py
├── analysis/
│   └── topic_prioritizer.py    # TF-IDF + LLM -> priorizacion
├── sync/
│   ├── task_parser.py           # markdown (plugin Tasks) -> objetos Task
│   ├── notion_client.py         # Task -> propiedades de Notion (esquema real via API)
│   └── notion_sync.py           # orquesta el parseo, LLM y subida a Notion
└── data/vault/                 # notas de ejemplo (reemplazar por tu vault real)
```

## 6. Mapeo a la rubrica del proyecto

| Modulo | Categoria de resultado de IA |
|---|---|
| `quiz_generator.py`, `handwriting_reader.py` | **Automatizacion** |
| `topic_prioritizer.py` | **Identificacion de patrones** |
| `topic_prioritizer.suggest_priorities()` (recomendaciones basadas en tu propio historial de apuntes) | **Personalizacion** |
| `sync/notion_sync.py` (el LLM elige el valor de cada propiedad de Notion que no venga explicito en la tarea, entre las opciones reales de la base) | **Toma de decisiones** |

## 7. Sincronizacion con Notion

Las tareas se escriben en `Tareas/001_Tareas.md` (dentro del vault) usando
la sintaxis del plugin **Tasks** de Obsidian; `sync/` las parsea y las
sube a una base de datos de Notion, usando el LLM para decidir los
valores de las propiedades que no vengan explicitas en el texto
(categoria de **Toma de decisiones**).

**Configuracion (una sola vez):**

1. Instala el plugin **Tasks** en Obsidian y en Settings > Tasks >
   Statuses agrega los estados personalizados documentados en
   `data/vault/Tareas/001_Tareas.md` (para que el checkbox refleje el
   mismo Status que usas en Notion).
2. Crea una integracion en https://www.notion.so/my-integrations,
   comparte tu base de datos con ella ("Compartir" -> invitar la
   integracion), y copia el token y el ID de la base a tu `.env`:
   ```
   NOTION_API_KEY=tu_token
   NOTION_DATABASE_ID=tu_database_id
   ```
   Si los nombres de tus propiedades no coinciden con los defaults
   (`Status`, `Fecha`, `Prioridad`, `Contexto`, `Energía`, `Proyecto`,
   `URL`), sobreescribelos con `NOTION_PROP_*` (ver `.env.example`).

   Propiedades de tipo `relation` (ej. si `Proyecto` en tu base es una
   relacion a otra base, no texto) no se completan automaticamente: se
   omiten con un aviso en consola, porque requieren el page ID de la
   pagina relacionada, no un valor de texto libre.

**Uso:**

```bash
python3 main.py --sync-notion
```

Escribe tus tareas en `Tareas/001_Tareas.md` con el formato descrito en
ese mismo archivo, y cada corrida con `--sync-notion` crea o actualiza la
pagina correspondiente en Notion (usa el marcador invisible
`%%notion:<page_id>%%` para no duplicar).

**Codigo:**

```
sync/
├── task_parser.py   # texto Markdown -> objetos Task (checkbox, fechas, prioridad, tags)
├── notion_client.py # Task -> propiedades de Notion, segun el esquema real de la base
└── notion_sync.py   # orquesta: parsea, completa campos faltantes via LLM, sube, reescribe el archivo
```
