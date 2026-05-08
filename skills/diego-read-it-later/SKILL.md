---
name: diego-read-it-later
description: Navega a una URL, extrae su contenido y genera un reporte estructurado listo para guardar en el sistema MCP como intel permanente.
version: 4.0.0
metadata:
  hermes:
    tags: [read-it-later, web, extraction, intel, MCP]
    category: productivity
---

# Read It Later 📄

## Objetivo

Navegar a una URL, extraer su contenido, generar un reporte estructurado en castellano y guardarlo inmediatamente en el ledger de MCP como intel permanente.

## Arquitectura

Este skill usa **dos modelos**:

- **MiniMax** (agente principal): orquesta el flujo y guarda en el ledger
- **DeepSeek V4 Flash** (delegado): extrae contenido y sintetiza el reporte en castellano

```
MiniMax → delegate_task → extraer URL + sintetizar reporte
       ← reporte en castellano ←
MiniMax → ledger_item_create
```

El modelo para delegate_task se toma del default en config.yaml (deepseek/deepseek-v4-flash).

## Paso 1: Extraer y sintetizar con DeepSeek (delegar)

Usar `delegate_task` para extraer el contenido de la URL Y generar el reporte en castellano en una sola llamada:

```
delegate_task(
  goal="Navega a [URL] y extrae su contenido completo. Luego, redacta un reporte en CASTELLANO con esta estructura exacta:

## Resumen Ejecutivo
[Máximo 500 caracteres. Descripción breve de qué trata el artículo.]

## Resumen Destilado
[Máximo 300 palabras. Principales puntos en narrativa, sin bullets ni listas.]

## Fuente Original
[URL exacta]

Devuelve SOLO el reporte completo, sin comentarios tuyos ni notas adicionales.",
  context="El usuario quiere guardar este artículo para leer después. Extrae todo el contenido relevante y sintetízalo en castellano. Si la URL no es accesible, intentá con un preprint o versión alternativa (arXiv, ePrint). Si no hay nada, usá web_search para encontrar un abstract."
)
```

**Fallback:** Si el delegate falla, usar `web_extract` directamente. Si también falla, buscar con `web_search` y construir el reporte desde ahí.

## Paso 2: Guardar en MCP

Con el reporte en castellano, guardar inmediatamente en el ledger:

| Campo   | Valor                                                                |
|---------|----------------------------------------------------------------------|
| title   | Título del artículo en CASTELLANO                                   |
| content | El reporte completo (Resumen Ejecutivo + Resumen Destilado + Fuente Original) |
| nature  | "intel"                                                              |
| status  | "permanent"                                                          |

```
ledger_item_create(
  title="[Título en castellano]",
  nature="intel",
  status="permanent",
  content="[Reporte completo]"
)
```

## Estructura de archivos

```
~/.hermes/skills/diego-read-it-later/output/
  YYYY-MM-DD-URL-SLUG.md   # Reporte guardado localmente por si se necesita
```

## Uso

El usuario provee una URL. El skill ejecuta los pasos en secuencia automática.

## Notas

- No preguntar confirmaciones — ejecutar completo en una pasada
- Síntesis → DeepSeek (delegate_task), no el agente principal
- MiniMax solo orquesta y guarda en ledger
- El ledger es la memoria permanente — siempre guardar como intel "permanent"
- Para找回 posteriores: usar `ledger_query` para buscar por título o contenido
