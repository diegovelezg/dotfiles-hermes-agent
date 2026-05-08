#!/bin/bash
# Backup de configuraciones de Hermes Agent
# Solo lo que necesita Diego: configs, plugins personal-ai, skills custom
# Uso: ./scripts/backup.sh

set -e

HERMES_DIR="${HERMES_HOME:-$HOME/.hermes}"
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$HERMES_DIR/.env"

echo "=== Hermes Agent Backup ==="

# 1. Configs
cp "$HERMES_DIR/config.yaml" "$REPO_DIR/configs/config.yaml"
cp "$HERMES_DIR/gateway_state.json" "$REPO_DIR/configs/gateway_state.json" 2>/dev/null || true
cp "$HERMES_DIR/channel_directory.json" "$REPO_DIR/configs/channel_directory.json" 2>/dev/null || true

# 2. Plugins personal-ai (se wipean en hermes update — requieren backup)
rm -rf "$REPO_DIR/plugins"
mkdir -p "$REPO_DIR/plugins"
for plugin in personal-ai-memory personal-ai-ledger; do
    src="$HERMES_DIR/plugins/$plugin"
    dst="$REPO_DIR/plugins/$plugin"
    if [ -d "$src" ]; then
        cp -r "$src" "$dst"
        echo "  + $plugin"
    fi
done

# 3. Skills custom de Diego (desde custom-skills/, archivos reales)
for skill in diego-buenos-dias diego-intel diego-read-it-later diego-research diego-shopping-scout; do
    src="$HERMES_DIR/custom-skills/$skill"
    dst="$REPO_DIR/skills/$skill"
    if [ -d "$src" ]; then
        rm -rf "$dst"
        cp -r "$src" "$dst"
        echo "  + $skill"
    fi
done

# 4. .env.example (sin secrets)
grep -v "^#" "$ENV_FILE" | grep -v "^$" | sed 's/=.*/=***REDACTED***/' > "$REPO_DIR/configs/.env.example"

echo ""
echo "Backup completado"
cd "$REPO_DIR" && git status --short
