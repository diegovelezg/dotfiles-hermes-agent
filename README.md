# Hermes Agent — Dotfiles

Configuración personalizada de Hermes Agent para Diego Vélez (@diegovelezg).

Stack: MiniMax-M2 como agente principal + DeepSeek (OpenRouter) para investigación + personal-ai (Mem0) como memoria persistente.

---

## Arquitectura General

```
Usuario (Telegram / Discord)
         ↓
  Hermes Gateway  (Telegram bot + Discord bot)
         ↓
  AIAgent  (MiniMax-M2 — agente principal)
         ↓
  ┌─────────────────────────────────────┐
  │  Tools nativas                      │
  │  • web_search / web_extract         │
  │  • terminal / execute_code           │
  │  • delegate_task                     │
  │  • memory (builtin + plugin)         │
  │  • mcp_* (personal-ai bridge)        │
  └─────────────────────────────────────┘
         ↓
  OpenRouter  (DeepSeek-V3 / R1 — investigación)
```

**Canal de memoria personal:** personal-ai MCP v5 (Mem0) via plugin SSE bridge.

---

## Sistema de Memoria y Ledger

### Arquitectura de plugins (SSOT)

```
MemoryManager
    ├── BuiltinMemoryProvider        ← MEMORY.md / USER.md (siempre activo)
    │                                    Memorias de trabajo y perfil de usuario
    │
    └── PersonalAIMemoryProvider     ← Plugin memory/personal-ai
         │                              Conexión SSE → personal-ai MCP
         ├── prefetch()                 → recall semántico al inicio de sesión
         ├── system_prompt_block()      → instrucciones de tools en el prompt
         ├── get_tool_schemas()         → 2 tools de memoria expuestas
         └── handle_tool_call()         → dispatch directo al MCP

PersonalAILedgerProvider            ← Plugin personal-ai-ledger
     │                                Conexión SSE → mismo MCP (SSOT)
     ├── get_tool_schemas()         → 6 tools de ledger/briefing/browser
     └── handle_tool_call()         → dispatch directo al MCP
```

**SSOT:** Ambos plugins comparten una única conexión SSE al servidor MCP `uaimcp.papelitosdecolor.com`. No hay intermediarios (sin mcporter).

### Plugins personal-ai

**Plugin memory (`plugins/memory/personal-ai/`)** — Solo tools de memoria:

| Tool | Descripción |
|------|-------------|
| `personal_ai_memories_search` | Búsqueda semántica sobre know/policy/episodic |
| `personal_ai_memories_manage` | Crear, actualizar, deprecar memorias |

**Plugin ledger (`plugins/personal-ai-ledger/`)** — Solo tools de ledger/briefing/browser:

| Tool | Descripción |
|------|-------------|
| `ledger_query` | Consultar items del ledger (action/intel) |
| `ledger_item_create` | Crear item en el ledger |
| `ledger_bulk_action` | Bulk update/archive de items del ledger |
| `briefing_generate` | Generar briefing estructurado desde ledger |
| `browser_activity_add` | Registrar actividad de navegación |
| `browser_activity_query` | Consultar historial de navegación |

**Configuración del plugin** (variables en `~/.hermes/.env`):

```bash
PERSONAL_AI_BASE_URL=https://uaimcp.papelitosdecolor.com
PERSONAL_AI_API_KEY=***
PERSONAL_AI_REMOTE_URL=https://uaimcp.papelitosdecolor.com/sse
PERSONAL_AI_USER_ID=1093162286
```

**Activar en** `~/.hermes/config.yaml`:

```yaml
memory:
  provider: personal-ai
  provider_settings:
    personal-ai:
      cache_ttl: 120
```

### Protocolo SSE del personal-ai MCP

El MCP server (`papelitosdecolor.com`) usa Server-Sent Events con sesión aislada por UUID:

- **GET `/sse`** → downstream (servidor → cliente): stream de eventos JSON-RPC
- **POST `/messages?sessionId=UUID`** → upstream (cliente → servidor): comandos y queries
- El servidor envía `endpoint` como primer evento con la URL de callback
- Heartbeats automáticos para mantener la conexión viva
- Cada sesión tiene su propia instancia aislada del servidor MCP

### Memorias en Mem0 (personal-ai MCP)

| Tipo | Descripción | Ejemplo |
|------|-------------|---------|
| `know` | Hechos persistentes sobre Diego | proyectos, personas, preferencias |
| `policy` | Reglas operativas | "Diego prefiere español, sin markdown en Telegram" |
| `episodic` | Eventos pasados | "Grupos focales completados 2-3 abr 2026" |

### Protocolo SSE del personal-ai MCP

Archivos planos en `~/.hermes/memories/`:

- `MEMORY.md` — notas de trabajo del agente (cargadas via `MemoryStore.load_from_disk`)
- `USER.md` — perfil del usuario

