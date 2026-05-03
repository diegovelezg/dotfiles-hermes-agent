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

# 2. Plugins personal-ai (desde ~/.hermes/custom-plugins/ — survives Hermes updates)
# custom-plugins/ se crea manualmente y se respalda en el repo de dotfiles
# (no es un git repo propio — el backup está en dotfiles, el runtime en ~/.hermes/)
if [ -d "$HERMES_DIR/custom-plugins" ]; then
  rm -rf "$REPO_DIR/plugins"
  cp -r "$HERMES_DIR/custom-plugins" "$REPO_DIR/plugins"
  echo "  + plugins (desde custom-plugins)"
else
  # Fallback: respaldar los plugins activos desde ~/.hermes/plugins/
  rm -rf "$REPO_DIR/plugins"
  if [ -d "$HERMES_DIR/plugins/personal-ai-memory" ]; then
    mkdir -p "$REPO_DIR/plugins"
    cp -r "$HERMES_DIR/plugins/personal-ai-memory" "$HERMES_DIR/plugins/personal-ai-ledger" "$REPO_DIR/plugins/"
    echo "  + plugins (desde plugins/)"
  fi
fi

# 3. Skills (excluye custom skills de Diego — ya están en custom-skills/)
# Los custom skills (diego-*) se gestionan vía ~/.hermes/custom-skills/ con symlinks
rm -rf "$REPO_DIR/skills"
cp -r "$HERMES_DIR/skills" "$REPO_DIR/skills"
# Reemplaza los skills de Diego (que son symlinks) por copias reales de custom-skills
for skill in diego-buenos-dias diego-intel diego-read-it-later diego-research; do
  src="$HERMES_DIR/custom-skills/$skill"
  dst="$REPO_DIR/skills/$skill"
  if [ -L "$dst" ] || [ -d "$dst" ]; then
    rm -rf "$dst"
  fi
  if [ -d "$src" ]; then
    cp -r "$src" "$dst"
    echo "  + $skill (desde custom-skills)"
  fi
done

# 4. .env example (sin secrets)
grep -v "^#" "$ENV_FILE" | grep -v "^$" | sed 's/=.*/=***REDACTED***/' > "$REPO_DIR/configs/.env.example"

echo "Backup completado en $REPO_DIR"
echo "Archivos modificados:"
cd "$REPO_DIR" && git status --short
