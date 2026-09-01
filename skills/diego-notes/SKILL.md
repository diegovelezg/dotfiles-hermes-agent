---
name: diego-notes
description: Guarda notas en el ledger MCP (intel permanente) desde texto directo del usuario o desde URL. Procesa texto extrayendo título/tags/resumen; URLs se delegan a DeepSeek para extracción y síntesis.
version: 1.0.0
metadata:
  hermes:
    tags: [notes, ledger, MCP, intel, productivity]
    category: productivity
---

# Diego Notes 📝

## Objetivo

Recibir una nota del usuario — texto que él escribió o una URL — y guardarla en el ledger MCP como intel permanente. Procesamiento mínimo, sin pedir confirmación, ejecutando todo en una pasada.

## Dos modos de entrada

| Entrada | Quién procesa | Qué se guarda |
|---|---|---|
| **Texto directo** del usuario | MiniMax (este agente) | Texto literal + título limpio + tags + resumen ejecutivo corto |
| **URL** | DeepSeek V4 Flash (delegate_task) | Reporte en castellano (Resumen Ejecutivo + Resumen Destilado + Fuente) |

Regla única: nunca preguntar confirmación. Si la entrada es ambigua, asumir texto directo y ejecutar.

---

## Modo A — Texto directo

### Paso A1: Extraer metadatos del texto

A partir del texto que el usuario mandó, extraer:

- **title**: ≤80 caracteres, refleja la idea central. Si no se deduce, usar las primeras palabras relevantes del texto.
- **tags**: 3 a 7 tags temáticos en kebab-case (`arquitectura`, `python`, `idea-pendiente`, etc.). Si el texto es muy corto o no sugiere tags, usar al menos 2 genéricos (`nota`, `idea`).
- **resumen_ejecutivo**: ≤500 caracteres. Una o dos frases con la idea nuclear. Si el texto es <200 caracteres, omitir resumen y guardar el texto completo como `content`.

### Paso A2: Guardar en ledger

```
ledger_item_create(
  title="[title extraído]",
  nature="intel",
  status="permanent",
  content="[texto literal del usuario]\n\n---\nResumen: [resumen_ejecutivo o vacío]\nTags: [tag1, tag2, tag3]"
)
```

Si el texto es muy corto (<200 chars), `content` = texto literal del usuario sin adornos (sin bloque `---\nResumen`).

### Edge cases — texto

- Texto vacío o solo whitespace → no guardar nada, responder pidiendo contenido real.
- Texto con URLs embebidas → ignorar las URLs, tratar como texto.
- Texto >5000 caracteres → guardar truncado a 5000 chars en `content` con nota "(texto truncado)".

---

## Modo B — URL

**REGLA DURA (corregida 2026-08-31):** NO delegar a DeepSeek para URLs. El delegado puede colgarse >2 min sin entregar nada y bloquea la confianza del usuario. Procesar URLs directo, en cadena de fallbacks:
1. `web_extract` (puede fallar con 403 si Firecrawl keyless está sin clave — en ese caso saltar al paso 2)
2. `web_search` con query temática para encontrar abstract / versión alternativa (preprint, ePrint, mirror)
3. Usar el contenido extraído + el contexto adjunto por el usuario para sintetizar el reporte

Si el usuario provee el contenido completo de la URL pegado en el mensaje (como en el caso que motivó esta corrección), usarlo directamente sin necesidad de web tools.

Síntesis la hace MiniMax directo, sin delegate_task.

### Paso B2: Guardar en ledger

```
ledger_item_create(
  title="[Título en castellano extraído del reporte]",
  nature="intel",
  status="permanent",
  content="[Reporte completo del delegado]"
)
```

---

## Diferencia clave vs diego-read-it-later

| Aspecto | diego-read-it-later | diego-notes (texto) |
|---|---|---|
| Quién procesa | Siempre DeepSeek | MiniMax directo (texto del usuario, no requiere reescritura) |
| Contenido guardado | Reporte sintetizado por el delegado | Texto literal del usuario + metadatos |
| Cuando es URL | Idéntico | Idéntico |

---

## Uso

El usuario provee contenido (texto o URL). El skill detecta el modo:
- Si empieza con `http://` o `https://` → Modo B (URL)
- Cualquier otra cosa → Modo A (texto)

Ejecutar completo en una pasada. Nunca pedir confirmación.

---

## Recuperación

Para buscar notas guardadas:
- `ledger_query` con palabras clave → búsqueda híbrida semántica + texto exacto
- Filtrar mentalmente por `nature="intel"` (las notas son intel permanente)

---

## Notas

- No preguntar confirmaciones — ejecutar completo en una pasada
- Texto corto (<200 chars) → guardar literal sin resumen
- Texto del usuario se preserva tal cual en `content` (no reescribir ni "mejorar")
- Tags van en kebab-case, en español preferentemente
- El ledger es la memoria permanente — siempre `nature="intel"`, `status="permanent"`