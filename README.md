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
EXA_API_KEY=c785bef5-42cf-41c4-abd3-c04cf9486808
BRAVE_API_KEY=BSAoynGh-Yb5ZuagHbqS5sbeX3Dy4Mt
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
2. web_extract (urls de los resultados)
   ↓
3. DeepSeek-V3 via OpenRouter → síntesis + análisis
   ↓
4. Respuesta al usuario (Telegram/Discord)
```

Si Exa falla → paso 1 usa Brave automáticamente (gracias al fallback).

---

## DeepSeek via OpenRouter

### Config

```bash
OPENROUTER_API_KEY=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
```

### Uso

Llamadas directas via `terminal` + `urllib` (no usar `execute_code` para OpenRouter — tiene timeouts de 30s que cortan la conexión).

```python
import urllib.request, json

api_key = os.getenv("OPENROUTER_API_KEY")
url = "https://openrouter.ai/api/v1/chat/completions"
payload = {
    "model": "deepseek/deepseek-chat-v3",
    "messages": [{"role": "user", "content": "..."}]
}
req = urllib.request.Request(url, data=json.dumps(payload).encode(),
    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"})
with urllib.request.urlopen(req, timeout=60) as resp:
    result = json.loads(resp.read())
```

### Modelos disponibles en OpenRouter

- `deepseek/deepseek-chat-v3` — análisis y síntesis
- `deepseek/deepseek-reasoner` (R1) — razonamiento profundo

---

## MCP — Model Context Protocol

### Servidores MCP conectados

| Servidor | Herramientas | Propósito |
|----------|-------------|-----------|
| `personal-ai` | ledger_query, ledger_create, memories_search | P.A.I. de Diego (memoria, tareas, facts) |
| `browserbase` | browser_navigate, browser_snapshot, browser_click | Automatización web |

### Config MCP (`~/.hermes/config.yaml`)

```yaml
mcp_servers:
  personal-ai:
    url: https://uaimcp.papelitosdecolor.com/sse
    headers:
      x-user-id: "1093162286"
    tools:
      - ledger_query
      - ledger_create
      - ledger_bulk_action
      - memories_search
      - memories_manage
      - briefing_generate
  browserbase:
    # credentials en ~/.hermes/.env
```

### Skill: `personal-ai-bridge`

Ubicación: `skills/mcp/personal-ai-bridge/`

Expone el ledger de la P.A.I.:
- **ledger**: intel (conocimiento permanente), action (tareas)
- **action statuses**: inbox, todo, doing, review, done, dismissed
- **subjects**: salud, autismo, neurociencia, finanzas, emprendimiento, ChicasTEC, etc.
- **briefing_generate**: stats de inbox, kanban, urgent

### Personal AI MCP Server

- **user_id**: `1093162286` (mismo que Telegram)
- **Ledger subjects**: @salud, @autismo, @neurociencia, @finanzas, @emprendimiento, @ChicasTEC, @comitetp, @clarity, @openclaw, @inmobiliario, @ColleenLove, @mariana, @banco
- **Credential**: `PERSONAL_AI_API_KEY` en `~/.hermes/.env`

---

## Memory — Configuración Persistente

### Sistema de记忆

| Herramienta | Qué guarda | Dónde |
|-----------|-----------|-------|
| `mcp_memory` | facts clave, preferencias de usuario | inyectado en cada sesión |
| `session_search` | transcripciones de conversaciones | SQLite en `~/.hermes/sessions/` |
| Skills (`~/.hermes/skills/`) | procedimientos reutilizables | filesystem |

### Memory actual (inyectada al inicio)

```
- TTS: Edge TTS con voz es-MX-DaliaNeural (castellano neutro)
- Gateway: arranca con systemd + linger habilitado
- GH token: fine-grained PAT (diegovelezg)
- Repos principales: dotfiles-claude-code, personal-ai-infrastructure, etc.
- Skill Buenos Días: ~/.hermes/skills/buenos-dias/
- Cron job Buenos Días: 20257ad8ddf4 a las 7AM Lima (12 UTC) por Telegram
- Briefing stats: inbox=0, kanban=15, urgent=2
```

---

## Skills Instalados

Ubicación: `~/.hermes/skills/`

### Destacados

| Skill | Descripción |
|-------|-------------|
| `buenos-dias` | Reporte matutino 5 fuentes → audio .ogg + markdown |
| `autonomous-ai-agents` | Delegar a Claude Code, Codex, OpenCode |
| `research/arxiv` | Búsqueda académica en arXiv |
| `research/intel-reader` | Procesa URLs → reporte estructurado |
| `research/polymarket` | Datos de prediction markets |
| `mlops/inference/llama-cpp` | Inference de LLMs en CPU/GPU |
| `mlops/training/unsloth` | Fine-tuning rápido (2-5x) |
| `github/*` | PR workflow, code review, issues |
| `mcp/native-mcp` | Cliente MCP nativo |
| `mcp/personal-ai-bridge` | Bridge al ledger/memoria de la P.A.I. |

Ver directorio `skills/` para lista completa (~50 skills).

---

## Patches Personalizados

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
MINIMAX_API_KEY=...
OPENROUTER_API_KEY=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
EXA_API_KEY=c785bef5-42cf-41c4-abd3-c04cf9486808
BRAVE_API_KEY=BSAoynGh-Yb5ZuagHbqS5sbeX3Dy4Mt
PERSONAL_AI_API_KEY=...
TELEGRAM_BOT_TOKEN=...
DISCORD_BOT_TOKEN=...
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
