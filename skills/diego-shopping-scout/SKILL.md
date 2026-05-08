---
name: diego-shopping-scout
description: Monitorea y compara precios de cualquier producto o servicio usando búsqueda web y extracción de contenido. Genera reportes con tendencias y cambios.
version: 1.0.0
metadata:
  hermes:
    tags: [shopping, price-tracker, web-search, comparison]
    category: productivity
---

# Shopping Scout 🛒

## Objetivo

Buscar, comparar y monitorear precios de cualquier cosa — productos, vuelos, servicios, etc. Detecta cambios de precio entre ejecuciones y muestra tendencias.

## Arquitectura

```
User → web_search (mapa mercado)
     → web_extract (precios de top URLs)
     → analyze (comparar con historial)
     → format_report (Discord/Telegram)
     → save (output/prices/{id}.json)
```

## Paso 1: Obtener query

Si el usuario no provee query, usar `mcp_clarify` para pedirla.

## Paso 2: Buscar en la web

Usar `web_search` con la query para obtener URLs del mercado:

```
web_search(query="ASUS NUC 14 Peru", limit=15)
```

## Paso 3: Extraer precios

De las URLs relevantes, usar `web_extract` para obtener el contenido de cada una.

**Regex de extracción** (implementado en `scripts/check_prices.py`):
- **Soles:** `S/\s*([\d.,]+)`
- **USD:** `\$\s*([\d.,]+)`

Usar `scripts/check_prices.py` para procesar los resultados — invocar vía `terminal` (no `execute_code`, ver Pits):
```
terminal(command="python3 /tmp/check_prices.py ...")
```
Alternativamente, escribir el script a `/tmp/` fresco cada vez con `write_file` y ejecutarlo con `terminal`.

## Paso 4: Cargar historial previo

Leer `output/prices/{id}.json`. Si existe y tiene datos previos, cargar el último snapshot.

## Paso 5: Analizar cambios

Usar `scripts/check_prices.py analyze` con el historial previo y los precios actuales para detectar:
- Nuevos proveedores
- Proveedores eliminados
- Cambios de precio > 0.5%

## Paso 6: Guardar resultados

```python
# Guardar en output/prices/{id}.json
# Estructura: { query, history: { timestamp: { prices } } }
write_file(output/prices/{id}.json, json.dumps(data, indent=2))
```

## Paso 7: Formatear reporte

Generar reporte legible para Discord/Telegram:

```
🛒 **{query}** ({fecha})

📈/*📉 Cambios:
• dominio.com: S/XXX (+2.1%)

💰 Precios:
1. dominio1.com: S/XXX
2. dominio2.com: S/XXX
```

## Gestión de queries (avanzado)

### Agregar query
```python
# Leer output/config.json
# Agregar { "id": "...", "query": "...", "active": true, "created": "YYYY-MM-DD" }
# Guardar
```

### Listar queries
```python
# Leer output/config.json → mostrar todos
```

### Pausar/reanudar
```python
# Editar output/config.json → toggle active
```

### Eliminar query
```python
# Eliminar entrada de config.json
# Opcional: eliminar output/prices/{id}.json
```

## Archivo de configuración

`output/config.json`:
```json
{
  "queries": []
}
```

## Archivo de historial

`output/prices/{id}.json`:
```json
{
  "query": "ASUS NUC 14 Peru",
  "id": "asus-nuc-14-peru",
  "history": {}
}
```

## Scheduling

Para monitoreo recurrente, crear un cron job:

```python
mcp_cronjob(
  action="create",
  name="Shopping Scout: {query}",
  prompt="Ejecuta el skill shopping-scout con la query guardada en output/config.json para cada query activa.",
  schedule="8am,8pm",
  deliver="origin",
  skill="shopping-scout"
)
```

## Notas

- No usar npm packages de OpenClaw (omnisearch, extract) — usar herramientas nativas de Hermes
- `.env` leer de `~/.hermes/.env` si se necesitan API keys
- El ID del query se genera sanitizando el query: espacios → guiones, caracteres especiales removidos
- Los reportes van a `origin` (chat actual) por defecto

## Pits / Problemas conocidos

### Python sandbox caching (execute_code / terminal)
El sandbox de `execute_code` mantiene cache del script entre ejecuciones si el contenido es idéntico o si se usa la misma ruta de archivo (`/tmp/...`). **Solución:** al re-ejecutar un script modificado, usar una ruta nueva cada vez, o usar `terminal` con `python3 /dev/stdin << 'PYEOF'` (heredoc), o escribir el archivo con `write_file` y ejecutar desde ahí. Esto aplica tanto a `execute_code` como a `terminal` cuando llaman scripts Python.

### Múltiples queries en un solo reporte (cron)
Cuando se monitorean múltiples queries activas en una sola ejecución, **generar un reporte separado por producto** (con su propio bloque 🛒). No combinar todos los productos en un solo reporte — cada query es independiente y el usuario quiere ver cambios individuales. Ver ejemplo de formato en Paso 7.
