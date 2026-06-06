# Hermes Agent — Dotfiles de Diego

Configuración personalizada de Hermes Agent. Stack: MiniMax-M2 como agente principal + DeepSeek (OpenRouter) para investigación + personal-ai (Mem0) como memoria persistente.

---

## Backup

Este repo es el backup canónico. Se commitea desde el estado real de `~/.hermes/`.

**Workflow:**
- **Rama `main`** = estado actual del runtime, sincronizada con `~/.hermes/`
- **Rama `master`** = estado legacy (no se usa activamente)
- **Rama `con-memoria`** = variante experimental (no usar en producción)
- **Rama `backup`** = snapshot pre-arquitectura v0.7

**Lo que está en el repo:**
- `configs/MEMORY.md`, `configs/USER.md` — contexto de Diego (personal, no secretos)
- `configs/config.yaml.example` — template de config con URLs/secrets redactados
- `configs/.env.example` — nombres de variables de entorno
- `configs/channel_directory.json` — canales registrados (Telegram/Discord)
- `configs/discord_threads.json` — threads tracked
- `skills/diego-*/` — 5 skills custom (buenos-dias, read-it-later, research, shopping-scout, chrome-remote-control)
- `plugins/personal-ai-*/` — 2 plugins (memory + ledger) para Mem0/papelitosdecolor
- `scripts/`, `hooks/`, `cron/`, `gateway/` — infra y automatizaciones
- `README.md` — este archivo

**Lo que NO está en el repo (secrets):**
- `configs/config.yaml` — config real con URLs internas → en Bitwarden Secrets Manager
- `~/.hermes/.env` — API keys, tokens, home channels → en Bitwarden Secrets Manager

**Restore en máquina nueva:**
1. Clonar este repo
2. Instalar `bws` (Bitwarden CLI) y autenticar con el `BWS_ACCESS_TOKEN`
3. `bws run -- hermes init` — Hermes carga los secrets desde Bitwarden
4. Los plugins y skills se descubren automáticamente desde `~/.hermes/plugins/` y `~/.hermes/skills/`
5. Verificar con `hermes skills list | grep diego-` y `hermes plugins list`

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

**SSOT: personal-ai MCP (Mem0)**

Todos los hechos sobre Diego, sus relaciones, preferencias y contexto personal viven en Mem0 (servidor `uaimcp.papelitosdecolor.com`). La tool `memory` escribe a archivos locales (`~/.hermes/memories/MEMORY.md`, `USER.md`) que sincronizan con Mem0.

```
MemoryManager
    ├── BuiltinMemoryProvider   → MEMORY.md / USER.md (archivos planos)
    └── PersonalAIMemoryProvider → plugins/personal-ai-memory/
                                  SSE → personal-ai MCP → Mem0

PersonalAILedgerProvider        → plugins/personal-ai-ledger/
```

### Plugins

| Plugin | Tools | Descripción |
|--------|-------|-------------|
| `personal-ai-memory` | `personal_ai_memories_search`, `personal_ai_memories_manage` | Búsqueda y gestión de memorias |
| `personal-ai-ledger` | `ledger_query`, `ledger_item_create`, `ledger_bulk_action`, `briefing_generate`, `browser_activity_*` | Items action/intel + briefings |

### Tipos de memoria en Mem0

| Tipo | Descripción |
|------|-------------|
| `know` | Hechos persistentes — proyectos, personas, preferencias |
| `policy` | Reglas operativas — "Diego prefiere español informal" |
| `episodic` | Eventos pasados — "Grupos focales completados 2-3 abr 2026" |

---

## Skills Custom

Los 4 skills de Diego se cargan via `external_dirs` en `config.yaml`. **Sobreviven a `hermes update`** — no necesitan restore.

|| Skill | Descripción |
|-------|-------------|
| `diego-buenos-dias` | Informe matutino con TTS para Telegram |
| `diego-read-it-later` | Extraer y guardar contenido de URLs |
| `diego-research` | Investigación estructurada con hechos atómicos |
| `diego-shopping-scout` | Monitoreo y comparación de precios de productos |

---

## Cron Jobs

| Job | Schedule | Delivery | Descripción |
|-----|----------|----------|-------------|
| Buenos Días (`a5976debdb34`) | Daily 7:00 AM Lima (`0 12 * * *`) | Telegram | Informe con histórico, Techmeme, AI Twitter, ScienceDaily, BigThink |
| Shopping Scout (`0cd58cf53397`) | Daily 22:00 Lima (`0 22 * * *`) | Origin | Revisa precios configurados en `output/config.json` y reporta cambios |

---

## Flujo de Investigación

