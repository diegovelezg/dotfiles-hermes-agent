#!/bin/bash
# restore-secrets-from-bws.sh
# On a fresh machine, fetch the hermes-dotfiles-env secret from Bitwarden
# Secrets Manager and write it to ~/.hermes/.env (chmod 600).
#
# Prerequisites:
#   1. bws installed
#   2. BWS_ACCESS_TOKEN exported (same one used to upload)
#
# Usage:
#   export BWS_ACCESS_TOKEN="0.fc1....ffee"
#   ./scripts/restore-secrets-from-bws.sh

set -euo pipefail

HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
HERMES_ENV="$HERMES_HOME/.env"
SECRET_NAME="hermes-dotfiles-env"

if [ -z "${BWS_ACCESS_TOKEN:-}" ]; then
  echo "❌ BWS_ACCESS_TOKEN no está exportada." >&2
  exit 1
fi

# Find the secret ID by name
SECRET_ID=$(bws secret list 2>/dev/null | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    for s in data:
        if s.get('key') == '$SECRET_NAME':
            print(s.get('id', ''))
            break
except Exception as e:
    print(f'ERROR: {e}', file=sys.stderr)
    sys.exit(1)
")

if [ -z "$SECRET_ID" ]; then
  echo "❌ No se encontró el secret '$SECRET_NAME' en el proyecto accesible por este token." >&2
  echo "   Verificá que el token tenga acceso al proyecto correcto." >&2
  exit 1
fi

echo "📥 Descargando secret $SECRET_NAME (id: $SECRET_ID)..."
SECRET_VALUE=$(bws secret get "$SECRET_ID" | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(data.get('value', ''))
")

# Validate it's a JSON object
if ! echo "$SECRET_VALUE" | python3 -c "import json,sys; json.load(sys.stdin)" 2>/dev/null; then
  echo "❌ El secret value no es JSON válido. Abortando." >&2
  exit 1
fi

# Convert JSON object to .env format
mkdir -p "$HERMES_HOME"
echo "$SECRET_VALUE" | python3 -c "
import json, sys
data = json.load(sys.stdin)
for k, v in data.items():
    # Quote values that contain spaces or special chars
    needs_quote = any(c in str(v) for c in ' \"\\'#')
    if needs_quote:
        # Escape any existing double quotes
        escaped = str(v).replace('\"', '\\\\\"')
        print(f'{k}=\"{escaped}\"')
    else:
        print(f'{k}={v}')
" > "$HERMES_ENV"

chmod 600 "$HERMES_ENV"
KEY_COUNT=$(wc -l < "$HERMES_ENV")
echo "✅ $KEY_COUNT variables escritas en $HERMES_ENV (permisos 600)"
echo ""
echo "🔍 Verificá con:"
echo "   grep -c '^[A-Z_]' $HERMES_ENV"
echo "   head -3 $HERMES_ENV   # no commitees esto, es read-only"
