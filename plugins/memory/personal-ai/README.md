# Personal AI Memory Provider Plugin

**Plugin:** `plugins/memory/personal-ai`
**For:** Hermes Agent v0.7.0+
**Author:** Diego Vélez

Exposes memory tools (know/policy/episodic search & management) from Diego's personal-ai MCP v5 (Mem0-backed). Ledger/briefing/browser tools are in the separate `personal-ai-ledger` plugin.

---

## What it does

The `PersonalAIMemoryProvider` subclasses the v0.7.0 `MemoryProvider` ABC and connects to the personal-ai MCP via SSE+JSON-RPC. It exposes 2 memory tools to the model and provides recall at session start.

## Tools exposed

| Tool | Description |
|------|-------------|
| `personal_ai_memories_search` | Semantic search over know/policy/episodic memories |
| `personal_ai_memories_manage` | Create, update, use, deprecate memories |

## Architecture

```
PersonalAIMemoryProvider
    ├── PersonalAIClient  (SSE → personal-ai MCP)
    ├── prefetch()        → recall know+policy at session start
    ├── get_tool_schemas() → 2 memory tools
    └── handle_tool_call() → dispatch to MCP
```

## Memory types

| Type | Description |
|------|-------------|
| `know` | Persistent facts about Diego |
| `policy` | Operational rules |
| `episodic` | Past events |

## Config

Uses env vars from `~/.hermes/.env`:
- `PERSONAL_AI_BASE_URL`
- `PERSONAL_AI_API_KEY`
- `PERSONAL_AI_REMOTE_URL`
- `PERSONAL_AI_USER_ID`
