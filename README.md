# Hermes Agent — Dotfiles de Diego

Configuración personalizada de Hermes Agent. Stack: MiniMax-M2 como agente principal + DeepSeek (OpenRouter) para investigación + personal-ai (Mem0) como memoria persistente.

---

## Plataformas Conectadas

| Plataforma | Status | Destino |
|-----------|--------|---------|
| Telegram | ✓ | DM y Home: 1093162286 |
| Discord | ✓ | Home: 1474242034356326442 |

---

## Arquitectura

```
Usuario (Telegram / Discord)
         ↓
  Hermes Gateway  (Telegram bot + Discord bot)
         ↓
  AIAgent  (MiniMax-M2 — agente principal)
         ↓
  ┌─────────────────────────────────────┐
  │  Tools nativas                      │
  │  web_search / web_extract          │
  │  terminal / execute_code            │
  │  delegate_task                     │
  │  memory (builtin + personal-ai)    │
  └─────────────────────────────────────┘
         ↓
  OpenRouter  (DeepSeek-V3 / R1 — investigación)
```

---

## Modelos LLM

| Rol | Modelo | Provider | Uso |
|-----|--------|----------|-----|
| Agente principal | MiniMax-M2 | minimax | Conversación, coordinación, todas las tools |
| Investigación pesada | DeepSeek-V3 | OpenRouter | Síntesis de temas complejos |
| Razonamiento profundo | DeepSeek-R1 | OpenRouter | Análisis lógico, debugging |
| Visión | MiniMax-V06 | minimax | Análisis de imágenes |

---

## Sistema de Memoria

###SSOT: personal-ai MCP (Mem0)

Ambos plugins comparten una única conexión SSE al servidor MCP `uaimcp.papelitosdecolor.com`.

```
MemoryManager
    ├── BuiltinMemoryProvider        ← MEMORY.md / USER.md
    │    (archivos planos para notas de sesión)
    │
    └── PersonalAIMemoryProvider   ← plugins/personal-ai-memory/
         │                          SSE → personal-ai MCP
         ├── prefetch()             → recall semántico al inicio
         ├── system_prompt_block()  → instrucciones en el prompt
         ├── get_tool_schemas()     → 2 tools de memoria
         └── handle_tool_call()     → dispatch directo al MCP

PersonalAILedgerProvider             ← plugins/personal-ai-ledger/
     ├── get_tool_schemas()     → 6 tools ledger/briefing/browser
     └── handle_tool_call()
```

### Tipos de memoria en Mem0

| Tipo | Descripción | Ejemplo |
|------|-------------|---------|
| `know` | Hechos persistentes | proyectos, personas, preferencias |
| `policy` | Reglas operativas | "Diego prefiere español, sin markdown en Telegram" |
| `episodic` | Eventos pasados | "Grupos focales completados 2-3 abr 2026" |

### Plugin memory — tools

| Tool | Descripción |
|------|-------------|
| `personal_ai_memories_search` | Búsqueda semántica sobre know/policy/episodic |
| `personal_ai_memories_manage` | Crear, actualizar, deprecar memorias |

### Plugin ledger — tools

| Tool | Descripción |
|------|-------------|
| `ledger_query` | Consultar items del ledger (action/intel) |
| `ledger_item_create` | Crear item en el ledger |
| `ledger_bulk_action` | Bulk update/archive de items |
| `briefing_generate` | Generar briefing estructurado desde ledger |
| `browser_activity_add` | Registrar actividad de navegación |
| `browser_activity_query` | Consultar historial de navegación |

---

## Skills Custom

| Skill | Descripción |
|-------|-------------|
| `diego-buenos-dias` | Informe matutino con TTS para Telegram |
| `diego-read-it-later` | Extraer y guardar contenido de URLs |
| `diego-research` | Investigación estructurada con hechos atómicos |
| `diego-intel` | Briefing personalizado + workflow de investigación |

Se cargan via `external_dirs` en `config.yaml` — sobreviven a updates de Hermes sin necesidad de restore.

---

## Flujo de Investigación

```
1. web_search (Exa, limit=5)
   ↓
2. web_extract (las 3-5 URLs más relevantes)
   ↓
3. Síntesis con DeepSeek-V3 via OpenRouter
```

### Web Search — Backends

`web_search` usa Exa por defecto → Brave como fallback automático.

```bash
EXA_API_KEY=***
BRAVE_API_KEY=***
```

> **Nota Brave:** Necesita plan "Data for Search" (no "Data for AI"). Keys `BSA*` del plan AI no funcionan.

---

## Gateway y Plataformas

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
- **Output:** `skills/diego-buenos-dias/output/hoy.ogg` + `.md` con fecha

---

## Configuración

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

skills:
  external_dirs:
    - ~/dotfiles-hermes-agent/skills
```

### `~/.hermes/.env` (nunca subir al repo)

```bash
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

## Restauración Post-Update

### Skills (automático)

No requieren acción. `external_dirs` en `config.yaml` los descubre automáticamente después de cualquier update.

### Plugins personal-ai (requiere script)

Los plugins **no** soportan `external_dirs`. Después de un update de Hermes:

```bash
bash ~/dotfiles-hermes-agent/scripts/restore.sh
hermes plugins list | grep personal-ai
```

---

## Estructura del Repo

```
dotfiles-hermes-agent/
├── configs/
│   ├── config.yaml          # Config principal
│   ├── .env.example         # Template de variables
│   ├── channel_directory.json
│   ├── discord_threads.json
│   └── gateway_state.json
├── cron/
│   ├── jobs.json            # Jobs programados
│   └── scheduler.py
├── gateway/
│   ├── run.py
│   └── builtin_hooks/
│       ├── personal_ai_client.py
│       └── personal_ai_memory_provider.py
├── plugins/
│   ├── personal-ai-memory/  # Plugin memory provider (Mem0)
│   └── personal-ai-ledger/  # Plugin ledger/briefing tools
├── scripts/
│   ├── backup.sh            # Backup idempotente
│   └── restore.sh           # Restaurar plugins post-update
├── skills/
│   ├── diego-buenos-dias/   # + output/
│   ├── diego-intel/
│   ├── diego-read-it-later/
│   └── diego-research/      # + facts/ + output/
├── SOUL.md                  # Identidad del agente
└── README.md
```

---

## Comandos Útiles

```bash
# Backup de configs y plugins
./scripts/backup.sh

# Restaurar plugins después de update de Hermes
bash ~/dotfiles-hermes-agent/scripts/restore.sh

# Ver estado del gateway
systemctl --user status hermes-gateway
journalctl --user -u hermes-gateway -f
systemctl --user restart hermes-gateway

# Verificar plugins y skills
hermes plugins list | grep personal-ai
hermes skills list | grep diego

# Doctor
hermes doctor
```

---

## Notas

1. **API Keys** — nunca subirlas. Usar `configs/.env.example` como template.
2. **Plugins** — `personal-ai-memory` y `personal-ai-ledger` se respaldan en el repo. Post-update: `restore.sh`.
3. **Skills** — se cargan via `external_dirs`. No necesitan restore post-update.
