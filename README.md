# Hermes Agent — Configuración y Arquitectura

## Overview

Setup personalizado de Hermes Agent (Claude Code) para Diego Vélez. Coordina MiniMax como agente principal con DeepSeek (OpenRouter) para investigación pesada, y múltiples backends de búsqueda web con fallback automático.

---

## Arquitectura General

```
Usuario (Telegram/Discord)
        ↓
  Hermes Gateway
        ↓
  AIAgent (MiniMax-M2) ← agente principal, coordina todo
        ↓
  ┌─────────────────────────────────────┐
  │  Tools: web_search, web_extract     │
  │          delegate_task, terminal   │
  │          execute_code, memory       │
  │          mcp_* (personal-ai bridge) │
  └─────────────────────────────────────┘
        ↓
  Subagentes opcionales (delegate_task)
  └─ modelo + provider override
        ↓
  OpenRouter API (DeepSeek-V3/R1)
```

---

## Sistema de Memorias

### Arquitectura de memoria dual (v0.7.0 + plugin)

Hermes v0.7.0 introduce un sistema de memory providers pluggables. Nuestra implementación usa:

#### 1. Builtin Memory Provider (siempre activo)

Archivos planos que se cargan via `MemoryStore.load_from_disk()`:

- `~/.hermes/memories/MEMORY.md` — notas de trabajo del agente
- `~/.hermes/memories/USER.md` — perfil del usuario

#### 2. Personal AI Memory Provider Plugin (v1.0.0)

Plugin nativo en `plugins/memory/personal-ai/`. Integra el MCP personal-ai v5 (Mem0-backed) como provider de primera clase.

- **SSOT**: personal-ai MCP — sin escritura intermedia a MEMORY.md
- **7 tools expuestas** al modelo: search, memories_manage, briefing_generate, ledger_*, browser_activity_query
- **Lifecycle nativo**: initialize/prefetch/sync_turn llamados por MemoryManager
- **Cache TTL**: 120s en prefetch para evitar llamadas redundantes

**Flujo (v0.7.0 + plugin):**
```
AIAgent.__init__
    → MemoryManager.add_provider(BuiltinMemoryProvider)
    → MemoryManager.add_provider(PersonalAIMemoryProvider)
    → initialize() → SSE connect a personal-ai MCP
    → prefetch() → recall semántico (cached)
    → get_tool_schemas() → 7 tools disponibles al modelo
```

**Config:**
```yaml
# ~/.hermes/config.yaml
memory:
  provider: personal-ai
  provider_settings:
    personal_ai:
      cache_ttl: 120
```

**Plugin estructura:**
```
plugins/memory/personal-ai/
├── __init__.py      # PersonalAIMemoryProvider + PersonalAIClient
├── plugin.yaml      # Metadata, pip_dependencies
└── README.md        # Documentación completa
```

### Hook legacy (deprecado — mantener temporalmente)

```
~/.hermes/hooks/personal-ai-memory-loader/
├── HOOK.yaml       # eventos + credenciales
└── handler.py      # lógica legacy via SSE
```

Una vez el plugin verificado funcional, remover este hook y limpiar la sección `<!-- PERSONAL-AI-INJECT -->` de MEMORY.md.

### Tipos de memoria personal-ai

| Tipo | Descripción |
|------|-------------|
| `know` | Hechos persistentes sobre Diego (preferencias, proyectos, personas) |
| `policy` | Reglas operativas (ej: "Diego prefiere español, sin markdown") |
| `episodic` | Eventos pasados (ej: "Grupos focales completados 2-3 abr 2026") |

---

## Modelos LLM

| Rol | Modelo | Provider | Uso |
|-----|--------|----------|-----|
| Agente principal | MiniMax-M2 | minimax | Conversación, coordinación |
| Análisis pesado | DeepSeek-V3 | OpenRouter | Síntesis de investigación |
| Razonamiento | DeepSeek-R1 | OpenRouter | Análisis profundo |
| Visión | MiniMax-V06 | minimax | Imágenes |

---

## Web Search — Backends y Fallback

### Stack configurado

**Default: Exa Search** → **Fallback: Brave Search**

### Cómo funciona

`web_search_tool` usa `_get_backend()` que:
1. Si `config.yaml` tiene `web.backend` explícito → usa ese
2. Si no → default = `"exa"`

Cuando Exa falla (exception), el código en `web_search_tool` llama a `_get_fallback_backend("exa")` → retorna `"brave"`, y re-ejecuta con Brave.

### Keys requeridas

```bash
EXA_API_KEY=c785be...6808
BRAVE_API_KEY=BSAoyn...y4Mt
```

Ambas configuradas en `~/.hermes/.env`.

### Fallback chain completo (todos los backends)

```
web_search → exa ──fail──→ brave ──fail──→ firecrawl
web_extract → firecrawl → parallel → tavily
```

---

## Flujo de Investigación ( patrón estándar )

