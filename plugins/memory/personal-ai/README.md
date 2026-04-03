# Personal AI Memory Provider Plugin

**Plugin:** `plugins/memory/personal-ai`
**For:** Hermes Agent v0.7.0+
**Author:** Diego Vélez

Integrates Diego's custom personal-ai MCP v5 (Mem0-backed) as a first-class memory provider, replacing the legacy hook-based injection system.

---

## What it does

The `PersonalAIMemoryProvider` subclasses the v0.7.0 `MemoryProvider` ABC and connects to the personal-ai MCP via the SSE+JSON-RPC bridge protocol. It exposes 7 tools to the model and provides recall context via the `prefetch()` hook.

### Tools exposed to the model

| Tool | Description |
|------|-------------|
| `personal_ai_search` | Semantic search over know/policy/episodic memories |
| `personal_ai_memories_manage` | Create, update, use, deprecate memories |
| `personal_ai_briefing_generate` | Daily briefing from ledger + memories |
| `personal_ai_ledger_query` | Query action/intel ledger items |
| `personal_ai_ledger_item_create` | Create a new ledger item |
| `personal_ai_ledger_bulk_action` | Bulk update multiple ledger items |
| `personal_ai_browser_activity_query` | Query browser history |

---

## Architecture

```
MemoryManager (hermes-agent core v0.7.0)
    │
    ├── BuiltinMemoryProvider  (MEMORY.md/USER.md — always on)
    │
    └── PersonalAIMemoryProvider (this plugin)
         │
         ├── initialize()       → SSE connect to personal-ai MCP
         ├── prefetch()          → recall context (cached, 2min TTL)
         ├── system_prompt_block() → static memory instructions
         ├── get_tool_schemas()  → 7 tools exposed to model
         ├── handle_tool_call()  → dispatch to personal-ai MCP
         ├── on_turn_start()     → refresh cache every 10 turns
         └── shutdown()          → close SSE connections
```

### vs. Legacy Hook

| | Legacy Hook (`personal-ai-memory-loader`) | New Plugin |
|---|---|---|
| Integration point | `session:start` event → writes MEMORY.md | `MemoryProvider` ABC → native lifecycle |
| SSOT | personal-ai MCP → MEMORY.md → MemoryStore | personal-ai MCP direct |
| Tools exposed | None | 7 tools |
| Timing | Before agent init (brittle) | Native `initialize()` / `prefetch()` |
| Maintenance | Custom hook code | Standard plugin interface |

---

## Setup

### 1. Install the plugin

```bash
cd ~/dotfiles-hermes-agent/plugins/memory/personal-ai
# Plugin auto-discovers on hermes-agent startup from plugins/memory/<name>/
```

### 2. Ensure env vars are set

```bash
# In ~/.hermes/.env (already configured):
PERSONAL_AI_BASE_URL=https://uaimcp.papelitosdecolor.com
PERSONAL_AI_API_KEY=<your-key>
PERSONAL_AI_REMOTE_URL=https://uaimcp.papelitosdecolor.com/sse
PERSONAL_AI_USER_ID=1093162286
```

### 3. Activate in config

```yaml
# ~/.hermes/config.yaml
memory:
  provider: personal-ai
```

### 4. Restart hermes-agent

```bash
systemctl --user restart hermes-gateway
# Or: hermes update && hermes tools install
```

---

## Memory Types

| Type | Description | Example |
|------|-------------|---------|
| `know` | Persistent facts about Diego | Preferences, projects, people, habits |
| `policy` | Operational rules | "Diego prefers Spanish, responses without markdown" |
| `episodic` | Past events and experiences | "Completed focus groups on April 2-3, 2026" |

---

## Deprecating the Legacy Hook

Once the plugin is verified working:

1. Remove or rename `~/.hermes/hooks/personal-ai-memory-loader/` → becomes inactive
2. Delete the `<!-- PERSONAL-AI-INJECT -->` section from `~/.hermes/memories/MEMORY.md` (builtin now pulls direct)
3. The `personal-ai-memory-loader` dotfiles entry in `hooks/` can be removed from the repo

---

## Troubleshooting

### Plugin not loading
```bash
hermes memory setup  # walk through wizard
hermes doctor        # check memory provider status
```

### SSE connection errors
Check that `PERSONAL_AI_REMOTE_URL` is reachable from the server:
```bash
curl -I https://uaimcp.papelitosdecolor.com/sse
```

### Tools not showing up
Verify `memory.provider: personal-ai` is set in `config.yaml` (not `config.yml`).

---

## Development

The plugin is self-contained in `__init__.py`. Key classes:

- `PersonalAIClient` — SSE+MCP bridge protocol client (same logic as legacy hook)
- `PersonalAIMemoryProvider` — `MemoryProvider` ABC implementation
- `register()` — plugin entry point called by `MemoryManager`

### Testing manually

```python
from plugins.memory.personal_ai import PersonalAIMemoryProvider, PersonalAIClient

client = PersonalAIClient()
print(client.search_memories("Diego project房地产"))
```
