---
name: personal-ai-bridge
description: Bridge skill that exposes the personal-ai MCP server (ledger tools) via mcporter. Includes ledger search/create, memories, browser activity, and briefing generation.
version: 1.0.0
author: hermes
license: MIT
metadata:
  hermes:
    tags: [personal-ai, ledger, memories, bridge, mcporter]
---

# personal-ai-bridge

Bridge skill that invokes the personal-ai MCP server tools via `mcporter` CLI.
The server name for mcporter is `personal-ai`. Credentials and endpoint are sourced from `~/.hermes/config.yaml` (`mcp_servers.personal-ai`) — mcporter references the same values.

## ⚠️ Root Cause — Why This Bridge Exists

The MCP Python SDK (hermes-agent) fails to connect to this server because of a timing bug:
- The SDK sends POST /initialize to `/sse` BEFORE reading the sessionId from the SSE stream
- The server responds HTTP 404 → "Session terminated"
- mcporter (Node.js) works because it waits for the `endpoint` SSE event before sending any POST

**Solution:** Use mcporter as the transport layer instead of the Python SDK.

## 📋 Available Tools

All calls follow this pattern:
```bash
npx -y mcporter call personal-ai.<tool_name> --args '...' --output json
```

---

## LEDGER — Ítems personales (tareas e información)

### ledger_query
**Purpose:** Búsqueda híbrida inteligente en el ledger.
Combina búsqueda de texto exacto con búsqueda semántica.

```bash
npx -y mcporter call personal-ai.ledger_query query="términos" limit=5 --output json
```

**Params:**
- `query` (string): Términos de búsqueda en lenguaje natural
- `status` (string, optional): inbox | todo | doing | review | done | dismissed | archived | permanent
- `nature` (string, optional): action (tarea) | intel (información)
- `limit` (number, default 50): Máximo de resultados
- `include_archived` (boolean, default false): Incluir ítems archivados
- `pending_ai` (boolean, optional): Solo ítems pendientes de procesamiento IA
- `timezone` (string, optional): ej "America/Lima"
- `id` (uuid, optional): Buscar por ID exacto

**Example response parsing:**
```python
data = json.loads(output)
items = data['data']['sample_items']
for item in items:
    print(f"- {item['title']} [{item['status']}]")
```

---

### ledger_item_create
**Purpose:** Crear un nuevo ítem en el ledger.

```bash
npx -y mcporter call personal-ai.ledger_item_create title="Título" nature="action" status="inbox" --output json
```

**Params:**
- `title` (string, **required**): Título del ítem
- `nature` (string, **required**): action (tarea) | intel (información)
- `status` (string, optional): Estado inicial (default: inbox para action, permanent para intel)
- `content` (string, optional): Descripción/contenido inicial
- `subject` (string, optional): Sujeto/materia principal (ej: "@trabajo", "@salud")
- `priority` (string, optional): low | medium | high | urgent (solo para action)
- `resolver` (string, optional): human | ai (quien resuelve, default: human)
- `due_at` (datetime, optional): Fecha límite ISO 8601
- `timezone` (string, optional): ej "America/Lima"

**Returns:** Los 13 campos estándar del ítem creado (id, title, status, nature, etc.)

---

### ledger_bulk_action
**Purpose:** Acción masiva sobre IDs explícitos del ledger.

```bash
npx -y mcporter call personal-ai.ledger_bulk_action ids='["id1","id2"]' note="nota" status="done" --output json
```

**Params:**
- `ids` (array of uuid, **required**): Lista de IDs de ítems
- `note` (string, **required**): Nota/log de la acción
- `status` (string, optional): Nuevo estado
- `priority` (string, optional): low | medium | high | urgent
- `subject` (string, optional): Nuevo sujeto
- `title` (string, optional): Nuevo título
- `content` (string, optional): Nuevo contenido
- `agent_name` (string, optional): Nombre del agente que ejecuta
- `due_at` (datetime, optional): Nueva fecha límite
- `timezone` (string, optional): ej "America/Lima"

---

## MEMORIES — Memoria y conocimiento personal

### memories_search
**Purpose:** Búsqueda semántica en memorias. Busca en Mem0 (vector store).

**⚠️ IMPORTANT:** Para buscar conocimiento personal (type="know" o "episodic") se requiere `user_id`.

```bash
npx -y mcporter call personal-ai.memories_search query="qué sabes de X" type="know" user_id="TU_USER_ID" limit=5 --output json
# TODO (future): parametrizar user_id desde config.yaml (ej: mcp_servers.personal-ai.user_id)
```

**Params:**
- `query` (string, **required**): Texto para buscar memorias similares
- `type` (string, optional): policy | know | episodic
  - `policy`: Reglas operativas públicas
  - `know`: Conocimiento personal
  - `episodic`: Episodios/memórias autobiográficas
- `limit` (number, default 10): Máximo de resultados
- `timezone` (string, optional): ej "America/Lima"
- `user_id` (string, **required** for know/episodic): ID del usuario. Valor: `1093162286` (Telegram ID). TODO (future): parametrizar desde config.yaml.