Estos archivos coexisten con el plugin. El plugin personal-ai es el SSOT para hechos sobre Diego; los archivos builtin se usan para notas de sesión y contexto temporal.

---

## Skills Custom de Diego

Las skills personalizadas viven en `~/.hermes/custom-skills/` y se restauran via symlinks en `~/.hermes/skills/`:

| Skill | Descripción |
|-------|-------------|
| `diego-buenos-dias` | Informe matutino con TTS para Telegram |
| `diego-read-it-later` | Extraer y guardar contenido de URLs |
| `diego-research` | Investigación estructurada con hechos atómicos |
| `diego-intel` | Briefing personalizado |

---

## Restauración Post-Update de Hermes

**Problema:** Las updates de Hermes pueden sobrescribir `~/.hermes/skills/`, borrando los symlinks a las skills custom.

**Solución:** Skills reales en `~/.hermes/custom-skills/` (directorio aislado), symlinks en `~/.hermes/skills/`.

```bash
# Después de cualquier update de Hermes:
bash ~/.hermes/custom-skills/restore.sh

# Verificar que están activas:
hermes skills list | grep diego
```

**Estructura:**

```
~/.hermes/custom-skills/          ← Backup gitado (sobrevive a updates)
  ├── diego-buenos-dias/
  ├── diego-read-it-later/
  ├── diego-research/
  ├── diego-intel/
  └── restore.sh                  ← Script de restauración

~/.hermes/skills/                 ← Symlinks (Hermes puede sobrescribir)
  ├── diego-buenos-dias → ~/.../custom-skills/diego-buenos-dias
  ├── diego-read-it-later → ~/.../custom-skills/diego-read-it-later
  ├── diego-research → ~/.../custom-skills/diego-research
  └── productivity/diego-intel → ~/.../custom-skills/diego-intel
```

**Para sincronizar cambios al repo:**

```bash
cd ~/.hermes/custom-skills
git add -A
git commit -m "descripción del cambio"
git push
```

---

## Modelos LLM

| Rol | Modelo | Provider | Uso |

**Repositorios remotos:**

| Branch | Contenido |
|--------|-----------|
| `main` | Backup completo de `~/.hermes/` (configs, cron, gateway, plugins, skills nativas, outputs) |
| `custom-skills` | Solo las skills custom de Diego (diego-buenos-dias, diego-read-it-later, diego-research, diego-intel) |

**Para sincronizar cambios al repo:**

```bash
cd ~/.hermes/custom-skills
git add -A
git commit -m "descripción del cambio"
git push
```

El branch `custom-skills` contiene únicamente las skills custom. El branch `main` tiene el backup completo.

|-----|--------|----------|-----|
| Agente principal | MiniMax-M2 | minimax | Conversación, coordinación, todas las tools |
| Investigación pesada | DeepSeek-V3 | OpenRouter | Síntesis de temas complejos |
| Razonamiento profundo | DeepSeek-R1 | OpenRouter | Análisis lógico, debugging |
| Visión | MiniMax-V06 | minimax | Análisis de imágenes |

```yaml
# ~/.hermes/config.yaml
model: "minimax/minimax-v06"
provider: "minimax"
```

---

## Web Search — Backends y Fallback

**Stack:** Exa Search (default) → Brave Search (fallback automático)

### Cómo funciona

`web_search_tool` usa `_get_backend()` que:
1. Si `config.yaml` tiene `web.backend` explícito → usa ese
2. Si no → default = `"exa"`

Cuando Exa lanza exception, el código re-ejecuta con Brave via `_get_fallback_backend("exa")`.

### Keys requeridas

```bash
EXA_API_KEY=***
BRAVE_API_KEY=***
```

**Nota Brave:** Necesita plan "Data for Search" (no "Data for AI"). Keys `BSA*` del plan AI no funcionan.

### Cadena completa

```
web_search  → exa ──fail──→ brave ──fail──→ firecrawl
web_extract → firecrawl → parallel → tavily
```

---

## Flujo de Investigación (patrón estándar)

```
1. web_search (Exa, limit=5)
   ↓
2. web_extract (las 3-5 URLs más relevantes)
   ↓
3. Síntesis con DeepSeek-V3 via OpenRouter
```

---

## Patches Aplicados

### 1. `tools/web_tools.py` — Brave Search

**Problema:** Endpoint incorrecto (`reso/v1/`) y auth wrong para Brave API.

**Cambios:**
- Endpoint: `reso/v1/search` → `res/v1/web/search`
- Auth: `Authorization: Bearer` → `X-Subscription-Token`
- HTTP client: `urllib` → `httpx` (gzip decompression automático)
- `_get_backend()`: default "exa"
- `_get_fallback_backend()`: nueva función (exa → brave)
- Bloque try/except en `web_search_tool` para fallback automático

```bash
# Reaplicar después de update del agent:
cd ~/dotfiles-hermes-agent
patch -p1 < patches/brave-search.patch
```

