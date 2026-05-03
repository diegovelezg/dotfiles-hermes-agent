#!/bin/bash
# Restore script — by the book según Hermes docs
# Skills: external_dirs en config.yaml las hace sobrevivir updates (no necesitan restore)
# Plugins: sí requieren restore porque ~/.hermes/plugins/ se wipea en updates
#
# Usage: bash ~/dotfiles-hermes-agent/scripts/restore.sh
# Post-update: copia plugins del repo → ~/.hermes/plugins/

set -e

HERMES_DIR="${HERMES_HOME:-$HOME/.hermes}"
REPO_DIR="$HOME/dotfiles-hermes-agent"
PLUGINS_DIR="$HERMES_DIR/plugins"

echo "=== Hermes restore ==="
echo "Source: $REPO_DIR/plugins/"
echo "Target: $PLUGINS_DIR"
echo ""

# Restore plugins (skills via external_dirs no necesitan esto)
echo "Restoring plugins..."
for plugin in personal-ai-memory personal-ai-ledger; do
    src="$REPO_DIR/plugins/$plugin"
    dst="$PLUGINS_DIR/$plugin"
    if [ -d "$src" ]; then
        rm -rf "$dst"
        cp -r "$src" "$dst"
        echo "  ✓ $plugin"
    else
        echo "  ✗ $plugin not found in repo, skipping"
    fi
done

echo ""
echo "Done. To verify:"
echo "  hermes plugins list | grep personal-ai"
echo ""
echo "Skills are loaded via external_dirs in config.yaml — no restore needed."
