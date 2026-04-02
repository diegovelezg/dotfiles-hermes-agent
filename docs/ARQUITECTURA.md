# Arquitectura y Configuración de Hermes Agent

## Stack de backends web

### Búsqueda (web_search_tool)
Orden de fallback: **Exa → Brave**

- **Default**: Exa Search
- **Fallback**: Brave Search (cuando Exa falla)
- Config: `web.backend: exa` en config.yaml
- Si no hay backend explícito: `_get_backend()` retorna "exa"

### Extracción (web_extract_tool)
- Usa el mismo backend que la búsqueda
- Firecrawl → Exa → Brave (fallback chain)

## Modelos LLM

| Rol | Modelo | Provider |
|-----|--------|----------|
| Coordinación | MiniMax-M2 (default) | minimax |
| Investigación pesada | DeepSeek-V3 / DeepSeek-R1 | OpenRouter |
| Visión | MiniMax-V06 | minimax |

## API Keys configuradas

Ver `configs/.env.example` para la lista de variables requeridas.

### Actual (`.env` real)
```
BRAVE_API_KEY=BSAoynGh-Yb5ZuagHbqS5sbeX3Dy4Mt
EXA_API_KEY=c785bef5-42cf-41c4-abd3-c04cf9486808
OPENROUTER_API_KEY=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
```

## Patches personalizados aplicados

### 1. `tools/web_tools.py` — Brave Search

**Problema**: El código original usaba endpoint incorrecto (`reso/v1/`) y auth wrong.

**Cambios aplicados**:
- Endpoint: `reso/v1/search` → `res/v1/web/search`
- Auth: `Authorization: Bearer` → `X-Subscription-Token`
- HTTP client: `urllib` → `httpx` (para gzip decompression automático)

**Archivos modificados**:
- `_brave_search_request()`: usa httpx con `X-Subscription-Token`
- `_brave_search()`: endpoint `web/search`
- `_get_backend()`: ahora default "exa" (antes fallback automático por key)
- `_get_fallback_backend()`: nueva función (exa → brave)

### 2. `tools/delegate_tool.py` — Provider/Model override

**Problema**: Los parámetros `provider` y `model` eran ignorados al delegar.

**Cambio**: Se asegura que `model` y `provider` se propaguen correctamente al subagente.

## Skills instalados

Ver directorio `skills/` para cada skill.

### Skills principales
- `buenos-dias`: Reporte matutino 5 fuentes → audio .ogg
- `autonomous-ai-agents`: Delegar a subagentes (Claude Code, Codex, OpenCode)
- `research`: Búsqueda académica (arXiv, etc.)
- `mcp`: Conexión MCP servers (personal-ai, browser, etc.)

## Flujo de investigación típico

```
1. web_search (Exa, limit=5) 
2. web_extract (urls seleccionados)
3. DeepSeek-V3 via OpenRouter → síntesis
4. Presentación al usuario
```

Si Exa falla → Brave como fallback automático.

## Gateway / Plataformas

- **Telegram**: DM a @tu_bot
- **Discord**: Conectado, canal home
- **Gateway**: corre en background (systemd)

## Notas

- La config real con API keys NO se sube al repo (solo `.env.example`)
- Skills敏感内容保存在本地
- Patches aplicados a `hermes-agent/` se documentan en `patches/`