```
1. web_search (Exa, limit=5)
   ↓
2. web_extract (las 3-5 URLs más relevantes)
   ↓
3. Synthesis con DeepSeek-V3 via OpenRouter
```

---

## Patches Activos

### 1. `tools/web_tools.py` — Brave Search

**Problema original**: Endpoint incorrecto y auth wrong para Brave API.

**Cambios**:
- `_brave_search_request()`: usa `httpx` con `X-Subscription-Token` header (no Bearer)
- `_brave_search()`: endpoint `web/search` (no `search`)
- `_get_backend()`: default "exa" (antes fallback automático por presencia de key)
- `_get_fallback_backend()`: nueva función (exa → brave)
- Bloque try/except en `web_search_tool` para fallback automático de Exa → Brave

**Archivo del patch**: `patches/brave-search.patch`

```bash
# Para reaplicar después de un update del agent:
cd ~/dotfiles-hermes-agent
patch -p1 < patches/brave-search.patch
```

### 2. `tools/delegate_tool.py` — Model/Provider override

**Problema**: los parámetros `model` y `provider` eran ignorados al delegar.

---

## Configuración de Archivos

### `~/.hermes/config.yaml`

```yaml
# Modelo y provider por defecto
model: "minimax/minimax-v06"
provider: "minimax"

# Web search
web:
  backend: exa          # explicit, sin esto default = exa

# Delegation defaults
delegation:
  provider: "openrouter"
  model: "deepseek/deepseek-chat-v3"

# Display
display:
  model: "anthropic/claude-sonnet-4"

# Gateway
gateway:
  platform: telegram
  telegram:
    bot_token: "${TELEGRAM_BOT_TOKEN}"
```

### `~/.hermes/.env` (NO subir al repo)

```
MINIMAX_API_KEY=***
OPENROUTER_API_KEY=***
EXA_API_KEY=c785be...6808
BRAVE_API_KEY=BSAoyn...y4Mt
PERSONAL_AI_API_KEY=***
TELEGRAM_BOT_TOKEN=***
DISCORD_BOT_TOKEN=***
```

Template de referencia: `configs/.env.example`

---

## Gateway y Plataformas

### Status

| Plataforma | Status | ID/Destino |
|-----------|--------|------------|
| Telegram | Conectado ✓ | DM, Home: 1093162286 |
| Discord | Conectado ✓ | Home: 1474242034356326442 |

### Gateway startup

```bash
# Con systemd (linger habilitado)
systemctl --user start hermes-gateway
systemctl --user enable hermes-gateway

# O manual
cd ~/dotfiles-hermes-agent
source venv/bin/activate
python -m gateway.run
```

---

## Cron Jobs

### Buenos Días

- **Job ID**: `20257ad8ddf4`
- **Schedule**: Daily 7:00 AM Lima (12 UTC)
- **Delivery**: Telegram
- **Sources**: Histórico, Techmeme, AI Twitter, ScienceDaily, BigThink
- **Output**: `skills/buenos-dias/output/hoy.ogg` + `.md` con fecha

---

## Comandos Útiles

```bash
# Backup de configs y skills
./scripts/backup.sh

# Ver estado del gateway
systemctl --user status hermes-gateway

# Logs del gateway
journalctl --user -u hermes-gateway -f

# Restart después de cambios
systemctl --user restart hermes-gateway
```

---

## Notas Importantes

1. **API Keys**: nunca subirlas al repo. Usar `.env.example` como template.
2. **Patches**: después de actualizar `hermes-agent`, reaplicar `patches/brave-search.patch`.
3. **delegate_task**: NO usar para research — truncó resultados a ~500 chars. Usar `terminal` + Python para llamadas OpenRouter.
4. **execute_code**: no confiable para APIs externas por timeouts de 30s. Preferir `terminal`.
5. **Brave API**: necesita plan "Data for Search" (no "Data for AI"). Keys `BSA*` del plan AI no funcionan.
6. **Memoria personal-ai**: ahora es un plugin nativo v0.7.0 (`plugins/memory/personal-ai/`). El hook legacy en `hooks/personal-ai-memory-loader/` está deprecado pero se mantiene temporalmente como fallback. Actualizar config.yaml con `memory.provider: personal-ai` para activar.

---

## Estructura del Repo

```
dotfiles-hermes-agent/
├── configs/
│   ├── config.yaml           # Config principal (sin secrets)
│   ├── .env.example          # Template de variables
│   └── gateway_*.json        # Estado de canales
├── hooks/
│   └── personal-ai-memory-loader/  # DEPRECADO: legacy hook (por remover post-verificación)
├── plugins/
│   └── memory/
│       └── personal-ai/      # Plugin memory provider v1.0.0
├── skills/                   # Todos los skills instalados
├── scripts/
│   └── backup.sh            # Backup idempotente
├── patches/
│   └── brave-search.patch    # Patch para web_tools.py
└── docs/
    └── ARQUITECTURA.md       # Detalle técnico adicional
```
