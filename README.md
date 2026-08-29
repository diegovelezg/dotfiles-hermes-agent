# Diego's Hermes Custom Stuff

Backup of Diego's custom skills and plugins for Hermes Agent.

Following the official Hermes docs:
- [Creating Skills](https://hermes-agent.nousresearch.com/docs/developer-guide/creating-skills)
- [Build a Plugin](https://hermes-agent.nousresearch.com/docs/guides/build-a-hermes-plugin)
- [Working with Skills](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills)
- [Plugins](https://hermes-agent.nousresearch.com/docs/user-guide/features/plugins)

## Layout

```
.
├── skills/                          # 6 custom skills (by the book: SKILL.md per skill)
│   ├── diego-buenos-dias/SKILL.md
│   ├── diego-read-it-later/SKILL.md
│   ├── diego-research/SKILL.md
│   ├── diego-research/references/   # additional docs loaded on demand
│   ├── diego-shopping-scout/SKILL.md
│   ├── diego-shopping-scout/scripts/  # helper scripts called from the skill
│   ├── diego-chrome-remote-control/SKILL.md
│   └── brave-auth-agent/            # persistent Brave profile for authenticated browsing
│       ├── SKILL.md
│       └── assets/
│
└── plugins/                         # 2 custom plugins (by the book: plugin.yaml + Python)
    ├── personal-ai-memory/          # NOT installed — superseded by Hindsight (SSOT)
    │   ├── plugin.yaml
    │   └── __init__.py
    └── personal-ai-ledger/
        ├── plugin.yaml
        ├── __init__.py
        ├── tools.py
        └── schemas.py
```

## Active vs archived

- **Skills** (`diego-*` + `brave-auth-agent`) → drop into `~/.hermes/skills/`
- **Plugins**:
  - `personal-ai-ledger` → drop into `~/.hermes/plugins/`
  - `personal-ai-memory` → **DO NOT INSTALL**. Superseded by Hindsight Cloud (see `~/.hermes/memories/`). Installing both creates a dual-SSOT conflict.

## Install on a new machine

```bash
# Skills — drop into ~/.hermes/skills/
mkdir -p ~/.hermes/skills
cp -r skills/* ~/.hermes/skills/

# Plugins — only personal-ai-ledger; skip personal-ai-memory
mkdir -p ~/.hermes/plugins
cp -r plugins/personal-ai-ledger ~/.hermes/plugins/

# Verify
hermes skills list
hermes plugins list
hermes doctor
```

## Restore

The runtime data, configs, secrets, and skill outputs are intentionally **not** in this repo — they live in `~/.hermes/` and are regenerated from the sources here on a fresh install.

Last sync with `~/.hermes/`: 2026-08-29.