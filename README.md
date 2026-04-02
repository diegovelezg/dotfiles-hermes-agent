# dotfiles-hermes-agent

Configuraciones, patches y scripts para mi setup de Hermes Agent (Claude Code).

## Estructura

```
dotfiles-hermes-agent/
├── configs/              # Configuraciones de ~/.hermes/
│   ├── config.yaml       # Config principal (sin API keys)
│   ├── .env.example      # Variables de entorno requeridas
│   └── gateway_*.json    # Estado de canales
├── skills/              # Skills instalados en ~/.hermes/skills/
├── scripts/
│   └── backup.sh        # Script de backup idempotente
├── patches/
│   └── brave-search.patch  # Patches aplicados al core
├── docs/
│   └── ARQUITECTURA.md   # Documentación de la arquitectura
└── README.md
```

## Setup rápido

```bash
# Clonar
git clone https://github.com/diegovelezg/dotfiles-hermes-agent.git ~/dotfiles-hermes-agent

# Restaurar configs
cp configs/config.yaml ~/.hermes/config.yaml

# Configurar .env
cp configs/.env.example ~/.hermes/.env
# Editar ~/.hermes/.env con tus API keys reales

# Restaurar skills
cp -r skills/* ~/.hermes/skills/
```

## API Keys requeridas

```
BRAVE_API_KEY=       # Brave Search API (Data for Search plan)
EXA_API_KEY=         # Exa Search API
OPENROUTER_API_KEY=  # OpenRouter (para DeepSeek)
```

## Patches aplicados

### brave-search.patch
Corrige `tools/web_tools.py` para usar Brave Search correctamente:
- Endpoint: `res/v1/web/search` (no `reso/v1/search`)
- Auth: `X-Subscription-Token` header (no Bearer)
- HTTP client: httpx (para gzip decompression)

Para reaplicar:
```bash
cd ~/dotfiles-hermes-agent
patch -p1 < patches/brave-search.patch
```

## Web Search Backend

- **Default**: Exa Search
- **Fallback**: Brave Search (cuando Exa falla)
- Fallback chain: `web_search_tool` intenta Exa → si falla, usa Brave automáticamente

## Modelo de investigación

```
web_search (Exa) → web_extract → DeepSeek-V3 (OpenRouter) → respuesta
                    ↓ si falla
              Brave search → DeepSeek
```

## Backup

```bash
./scripts/backup.sh
```

Esto respaldará:
- `~/.hermes/config.yaml`
- `~/.hermes/gateway_state.json`
- `~/.hermes/channel_directory.json`
- `~/.hermes/skills/` (todos)
- `.env.example` (sin API keys reales)

## Actualizar repo

```bash
cd ~/dotfiles-hermes-agent
git add -A
git commit -m "backup: $(date +'%Y-%m-%d')"
git push
```
