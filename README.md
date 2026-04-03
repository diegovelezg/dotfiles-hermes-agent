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

### Arquitectura de memoria dual

Hermes usa dos sistemas de memoria que se complementan:

#### 1. Memoria Nativa (archivos planos)

Archivos que se cargan automáticamente en cada sesión via `MemoryStore.load_from_disk()`:

- `~/.hermes/memories/MEMORY.md` — notas de trabajo del agente
- `~/.hermes/memories/USER.md` — perfil del usuario

Se leen al inicio de cada sesión (nueva o existente). Son estáticos hasta que se actualizan.

#### 2. Personal AI MCP (memoria persistente)

Mem0-backed, cargado via hook `session:reset`/`session:start`:

- **memories know** — hechos persistentes sobre Diego
- **memories policy** — reglas operativas

Un hook en `~/.hermes/hooks/personal-ai-memory-loader/` hace llamado SSE al MCP bridge y escribe los resultados en MEMORY.md, que luego carga `MemoryStore`.

**Flujo:**
```
/new → session:reset → hook ejecuta → SSE a personal-ai →
MEMORY.md actualizado → AIAgent.__init__ → MemoryStore.load_from_disk →
agente tiene memories disponibles
```

### Hook del sistema de memorias

```
~/.hermes/hooks/personal-ai-memory-loader/
├── HOOK.yaml       # eventos + credenciales (NO hardcodear aquí)
└── handler.py      # lógica de carga via SSE
```

El hook escucha `session:start` (sesiones nuevas) y `session:reset` (`/new`).

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
6. **Memoria personal-ai**: se carga via hook en `session:reset`/`session:start`. El hook necesita las variables `PERSONAL_AI_BASE_URL`, `PERSONAL_AI_API_KEY` y `PERSONAL_AI_REMOTE_URL` en su `HOOK.yaml` (env section).

---

## Estructura del Repo

```
dotfiles-hermes-agent/
├── configs/
│   ├── config.yaml           # Config principal (sin secrets)
│   ├── .env.example          # Template de variables
│   └── gateway_*.json        # Estado de canales
├── skills/                   # Todos los skills instalados
├── scripts/
│   └── backup.sh            # Backup idempotente
├── patches/
│   └── brave-search.patch    # Patch para web_tools.py
└── docs/
    └── ARQUITECTURA.md       # Detalle técnico adicional
```
