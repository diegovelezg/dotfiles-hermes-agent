# dotfiles-hermes-agent

Backup versionado de la configuración custom de Hermes Agent para el profile `notas` de Diego.

Sincronizado desde `~/.hermes/profiles/notas/` → este repo.

## Layout

```
.
├── config/
│   ├── config.yaml         # Hermes gateway config (modelos, providers, tools)
│   ├── profile.yaml        # metadata del profile "notas"
│   ├── SOUL.md             # identidad/convenciones del agente
│   └── .env.example        # template de secrets (sin valores reales)
│
├── memories/
│   ├── MEMORY.md           # reglas activas del agente
│   └── USER.md             # perfil de Diego
│
├── skills/                 # 4 skills custom (formato Hermes: SKILL.md)
│   ├── diego-brave-auth-agent/   # Brave persistente para X, Gmail, Reddit
│   ├── diego-notes/              # guarda notas en ledger MCP
│   ├── diego-research/           # investigación dialéctica (Tesis/Antítesis/Síntesis)
│   └── diego-shopping-scout/     # monitor de precios con detección de cambios
│
├── cron/                   # jobs programados (vacío por ahora)
│
└── .gitignore              # excluye runtime, caches, secrets
```

## Restore en otra máquina

```bash
# Clonar
git clone https://github.com/diegovelezg/dotfiles-hermes-agent.git

# Skills
mkdir -p ~/.hermes/profiles/notas/skills
cp -r skills/* ~/.hermes/profiles/notas/skills/

# Config + memories + cron + SOUL
mkdir -p ~/.hermes/profiles/notas
cp -r config/* ~/.hermes/profiles/notas/
cp -r memories/. ~/.hermes/profiles/notas/memories/
cp -r cron/. ~/.hermes/profiles/notas/cron/

# Renombrar .env.example → .env y rellenar secrets
cp config/.env.example ~/.hermes/profiles/notas/.env
$EDITOR ~/.hermes/profiles/notas/.env

# Verify
hermes skills list
hermes doctor
```

## Lo que NO está aquí (intencional)

- **Runtime data**: `state.db`, `sessions/`, `cache/`, `audio_cache/`, `image_cache/`, `logs/`, `runtime/`
- **Secrets reales**: solo `.env.example` con las keys vacías
- **Desktop local**: `desktop/`, `workspace/`, `home/`, `hooks/`, `pets/`, `skins/`
- **Hindsight SSOT**: las memorias duraderas viven en Hindsight (cloud), no en archivos locales
- **Backups automáticos**: `*.bak.*`, `*.lock`, `*.db`

Todo eso se regenera al correr Hermes con la config versionada.
