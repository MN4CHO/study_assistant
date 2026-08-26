# Tareas

Escribe aca todas las tareas que quieras sincronizar con Notion, usando la
sintaxis del plugin **Tasks** de Obsidian. Esta carpeta (`Tareas`) esta
excluida del pipeline de apuntes (`EXCLUDED_DIR_NAME` en `config.py`), asi
que `main.py --sync-notion` es lo unico que la toca.

## Configuracion previa del plugin Tasks (una sola vez)

Settings > Tasks > Statuses, agrega estos estados personalizados para que
el checkbox refleje el mismo "Status" que usas en Notion:

| Caracter | Estado en Obsidian | Status en Notion |
|---|---|---|
| `[ ]` | Todo | Inbox |
| `[/]` | En proceso | En proceso |
| `[w]` | Esperando | Esperando |
| `[d]` | Delegada | Delegada |
| `[x]` | Completado | Completed |

## Formato de una tarea

```
- [w] Titulo de la tarea 🛫 2026-07-06 📅 2026-07-06 [hora:: 13:00-16:00] ⏫ #proyecto/Kaizen #contexto/University #energia/Extreme
```

- `🛫 fecha` / `📅 fecha`: inicio / fecha (due). Reconocidas nativamente por Tasks.
- `[hora:: HH:MM-HH:MM]`: rango horario del mismo dia (Tasks no maneja horas).
- `🔺` Urgente, `⏫` Alta, `🔼` Media, `🔽` Baja, `⏬` Minima.
- `#proyecto/...`, `#contexto/...`, `#energia/...`: opcionales. Si los omites,
  el script le pide al LLM que elija el valor mas apropiado entre las
  opciones reales de tu base de Notion.
- Despues del primer `--sync-notion`, el script agrega automaticamente
  `%%notion:<page_id>%%` al final de la linea (invisible en Obsidian): no
  lo borres, es lo que evita crear una tarea duplicada en cada corrida.

## Ejemplos

- [ ] Repasar Normalizacion de Bases de Datos 📅 2026-08-28 ⏫ #proyecto/Kaizen #contexto/University
- [w] Entregar practica de Modelo OSI 🛫 2026-08-27 📅 2026-08-29 [hora:: 13:00-16:00] 🔺 #contexto/University
