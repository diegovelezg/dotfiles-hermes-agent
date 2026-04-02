#!/bin/bash
# Backup de configuraciones de Hermes Agent
# Uso: ./scripts/backup.sh

set -e

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
HERMES_DIR="${HERMES_HOME:-$HOME/.hermes}"
ENV_FILE="$HERMES_DIR/.env"

echo "=== Hermes Agent Backup ==="

# 1. Configs (limpias)
cp "$HERMES_DIR/config.yaml" "$REPO_DIR/configs/config.yaml"
cp "$HERMES_DIR/gateway_state.json" "$REPO_DIR/configs/gateway_state.json" 2>/dev/null || true
cp "$HERMES_DIR/channel_directory.json" "$REPO_DIR/configs/channel_directory.json" 2>/dev/null || true

# 2. Skills
rm -rf "$REPO_DIR/skills"
cp -r "$HERMES_DIR/skills" "$REPO_DIR/skills"

# 3. .env example (sin secrets)
grep -v "^#" "$ENV_FILE" | grep -v "^$" | sed 's/=.*/=***REDACTED***/' > "$REPO_DIR/configs/.env.example"

echo "Backup completado en $REPO_DIR"
echo "Archivos modificados:"
cd "$REPO_DIR" && git status --short
