# Hermes Agent — Arquitectura y Configuración

## Tabla de Contenidos

1. [Overview](#1-overview)
2. [Configuración General](#2-configuración-general)
3. [LLM Providers](#3-llm-providers)
4. [Gateway y Plataformas de Mensajería](#4-gateway-y-plataformas-de-mensajería)
5. [Plugins](#5-plugins)
6. [Skills](#6-skills)
7. [Tools y Toolsets](#7-tools-y-toolsets)
8. [Delegation (Subagentes)](#8-delegation-subagentes)
9. [Cron Jobs](#9-cron-jobs)
10. [Memory System](#10-memory-system)
11. [Browser Automation](#11-browser-automation)
12. [Flujo de Credentials](#12-flujo-de-credentials)

---

## 1. Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Hermes Agent                              │
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐ │
│  │  CLI (local) │    │   Gateway    │    │  Cron Scheduler  │ │
│  │              │    │  ( messaging) │    │   ( background)  │ │
│  └──────────────┘    └──────────────┘    └──────────────────┘ │
│         │                   │                      │           │
│         └───────────────────┼──────────────────────┘           │
│                             │                                  │
│                    ┌────────▼────────┐                        │
│                    │    AIAgent      │                        │
│                    │  (core agent)   │                        │
│                    └────────┬────────┘                        │
│                             │                                  │
│         ┌───────────────────┼───────────────────┐              │
│         │                   │                   │              │
│  ┌──────▼──────┐   ┌───────▼───────┐  ┌──────▼──────┐      │
│  │   Tools     │   │   Memory      │  │   Skills     │      │
│  │  Registry   │   │   Manager     │  │   Loader     │      │
│  └─────────────┘   └───────────────┘  └──────────────┘      │
│                             │                                  │
│                    ┌────────▼────────┐                        │
│                    │    Plugins      │                        │
│                    │ (personal-ai,   │                        │
│                    │  memory, etc)   │                        │
│                    └─────────────────┘                        │
└─────────────────────────────────────────────────────────────────┘
```

**Proceso único**: Todo corre en un solo proceso Python (gateway + CLI + cron). Cada platforma de mensajería es un adapter dentro del gateway.

---

## 2. Configuración General

### Archivos

| Archivo | Propósito |
|---------|-----------|
| `~/.hermes/config.yaml` | Configuración principal (modelos, toolsets, display, etc.) |
| `~/.hermes/.env` | API keys y secrets |
| `~/.hermes/channel_directory.json` | Directorio de canales activos (actualizado automáticamente) |
| `~/.hermes/gateway_state.json` | Estado del gateway (PID, session keys activas) |

### config.yaml — Secciones Principales

```yaml
model:
  base_url: https://api.minimax.io/anthropic  # MiniMax global endpoint
  default: MiniMax-M2.7                         # Modelo default
  provider: minimax

fallback_providers: []   # No fallback configurado

credential_pool_strategies:
  minimax: fill_first

toolsets:               # Herramientas habilitadas globalmente
  - hermes-cli

agent:
  max_turns: 60
  tool_use_enforcement: auto
  reasoning_effort: medium

auxiliary:
  vision:         { provider: auto }
  web_extract:    { provider: auto }
  compression:    { provider: auto, model: google/gemini-3-flash-preview }
  session_search: { provider: auto }
  skills_hub:     { provider: auto }
  approval:       { provider: auto }
  mcp:            { provider: auto }
  flush_memories: { provider: auto }

memory:
  provider: personal-ai        # Plugin de memory activo
  memory_enabled: true
  user_profile_enabled: true
  memory_char_limit: 2200
  flush_min_turns: 6

delegation:
  model: deepseek/deepseek-chat-v3
  provider: openrouter
  base_url: ''                 # Vacío → usa credential resolution normal
  max_iterations: 50

tts:
  provider: edge               # Edge TTS (gratis, no API key)
  edge: { voice: es-MX-DaliaNeural }

display:
  personality: kawaii
  skin: default
  tool_progress_command: false

compression:
  enabled: true
  threshold: 0.5
  target_ratio: 0.2
  summary_model: google/gemini-3-flash-preview
  summary_provider: auto

cron:
  wrap_response: true

session_reset:
  at_hour: 4                   # Reset diario a las 4am
  idle_minutes: 1440           # 24 horas de inactividad
  mode: both                   # reset + notify

mcp_servers: null               # MCP servers externos (no configurados)
```

### .env — Variables de Entorno

```
# LLM Providers
MINIMAX_API_KEY=***             # Provider principal
OPENROUTER_API_KEY=***          # Para delegation y auxiliary

# Plataformas de Mensajería
TELEGRAM_BOT_TOKEN=***
TELEGRAM_ALLOWED_USERS=1093162286
TELEGRAM_HOME_CHANNEL=1093162286

DISCORD_BOT_TOKEN=***
DISCORD_ALLOWED_USERS=1025907984498430044
DISCORD_HOME_CHANNEL=1474242034356326442

# Tools
EXA_API_KEY=***                 # Web search
BRAVE_API_KEY=***               # Web search alternativo

# Browser Automation
BROWSERBASE_API_KEY=***
BROWSERBASE_PROJECT_ID=
BROWSERBASE_PROXIES=true
BROWSERBASE_ADVANCED_STEALTH=false
BROWSER_SESSION_TIMEOUT=300
BROWSER_INACTIVITY_TIMEOUT=120

# Memory Provider Plugin
PERSONAL_AI_BASE_URL=https://uaimcp.papelitosdecolor.com
PERSONAL_AI_API_KEY=***
PERSONAL_AI_REMOTE_URL=https://uaimcp.papelitosdecolor.com/sse

# Skills Hub
GITHUB_TOKEN=***

# Voice
VOICE_TOOLS_OPENAI_KEY=***      # Para Whisper STT y OpenAI TTS
GROQ_API_KEY=***

# RL Training (opcional)
TINKER_API_KEY=***
WANDB_API_KEY=***

# Terminal
TERMINAL_TIMEOUT=60
TERMINAL_LIFETIME_SECONDS=300
```

---

## 3. LLM Providers

### Provider Principal: MiniMax

```yaml
model:
  provider: minimax
  base_url: https://api.minimax.io/anthropic
  default: MiniMax-M2.7
```

- **Base URL**: `https://api.minimax.io/anthropic` (compatible con OpenAI SDK)
- **Credential**: `MINIMAX_API_KEY` en `.env`
- **Strategy**: `fill_first` — usa la primera credential que funcione

### Provider para Delegation: OpenRouter

```yaml
delegation:
  provider: openrouter
  model: deepseek/deepseek-chat-v3
```

- **Credential**: `OPENROUTER_API_KEY` en `.env`
- **Model**: `deepseek/deepseek-chat-v3`
- Subagentes spawnneados con `delegate_task` usan OpenRouter

### Auxiliary Models (auto-detect)

Los servicios auxiliary usan `provider: auto`, lo que significa que el sistema detecta el mejor provider disponible:

| Auxiliary | Default Model | Provider |
|-----------|---------------|----------|
| Vision | — | Auto (OpenAI para vision) |
| Web Extract | — | Auto (Parallel/Firecrawl) |
| Compression | `google/gemini-3-flash-preview` | Auto |
| Session Search | — | Auto |
| Skills Hub | — | Auto |
| Approval | — | Auto |

### Runtime Provider Resolution

`hermes_cli/runtime_provider.py` resuelve credentials basadas en el provider:

```
Provider → Credential → Base URL
─────────────────────────────────
minimax    MINIMAX_API_KEY     https://api.minimax.io/anthropic
openrouter OPENROUTER_API_KEY  https://openrouter.ai/api/v1
anthropic  ANTHROPIC_API_KEY   https://api.anthropic.com
openai     OPENAI_API_KEY      https://api.openai.com/v1
z          ZAI_API_KEY         https://openrouter.ai/api/v1
kimi       KIMI_API_KEY        https://api.kimi.com/coding/v1
nous       NOUS_API_KEY        https://openrouter.ai/api/v1
```

---

## 4. Gateway y Plataformas de Mensajería

### Arquitectura del Gateway

```
gateway/run.py (main loop)
    │
    ├── adapters por platform
    │   ├── telegram.py
    │   ├── discord.py
    │   ├── slack.py
    │   ├── whatsapp.py
    │   ├── signal.py
    │   ├── email.py
    │   ├── homeassistant.py
    │   ├── sms.py
    │   └── ... (webhook, matrix, mattermost, dingtalk, feishu, wecom)
    │
    ├── SessionStore (sessions SQLite + WAL)
    ├── AIAgent cache (por session_key)
    ├── Memory Manager
    └── Cron Scheduler ( ThreadPoolExecutor)
```

### Plataformas Conectadas

**Telegram**:
- DM: `1093162286` (Diego)
- Allowed users: `1093162286`

**Discord**:
- Home channel: `1474242034356326442` (#general)
- Canales activos: #general, #agente, #diario, #proyectos, #investigación, #notas
- Threads de Discord detectados automáticamente y agregados al channel directory

**WhatsApp, Signal, Email, SMS**: Configurados pero no activos (listas vacías en channel_directory)

### Platform Toolsets

Cada platforma tiene toolsets específicos en `config.yaml`:

```yaml
platform_toolsets:
  cli:
    - browser, clarify, code_execution, cronjob, delegation
    - file, image_gen, memory, session_search, skills
    - terminal, todo, tts, vision, web

  telegram:
    - browser, clarify, code_execution, cronjob, delegation
    - file, image_gen, memory, session_search, skills
    - terminal, todo, tts, vision, web

  discord:
    - browser, clarify, code_execution, cronjob, delegation
    - file, image_gen, memory, session_search, skills
    - terminal, todo, tts, web
    # NOT: vision (no enviado por Discord)

  homeassistant:
    - hermes-homeassistant

  signal:
    - hermes-signal

  slack:
    - hermes-slack

  whatsapp:
    - hermes-whatsapp
```

**Nota**: `vision` no está en Discord porque Discord maneja imágenes como attachments y las pasa directamente al modelo de visión del gateway.

### Home Channels (Destinos por Defecto)

Cuando un cron job entrega a `deliver: "telegram"` o `deliver: "discord"`, usa:

| Platform | Chat ID | Nombre |
|----------|---------|--------|
| telegram | `1093162286` | Diego (DM) |
| discord | `1474242034356326442` | #general |

Para targeting explícito: `"platform:chat_id"` (ej: `telegram:1093162286`)

### Session Reset

```yaml
session_reset:
  at_hour: 4        # Reset automático diario a las 4am UTC
  idle_minutes: 1440 # Reset por inactividad (24h)
  mode: both         # reset + notify al usuario
```

---

## 5. Plugins

### Plugin System

Los plugins viven en `~/.hermes/plugins/<name>/` y son auto-descubiertos al arrancar. Cada plugin tiene:

- `plugin.yaml` — metadata y config fields
- `__init__.py` — implementación

### Plugin: `personal-ai` (Memory Provider)

**Path**: `~/.hermes/plugins/memory/personal-ai/`

```yaml
name: personal-ai
type: memory          # Provider de memory, no toolset
provider: memory
```

**Lo que hace**: Implementa `MemoryProvider` ABC y conecta al personal-ai MCP v5 via SSE+JSON-RPC.

**7 herramientas expuestas al modelo**:

| Tool | Descripción |
|------|-------------|
| `personal_ai_search` | Búsqueda semántica sobre know/policy/episodic memories |
| `personal_ai_memories_manage` | Crear, actualizar, deprecate memories |
| `personal_ai_briefing_generate` | Briefing diario desde ledger + memories |
| `personal_ai_ledger_query` | Query action/intel ledger items |
| `personal_ai_ledger_item_create` | Crear nuevo ledger item |
| `personal_ai_ledger_bulk_action` | Bulk update de ledger items |
| `personal_ai_browser_activity_query` | Query browser history |

**Configuración en `.env`**:
```
PERSONAL_AI_BASE_URL=https://uaimcp.papelitosdecolor.com
PERSONAL_AI_API_KEY=***
PERSONAL_AI_REMOTE_URL=https://uaimcp.papelitosdecolor.com/sse
PERSONAL_AI_USER_ID=1093162286
```

### Plugin: `personal-ai-ledger`

**Path**: `~/.hermes/plugins/personal-ai-ledger/`

```yaml
name: personal-ai-ledger
provider: personal-ai-ledger
```

**Expone 6 herramientas adicionales** (ledger + briefing + browser activity):

| Tool | Descripción |
|------|-------------|
| `ledger_query` | Buscar ledger items |
| `ledger_item_create` | Crear ledger item (note, task, project, person, intel) |
| `ledger_bulk_action` | Bulk update/archive ledger items |
| `briefing_generate` | Generar briefing estructurado desde ledger |
| `browser_activity_add` | Registrar browser activity |
| `browser_activity_query` | Query browser history |

**Comparación con plugin de memory**:

| | `personal-ai` (memory) | `personal-ai-ledger` |
|---|---|---|
| Type | `memory` provider | Tool provider |
| Tools | 7 (search/manage) | 6 (ledger/briefing) |
| SSOT | personal-ai MCP | personal-ai MCP |

Ambos usan la misma conexión SSE al servidor MCP. Son plugins separados porque uno es `type: memory` y el otro es un provider de tools normal.

---

## 6. Skills

### Skills Instalados

```
~/.hermes/skills/
├── apple/
├── autonomous-ai-agents/
│   ├── claude-code/      # Delegar a Claude Code CLI
│   ├── codex/            # Delegar a OpenAI Codex CLI
│   └── opencode/         # Delegar a OpenCode CLI
├── buenos-dias/          # Informe matutino con TTS
├── creative/
│   ├── ascii-art/
│   ├── ascii-video/
│   ├── excalidraw/
│   └── songwriting-and-ai-music/
├── data-science/
│   └── jupyter-live-kernel/
├── devops/
│   └── webhook-subscriptions/
├── diagramming/
├── dogfood/
├── domain/
├── email/
│   └── himalaya/         # Gestión de emails IMAP/SMTP
├── feeds/
├── gaming/
│   ├── minecraft-modpack-server/
│   └── pokemon-player/
├── gifs/
├── github/
│   ├── codebase-inspection/
│   ├── github-auth/
│   ├── github-code-review/
│   ├── github-issues/
│   ├── github-pr-workflow/
│   └── github-repo-management/
├── inference-sh/
├── leisure/
│   └── find-nearby/
├── mcp/
├── media/
│   ├── gif-search/
│   ├── heartmula/
│   ├── songsee/
│   └── youtube-content/
├── mlops/
│   ├── huggingface-hub/
│   ├── axolotl/
│   ├── dspy/
│   ├── gguf/
│   ├── guidance/
│   ├── grpo-rl-training/
│   ├── lm-evaluation-harness/
│   ├── llama-cpp/
│   ├── modal/
│   ├── oblique/
│   ├── peft/
│   ├── pytorch-fsdp/
│   ├── stable-diffusion/
│   ├── text-generation-inference/
│   ├── trl-fine-tuning/
│   ├── unsloth/
│   ├── vllm/
│   └── weights-and-biases/
├── note-taking/
│   └── obsidian/
├── productivity/
│   ├── google-workspace/
│   ├── linear/
│   ├── nano-pdf/
│   ├── notion/
│   ├── ocr-and-documents/
│   └── powerpoint/
├── red-teaming/
│   └── godmode/
├── research/
│   ├── arxiv/
│   ├── blogwatcher/
│   ├── intel-reader/
│   ├── ml-paper-writing/
│   └── polymarket/
├── smart-home/
│   └── openhue/
└── social-media/
    └── xitter/
```

### Skill: `buenos-dias`

**Descripción**: Informe matutino con noticias, historia y ciencia — generado como audio para Telegram.

**Fuentes**:
1. Twitter/X — Trending topics AI (`browser_navigate`)
2. onthisday.com — Evento histórico del día (`browser_navigate`)
3. techmeme.com — 3 noticias principales de tecnología (`web_search` + `web_extract`)
4. sciencedaily.com — Noticia científica principal (`web_search` + `web_extract`)
5. bigthink.com — Artículo interesante (`web_search` + `web_extract`)

**Flujo**:
1. Investigar fuentes (browser + web search/extract)
2. Redactar reporte en castellano (~2000-2500 chars)
3. Generar audio con `text_to_speech` (Edge TTS, `es-ES`)
4. Enviar como nota de voz a Telegram

**Output**: `/root/.hermes/skills/buenos-dias/output/hoy.ogg`

**Scheduling**: Diario a las 12:00 UTC (configurado como cron job)

---

## 7. Tools y Toolsets

### Core Tools (`_HERMES_CORE_TOOLS`)

```python
_HERMES_CORE_TOOLS = [
    # Web
    "web_search", "web_extract",
    # Terminal
    "terminal", "process",
    # File
    "read_file", "write_file", "patch", "search_files",
    # Vision + Image
    "vision_analyze", "image_generate",
    # MoA
    "mixture_of_agents",
    # Skills
    "skills_list", "skill_view", "skill_manage",
    # Browser
    "browser_navigate", "browser_snapshot", "browser_click",
    "browser_type", "browser_scroll", "browser_back",
    "browser_press", "browser_close", "browser_get_images",
    "browser_vision", "browser_console",
    # TTS
    "text_to_speech",
    # Planning & Memory
    "todo", "memory",
    # Session
    "session_search",
    # Interaction
    "clarify",
    # Code + Delegation
    "execute_code", "delegate_task",
    # Cron
    "cronjob",
    # Messaging
    "send_message",
    # Home Assistant
    "ha_list_entities", "ha_get_state", "ha_list_services", "ha_call_service",
]
```

### Toolsets

| Toolset | Tools incluidos |
|---------|----------------|
| `web` | `web_search`, `web_extract` |
| `search` | `web_search` |
| `vision` | `vision_analyze` |
| `image_gen` | `image_generate` |
| `terminal` | `terminal`, `process` |
| `moa` | `mixture_of_agents` |
| `skills` | `skills_list`, `skill_view`, `skill_manage` |
| `browser` | `browser_*` + `web_search` |
| `cronjob` | `cronjob` |
| `messaging` | `send_message` |
| `rl` | `rl_*` (RL training tools) |
| `file` | `read_file`, `write_file`, `patch`, `search_files` |
| `tts` | `text_to_speech` |
| `todo` | `todo` |
| `memory` | `memory` |
| `session_search` | `session_search` |
| `clarify` | `clarify` |
| `code_execution` | `execute_code` |
| `delegation` | `delegate_task` |
| `homeassistant` | `ha_*` |
| `hermes-cli` | `_HERMES_CORE_TOOLS` completo |
| `cli` | `_HERMES_CORE_TOOLS` completo |
| `telegram` | `_HERMES_CORE_TOOLS` completo |
| `discord` | `_HERMES_CORE_TOOLS` completo (sin vision) |

### Tool Registration

Cada tool se registra en `tools/registry.py`:

```python
registry.register(
    name="web_search",
    toolset="web",
    schema={...},  # OpenAI tool schema
    handler=lambda args, **kw: web_search(query=..., task_id=...),
    check_fn=check_web_search_requirements,  # Valida API keys
)
```

Los tools handlers son funciones que retornan JSON strings.

### Herramientas Especiales

**Agent-level tools** (interceptadas en `run_agent.py` antes de `handle_function_call`):
- `todo` — planning/interruption
- `memory` — persistent memory
- `delegate_task` — subagent spawning
- `cronjob` — cron management
- `send_message` — cross-platform messaging
- `skills_list/view/manage` — skill management

**Gated tools** (requieren que el gateway esté corriendo):
- `send_message` — usa el gateway adapter para delivery
- `cronjob` — solo funciona con gateway activo

---

## 8. Delegation (Subagentes)

### Cómo funciona

`delegate_task` spawnea un `AIAgent` hijo en un thread separado con:
- Contexto aislado (sin historial del parent)
- Toolset restringido
- Terminal session propia
- Credential bundle configurado

El parent solo ve el resultado final (summary), nunca los tool calls intermedios del hijo.

### Configuración de Delegation

```yaml
delegation:
  model: deepseek/deepseek-chat-v3
  provider: openrouter
  base_url: ''          # Vacío → usa credential resolution de provider
  max_iterations: 50
```

### Credential Resolution para Subagentes

`tools/delegate_tool.py::_resolve_delegation_credentials()`:

```
Si delegation.base_url está configurado:
    → Usa base_url directo con api_key
    → provider = "custom", api_mode = "chat_completions"

Si solo delegation.provider está configurado:
    → resolve_runtime_provider(provider)
    → Obtiene base_url, api_key, api_mode del provider system

Si nada está configurado:
    → Child hereda todo del parent agent
```

### Bloqueo de Herramientas en Hijos

```python
DELEGATE_BLOCKED_TOOLS = frozenset([
    "delegate_task",   # No recursive delegation
    "clarify",        # No user interaction
    "memory",         # No writes to shared MEMORY.md
    "send_message",   # No cross-platform side effects
    "execute_code",   # Children should reason step-by-step
])
```

### Límites

- `MAX_CONCURRENT_CHILDREN = 3`
- `MAX_DEPTH = 2` (parent → child → grandchild rejected)
- `DEFAULT_MAX_ITERATIONS = 50`

### Skills que usan delegation

```
autonomous-ai-agents/
├── claude-code/     # Spawns Claude Code CLI
├── codex/           # Spawns OpenAI Codex CLI
└── opencode/        # Spawns OpenCode CLI
```

---

## 9. Cron Jobs

### Job Activo

```json
{
  "job_id": "20257ad8ddf4",
  "name": "Buenos Días - Informe Matutino",
  "skill": "buenos-dias",
  "skills": ["buenos-dias"],
  "model": "deepseek/deepseek-chat-v3",
  "provider": "openrouter",
  "base_url": "https://openrouter.ai/api/v1",
  "schedule": "0 12 * * *",
  "repeat": "forever",
  "deliver": "telegram",
  "next_run_at": "2026-04-07T12:00:00+00:00",
  "last_run_at": "2026-04-06T12:10:59",
  "last_status": "error"
}
```

### Scheduler Architecture

```
cron/scheduler.py
    │
    ├── ThreadPoolExecutor(max_workers=1)  # Un job a la vez
    │
    └── Job execution flow:
        1. agent = AIAgent(model, provider, base_url, skills=[skill_name])
        2. agent.run_conversation(prompt)  # Blocking en thread pool
        3. Timeout: 600s (10 min) — hard timeout
        4. finally: clear_interrupt()
        5. Delivery: send_message → telegram:1093162286
```

### Timeout y Clear Interrupt

```python
# scheduler.py — después de timeout
except concurrent.futures.TimeoutError:
    agent.interrupt("Cron job timed out")
    _cron_pool.shutdown(wait=False, cancel_futures=True)
    agent.clear_interrupt()  # ← Limpia el flag global
    raise TimeoutError(...)

# finally block — siempre limpia
finally:
    _cron_pool.shutdown(wait=False)
    agent.clear_interrupt()  # ← Limpia el flag global
```

### Configuración de Timeout

```python
_cron_timeout = float(os.getenv("HERMES_CRON_TIMEOUT", 600))  # 10 min default
```

---

## 10. Memory System

### Dual Memory Architecture

```
MemoryManager
    │
    ├── BuiltinMemoryProvider (MEMORY.md / USER.md — siempre activo)
    │       ├── ~/.hermes/memories/MEMORY.md — notas del agente
    │       └── ~/.hermes/memories/USER.md — perfil del usuario
    │
    └── PersonalAIMemoryProvider (plugin)
            │
            └── Conexión SSE al personal-ai MCP v5 server
                    (https://uaimcp.papelitosdecolor.com)
```

### Configuración

```yaml
memory:
  provider: personal-ai        # Plugin activo
  memory_enabled: true
  user_profile_enabled: true
  memory_char_limit: 2200
  user_char_limit: 1375
  flush_min_turns: 6
  nudge_interval: 10
  provider_settings:
    personal_ai:
      cache_ttl: 120            # Cache de prefetch: 2 min
```

### Memory Types (personal-ai)

| Type | Descripción | Ejemplo |
|------|-------------|---------|
| `know` | Facts persistentes sobre Diego | Preferencias, proyectos, personas |
| `policy` | Reglas operativas | "Diego prefiere español, sin markdown" |
| `episodic` | Eventos pasados | "Completó focus groups el 2-3 abril 2026" |

### Personal AI MCP Server

- **URL**: `https://uaimcp.papelitosdecolor.com`
- **Auth**: `PERSONAL_AI_API_KEY`
- **SSE Endpoint**: `https://uaimcp.papelitosdecolor.com/sse`
- **User ID**: `1093162286` (Telegram ID de Diego)

### Legacy vs Plugin

| | Legacy Hook | New Plugin |
|---|---|---|
| Integration | `session:start` event → MEMORY.md | `MemoryProvider` ABC → native lifecycle |
| SSOT | personal-ai → MEMORY.md → MemoryStore | personal-ai direct |
| Tools | Ninguna | 7 herramientas |
| Timing | Antes de agent init | Native `initialize()` / `prefetch()` |

---

## 11. Browser Automation

### Browser Provider

```
tools/browser_tool.py + tools/browser_camofox.py
    │
    └── Browserbase Cloud
            ├── API: BROWSERBASE_API_KEY
            ├── Project ID: BROWSERBASE_PROJECT_ID
            └── Sessions managed remotely
```

### Configuración

```yaml
browser:
  inactivity_timeout: 120    # Cleanup después de 2 min sin actividad
  command_timeout: 30         # Timeout por comando
  record_sessions: false
  allow_private_urls: false
  camofox:
    managed_persistence: false
```

```env
BROWSERBASE_API_KEY=***
BROWSERBASE_PROJECT_ID=
BROWSERBASE_PROXIES=true
BROWSERBASE_ADVANCED_STEALTH=false
BROWSER_SESSION_TIMEOUT=300
BROWSER_INACTIVITY_TIMEOUT=120
```

### Browser Tools Disponibles

```python
browser_navigate    # Ir a URL
browser_snapshot    # Captar contenido (compact/full)
browser_click       # Click en elemento por ref (@e1, @e2...)
browser_type        # Escribir en input
browser_scroll      # Scroll up/down
browser_back        # Volver atrás
browser_press       # Teclado (Enter, Tab, etc)
browser_close       # Cerrar sesión
browser_get_images  # Listar imágenes en página
browser_vision      # screenshot + análisis visual
browser_console     # Capturar logs de consola JS
```

### Stealth Mode

- **Basic Stealth**: Siempre activo (random fingerprints, auto CAPTCHA solving)
- **Advanced Stealth**: Requiere `BROWSERBASE_ADVANCED_STEALTH=true` + Scale Plan

---

## 12. Flujo de Credentials

### Cadena de Resolution

```
AIAgent.__init__(model, provider, base_url, ...)
    │
    └── run_agent.py::_resolve_model_and_provider()
            │
            └── hermes_cli/runtime_provider.py::resolve_runtime_provider()
                    │
                    ├── CredentialPool.resolve(requested_provider)
                    │       │
                    │       └── Busca en: .env → auth.json → config.yaml
                    │
                    └── Retorna: {provider, base_url, api_key, api_mode}
```

### Credential Files

`~/.hermes/auth.json` — almacena tokens de OAuth (GitHub App, etc.)

### Priority de Credentials

1. Parámetros explícitos (`provider=`, `base_url=`)
2. `runtime_api_key` / `runtime_base_url` (en runtime overrides)
3. Env vars (`MINIMAX_API_KEY`, `OPENROUTER_API_KEY`, etc.)
4. Config file (`config.yaml` → `model.base_url`)
5. Defaults del provider

### Provider Secrets

| Provider | API Key Var | Default Base URL |
|----------|-------------|-----------------|
| minimax | `MINIMAX_API_KEY` | `https://api.minimax.io/anthropic` |
| openrouter | `OPENROUTER_API_KEY` | `https://openrouter.ai/api/v1` |
| anthropic | `ANTHROPIC_API_KEY` | `https://api.anthropic.com` |
| openai | `OPENAI_API_KEY` | `https://api.openai.com/v1` |
| zai | `ZAI_API_KEY` | `https://openrouter.ai/api/v1` |
| kimi-coding | `KIMI_API_KEY` | `https://api.kimi.com/coding/v1` |
| nous | `NOUS_API_KEY` | `https://openrouter.ai/api/v1` |

---

## Arreglos Recientes

### Fix: Interrupt Global en Cached Agents

**Problema**: Cuando un agent timeouteaba, `set_interrupt(True)` seteba un flag global (`threading.Event`). El cron agent (mismo proceso) leía ese flag y se interrumpía a sí mismo. El flag nunca se limpiaba.

**Fix en `gateway/run.py`**:
```python
if agent is None:
    # create new agent
else:
    agent.clear_interrupt()  # Limpia stale interrupt del cache
```

**Fix en `cron/scheduler.py`**:
```python
finally:
    _cron_pool.shutdown(wait=False)
    if hasattr(agent, "clear_interrupt"):
        agent.clear_interrupt()  # Limpia flag después de timeout
```

### Fix: Cron Job Buenos Días usando OpenRouter

El cron job de Buenos Días ahora usa:
```yaml
model: deepseek/deepseek-chat-v3
provider: openrouter
base_url: https://openrouter.ai/api/v1
```

Esto asegura que el skill use OpenRouter DeepSeek en vez del provider default (MiniMax).