```
1. web_search (Exa, limit=5)
   ↓
2. web_extract (las 3-5 URLs más relevantes)
   ↓
3. Síntesis con DeepSeek-V3 via OpenRouter
```

> **Nota Brave (fallback):** Necesita plan "Data for Search" — keys `BSA*` del plan AI no funcionan.

---

## Configuración

### Setup inicial en máquina nueva

```bash
# 1. Clonar repo
git clone https://github.com/diegovelezg/dotfiles-hermes-agent.git ~/dotfiles-hermes-agent

# 2. Copiar .env y completar API keys
cp dotfiles-hermes-agent/.env.example ~/.hermes/.env
# Editar ~/.hermes/.env con las API keys reales

# 3. Restaurar plugins personal-ai (no survive updates)
bash ~/dotfiles-hermes-agent/scripts/restore.sh

# 4. Verificar
hermes plugins list | grep personal-ai
hermes skills list  | grep diego
hermes doctor
```

### `~/.hermes/.env` (nunca commitear)

```bash
MINIMAX_API_KEY=
OPENROUTER_API_KEY=
EXA_API_KEY=
PERSONAL_AI_API_KEY=
PERSONAL_AI_BASE_URL=https://uaimcp.papelitosdecolor.com
PERSONAL_AI_REMOTE_URL=https://uaimcp.papelitosdecolor.com/sse
PERSONAL_AI_USER_ID=1093162286
TELEGRAM_BOT_TOKEN=
DISCORD_BOT_TOKEN=
```

Template público: `configs/.env.example`

### `~/.hermes/config.yaml`

Modelos, providers, skills `external_dirs`, y plugins activos. **Este repo versiona `configs/config.yaml`** — copiar a `~/.hermes/config.yaml` para mantener la config sincronizada.

### SOUL.md

Define la personalidad del agente. Actualmente: **kawaii**. Editar en `SOUL.md` y references en `configs/` via symlink.

---

## Post-Update de Hermes

`hermes update` reinstala hermes-agent y **wipea** `~/.hermes/plugins/`. Los plugins personal-ai se pierden.

```bash
# Restaurar plugins
bash ~/dotfiles-hermes-agent/scripts/restore.sh

# Verificar
hermes plugins list | grep personal-ai
```

Skills via `external_dirs` no necesitan acción — se recargan automáticamente.

---

## Backup

> ⚠️ `backup.sh` está roto — no copia archivos reales, solo symlinks. Hacer backup manualmente:

```bash
# Skills (con archivos reales, no symlinks)
cp -rL ~/.hermes/custom-skills/diego-shopping-scout/ ~/dotfiles-hermes-agent/skills/
for skill in diego-buenos-dias diego-read-it-later diego-research; do
  cp -rL ~/.hermes/skills/.archive/$skill/ ~/dotfiles-hermes-agent/skills/
done

# Plugins
bash ~/dotfiles-hermes-agent/scripts/restore.sh

# Push
cd ~/dotfiles-hermes-agent && git push
```

---

## Estructura del Repo

```
dotfiles-hermes-agent/
├── configs/
│   ├── config.yaml              # Config principal de Hermes
│   ├── .env.example             # Template de variables (sin secrets)
│   ├── MEMORY.md                # Memorias del agente (symlinked desde ~/.hermes/memories/)
│   ├── USER.md                  # Perfil del usuario (symlinked)
│   ├── channel_directory.json
│   ├── discord_threads.json
│   └── gateway_state.json
├── skills/
│   ├── diego-buenos-dias/       # Skill custom — survives via external_dirs
│   ├── diego-shopping-scout/    # Skill custom — survives via external_dirs
│   ├── diego-read-it-later/
│   └── diego-research/
├── plugins/
│   ├── personal-ai-memory/      # Plugin memory provider (post-update: restore.sh)
│   └── personal-ai-ledger/      # Plugin ledger/briefing
├── cron/
│   └── jobs.json                # Buenos Días job
├── gateway/builtin_hooks/
│   ├── personal_ai_client.py
│   └── personal_ai_memory_provider.py
├── scripts/
│   ├── backup.sh
│   └── restore.sh
├── SOUL.md                      # Personalidad del agente
└── README.md
```

---

## Comandos Útiles

```bash
# Backup
./scripts/backup.sh

# Restaurar plugins post-update
bash ~/dotfiles-hermes-agent/scripts/restore.sh

# Gateway
systemctl --user restart hermes-gateway
journalctl --user -u hermes-gateway -f

# Diagnóstico
hermes plugins list | grep personal-ai
hermes skills list  | grep diego
hermes doctor
```
