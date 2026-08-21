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
└── data/vault/                 # notas de ejemplo (reemplazar por tu vault real)
```

## 6. Mapeo a la rubrica del proyecto

| Modulo | Categoria de resultado de IA |
|---|---|
| `quiz_generator.py`, `handwriting_reader.py` | **Automatizacion** |
| `topic_prioritizer.py` | **Identificacion de patrones** |
| `topic_prioritizer.suggest_priorities()` (recomendaciones basadas en tu propio historial de apuntes) | **Personalizacion** |

## 7. Proximos pasos (Fase 2, fuera del alcance actual)

- Sincronizacion Obsidian (plugin Tasks) -> Notion, usando el LLM para
  decidir los valores correctos de cada propiedad de la base de Notion
  (categoria de **Toma de decisiones**).