---

### memory_manage
**Purpose:** Gestiona reglas operativas (policies) o memorias personales.
- Policies → van a Supabase como reglas estructurales
- know/episodic → van a Mem0 como hechos semánticos

```bash
# Crear una policy
npx -y mcporter call personal-ai.memory_manage action="create" content="Cuando llegue email de X, hacer Y" type="policy" unique_key="email-x-rule" --output json
# Para know/episodic: user_id = 1093162286 (Telegram ID). TODO (future): parametrizar desde config.yaml

# Usar una policy existente
npx -y mcporter call personal-ai.memory_manage action="use" id="UUID-DE-POLICY" --output json

# Deprecar una policy
npx -y mcporter call personal-ai.memory_manage action="deprecate" id="UUID-DE-POLICY" --output json
```

**Params:**
- `action` (string, **required**): create | update | use | deprecate
- `id` (uuid, **required** for update/use/deprecate): ID de la regla/memoria
- `content` (string, optional): Contenido de la regla o memoria
- `type` (string, optional): policy | know | episodic
- `context` (string, optional): Contexto adicional en texto
- `agent_id` (string, optional): ID del agente al que aplica (solo policy)
- `input_source` (string, optional): Fuente de entrada (ej: "email", "slack") (solo policy)
- `unique_key` (string, optional): Identificador único para evitar duplicados (solo policy)
- `timezone` (string, optional): ej "America/Lima"
- `user_id` (string, **required** for know/episodic): ID del usuario. Valor: `1093162286` (Telegram ID). TODO (future): parametrizar desde config.yaml.

---

## BROWSER ACTIVITY — Chrome Extension

These tools integrate with a Chrome Extension that tracks browsing activity.

### browser_activity_add
**Purpose:** Registrar actividad del navegador (desde Chrome Extension).
Vectoriza el summary para búsqueda semántica.

```bash
npx -y mcporter call personal-ai.browser_activity_add site="GitHub" title="Repo X" summary="Exploré el repo de Y" url="https://github.com/..." --output json
```

**Params:**
- `site` (string, **required**): Nombre del sitio (ej: "GitHub", "Youtube", "Twitter")
- `title` (string, optional): Título de la página
- `summary` (string, **required**): Resumen generado por la extensión
- `url` (string, optional): URL completa visitada
- `duration` (number, optional): Segundos de permanencia activa
- `metadata` (object, optional): Datos extra opcionales

---

### browser_activity_query
**Purpose:** Buscar actividades del navegador.
Híbrido: texto exacto en site/url y semántico en summary.

```bash
npx -y mcporter call personal-ai.browser_activity_query query="repo python" site="github.com" limit=5 --output json
```

**Params:**
- `query` (string, optional): Términos de búsqueda (semántico en summary)
- `site` (string, optional): Filtrar por sitio (ej: "github.com", "youtube.com")
- `limit` (number, default 10): Máximo de resultados
- `match_threshold` (number, default 0.5): Umbral de similitud (0-1)

---

## BRIEFING — Resumen diario inteligente

### briefing_generate
**Purpose:** Genera briefing diario basado en el estado actual del ledger y memorias previas.
Análisis táctico + cognitivo + conexiones + radar + CTA.

```bash
npx -y mcporter call personal-ai.briefing_generate timezone="America/Lima" --output json
```

**Params:**
- `timezone` (string, optional): Timezone del usuario (ej: "America/Lima")

**Returns:**
```json
{
  "status": "success",
  "data": {
    "content": "1. **SÍNTESIS TÁCTICA:** ...\n2. **ANÁLISIS COGNITIVO:** ...\n3. **CONEXIONES (INSIGHT):** ...\n4. **RADAR (+7d):** ...\n5. **PRIMER PASO (CTA):** ...",
    "rational": "Justificación del briefing...",
    "stats": {"inbox": N, "kanban": N, "urgent": N},
    "persistence": {"summaries": "success", "mem0": "success"}
  }
}
```

---

## 🔧 Configuration

**SSOT:** Credential data lives in `~/.hermes/config.yaml` under `mcp_servers.personal-ai`.
mcporter is pre-configured to use those same values — no separate credentials needed.

- **Server name (mcporter):** `personal-ai`
- **Config path (Hermes):** `mcp_servers.personal-ai`

To verify configuration:
```bash
npx -y mcporter config list
grep -A3 "personal-ai" ~/.hermes/config.yaml
```

---

## 📝 Usage Examples for Diego

```
"Genera mi briefing diario"
→ ledger_query + memorias + análisis

"Busca en mi ledger tareas sobre [tema]"
→ ledger_query with nature="action"

"Busca en mis memorias información sobre [tema]"
→ memories_search with type="know", user_id="..."

"Crea una tarea: [título]"
→ ledger_item_create with nature="action"

"Marca las siguientes tareas como done: [ids]"
→ ledger_bulk_action with status="done"

"Qué hice en el navegador lately?"
→ browser_activity_query

"Registra esta página: [título] - [resumen]"
→ browser_activity_add
```
