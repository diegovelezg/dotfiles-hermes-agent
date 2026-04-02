---
name: intel-reader
description: Procesa URLs, genera reporte estructurado y lo guarda en el MCP Personal AI del usuario
---

# Intel Reader Skill 📰

## Objetivo
Navegar a una URL, extraer su contenido, generar un reporte estructurado en castellano, y guardarlo en el MCP Personal AI del usuario via ledger_item_create.

## Herramientas usadas
- `mcp_web_extract` — extraer contenido de la URL
- `mcp_execute_code` — procesar y truncar texto
- `mcporter` — invocar ledger_item_create del MCP Personal AI

## Flujo

### Paso 1: Extraer contenido

Usar `mcp_web_extract` con la URL proporcionada:

```
mcp_web_extract(urls=["URL_DEL_USUARIO"])
```

Si la extracción falla (error, contenido vacío, o texto tipo "checking third-party user token"), usar `mcp_web_search` como fallback:

```
mcp_web_search(query="TÍTULO DEL ARTÍCULO site:DOMINIO_O_FUENTE")
```

De los resultados de search, usar `results[0].description` y `results[0].title` para construir el reporte. En casos de paywall o anti-bot severo, priorizar el snippet del search y标注 que el contenido completo puede requerir suscripción.

### Paso 2: Generar reporte en CASTELLANO

Del contenido extraído, generar:

- **Título**: extraído de `results[0].title` o inferido del contenido
- **Resumen Ejecutivo** (máx 500 caracteres): descripción breve de qué trata el contenido
- **Resumen Destilado** (máx 300 palabras): principales puntos en narrativa fluida, sin bullets
- **Fuente Original**: `results[0].url`

### Paso 3: Guardar en MCP Personal AI

Usar `mcporter` para invocar `ledger_item_create`:

```bash
npx -y mcporter call personal-ai.ledger_item_create \
  --args '{"title":"TÍTULO","nature":"intel","status":"permanent","content":"RESUMEN EJECUTIVO\n\nRESUMEN DESTILADO\n\nFuente: URL"}' \
  --output json
```

Verificado: requiere clave `mcpServers` (no `servers`) en `~/.mcporter/mcporter.json` y URL con `/sse` al final.

** mcporter** se invoca con `npx -y mcporter call personal-ai.ledger_item_create`. No necesita path local — npx lo resuelve.

## Reglas
- Siempre en CASTELLANO
- No preguntar — hacer directo después de extraer
- Si la extracción falla, guardar igual con lo disponible (título + enlace)
- Truncar: ejecutivo a 500 chars, destilado a 300 palabras
- Prescindir de browser-browse, relay, y cualquier dependencia externa