### 2. `tools/delegate_tool.py` — Model/Provider override

**Problema:** los parámetros `model` y `provider` eran ignorados al delegar.

---

## Gateway y Plataformas

### Status

| Plataforma | Status | ID/Destino |
|-----------|--------|------------|
| Telegram | Conectado ✓ | DM y Home: 1093162286 |
| Discord | Conectado ✓ | Home: 1474242034356326442 |

### Startup

```bash
# Con systemd
systemctl --user start hermes-gateway
systemctl --user enable hermes-gateway

# Logs
journalctl --user -u hermes-gateway -f

# Restart después de cambios
systemctl --user restart hermes-gateway
```

---

## Cron Jobs

### Buenos Días

- **Job ID:** `20257ad8ddf4`
- **Schedule:** Daily 7:00 AM Lima (12 UTC)
- **Delivery:** Telegram
- **Sources:** Histórico, Techmeme, AI Twitter, ScienceDaily, BigThink
- **Output:** `skills/buenos-dias/output/hoy.ogg` + `.md` con fecha

---

## Configuración de Archivos

### `~/.hermes/config.yaml`

```yaml
model: "minimax/minimax-v06"
provider: "minimax"

web:
  backend: exa

delegation:
  provider: "openrouter"
  model: "deepseek/deepseek-chat-v3"

display:
  model: "anthropic/claude-sonnet-4"

gateway:
  platform: telegram
  telegram:
    bot_token: "${TELEGRAM_BOT_TOKEN}"

memory:
  provider: personal-ai
```

### `~/.hermes/.env` (NUNCA subir al repo)

```
MINIMAX_API_KEY=***
OPENROUTER_API_KEY=***
EXA_API_KEY=***
BRAVE_API_KEY=***
PERSONAL_AI_API_KEY=***
PERSONAL_AI_BASE_URL=https://uaimcp.papelitosdecolor.com
PERSONAL_AI_REMOTE_URL=https://uaimcp.papelitosdecolor.com/sse
PERSONAL_AI_USER_ID=1093162286
TELEGRAM_BOT_TOKEN=***
DISCORD_BOT_TOKEN=***
```

Template público: `configs/.env.example`

---

## Estructura del Repo

```
dotfiles-hermes-agent/
├── configs/
│   ├── config.yaml          # Config principal (sin secrets)
│   ├── .env.example         # Template de variables
│   └── gateway_*.json       # Estado de canales
├── plugins/
│   ├── memory/
│   │   └── personal-ai/     # Plugin memory — solo tools de memoria
│   │       ├── __init__.py  # PersonalAIMemoryProvider + PersonalAIClient
│   │       ├── plugin.yaml  # Metadata + pip_dependencies
│   │       └── README.md    # Documentación del plugin
│   └── personal-ai-ledger/   # Plugin ledger — tools de ledger/briefing/browser
│       ├── __init__.py      # PersonalAILedgerProvider + PersonalAIClient
│       └── plugin.yaml      # Metadata
├── skills/                  # 29 skills instalados
├── scripts/
│   └── backup.sh            # Backup idempotente
├── patches/
│   └── brave-search.patch   # Patch para tools/web_tools.py
└── docs/
    └── ARQUITECTURA.md      # Detalle técnico adicional
```

**Directorios del runtime `~/.hermes/` (no en repo):**

- `memories/` — MEMORY.md y USER.md (builtin memory provider)
- `sessions/` — sesiones activas del gateway
- `cron/` — jobs programados
- `skills/` — skills runtime (symlink o copia)

---

## Notas Importantes

1. **API Keys**: nunca subirlas. Usar `.env.example` como template.
2. **Patches**: reaplicar `patches/brave-search.patch` después de actualizar hermes-agent.
3. **delegate_task**: no usar para research — trunca resultados. Preferir `terminal` + Python para llamadas OpenRouter.
4. **execute_code**: no confiable para APIs externas por timeouts de 30s. Preferir `terminal`.
5. **Brave API**: necesita plan "Data for Search" (no "Data for AI").
6. **SDK rewrite test memory**: existe físicamente en Mem0 pero no puede borrarse via MCP server (bug: IDs de search no resuelven en Mem0 update/delete). Filtrada client-side en prefetch y search. Solo afecta al plugin de memory.
7. **Hooks**: no hay hooks activos. El directorio `hooks/` está vacío.
8. **Sandboxes**: sin imágenes. El directorio `sandboxes/` está vacío.

---

## Comandos Útiles

```bash
# Backup de configs y skills
./scripts/backup.sh

# Ver estado del gateway
systemctl --user status hermes-gateway

# Ver logs en tiempo real
journalctl --user -u hermes-gateway -f

# Reiniciar después de cambios
systemctl --user restart hermes-gateway

# Verificar tools disponibles
hermes tools list

# Ver estado de memory providers
hermes doctor
```
