#!/bin/bash
# upload-secrets-to-bws.sh
# One-time migration: upload all current ~/.hermes/.env keys to Bitwarden Secrets Manager
# as a single multi-line secret named "hermes-dotfiles-env".
#
# After running this once, ~/.hermes/.env can be deleted from disk and
# Hermes Agent will load the secrets at boot from Bitwarden via BWS_ACCESS_TOKEN.
#
# Prerequisites:
#   1. bws installed (https://bitwarden.com/help/secrets-manager-cli/)
#   2. A Bitwarden Secrets Manager project created in the web vault
#   3. A Machine Account access token for that project
#   4. BWS_ACCESS_TOKEN and BWS_PROJECT_ID exported in your env
#
# Usage:
#   export BWS_ACCESS_TOKEN="0.fc1...your-token...c0ffee"
#   export BWS_PROJECT_ID="00000000-0000-0000-0000-000000000000"
#   ./scripts/upload-secrets-to-bws.sh          # dry-run
#   ./scripts/upload-secrets-to-bws.sh --apply  # actually upload

set -euo pipefail

HERMES_ENV="${HERMES_HOME:-$HOME/.hermes}/.env"
DRY_RUN=true
[[ "${1:-}" == "--apply" ]] && DRY_RUN=false

if [ -z "${BWS_ACCESS_TOKEN:-}" ]; then
  echo "❌ BWS_ACCESS_TOKEN no está exportada. Obtenela en:" >&2
  echo "   https://vault.bitwarden.com → Secrets Manager → Machine Accounts" >&2
  exit 1
fi

if [ -z "${BWS_PROJECT_ID:-}" ]; then
  echo "❌ BWS_PROJECT_ID no está exportada. Creá un proyecto en:" >&2
  echo "   https://vault.bitwarden.com → Secrets Manager → Projects" >&2
  exit 1
fi

if [ ! -f "$HERMES_ENV" ]; then
  echo "❌ No existe $HERMES_ENV" >&2
  exit 1
fi

# Validate token works
if ! bws project list >/dev/null 2>&1; then
  echo "❌ BWS_ACCESS_TOKEN inválido o sin acceso al proyecto $BWS_PROJECT_ID" >&2
  exit 1
fi

# Build a JSON object with all env vars
echo "📦 Leyendo $HERMES_ENV..."
export HERMES_ENV_FILE="$HERMES_ENV"
SECRET_JSON=$(HERMES_ENV_FILE="$HERMES_ENV" python3 - <<'PYEOF'
import json, re, os
result = {}
with open(os.environ['HERMES_ENV_FILE']) as f:
    for line in f:
        line = line.rstrip('\n')
        if not line or line.startswith('#'):
            continue
        m = re.match(r'^([A-Z_][A-Z0-9_]*)=(.*)$', line)
        if m:
            key, val = m.group(1), m.group(2)
            # Strip surrounding quotes if present
            if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                val = val[1:-1]
            result[key] = val
print(json.dumps(result, indent=2, ensure_ascii=False))
PYEOF
)

KEY_COUNT=$(echo "$SECRET_JSON" | python3 -c "import json,sys; print(len(json.load(sys.stdin)))")
echo "📋 $KEY_COUNT variables encontradas"

# Check if secret already exists
SECRET_NAME="hermes-dotfiles-env"
EXISTING_ID=$(bws secret list 2>/dev/null | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    for s in data:
        if s.get('key') == '$SECRET_NAME':
            print(s.get('id', ''))
            break
except: pass
")

if [ -n "$EXISTING_ID" ]; then
  echo "⚠️  El secret '$SECRET_NAME' ya existe (id: $EXISTING_ID)"
  if $DRY_RUN; then
    echo "🔍 DRY-RUN: actualizaría el secret existente con $KEY_COUNT keys"
  else
    echo "🔄 Actualizando secret existente..."
    bws secret update "$EXISTING_ID" --value "$SECRET_JSON" >/dev/null
    echo "✅ Secret actualizado"
  fi
else
  if $DRY_RUN; then
    echo "🔍 DRY-RUN: crearía nuevo secret '$SECRET_NAME' con $KEY_COUNT keys"
  else
    echo "📤 Creando secret '$SECRET_NAME'..."
    bws secret create "$SECRET_NAME" "$SECRET_JSON" --project-id "$BWS_PROJECT_ID" \
      --note "Diego's Hermes Agent env (Telegram, Discord, Mem0, OpenRouter, MiniMax, etc). Source: ~/.hermes/.env — uploaded 2026-06-06." \
      >/dev/null
    NEW_ID=$(bws secret list | python3 -c "
import json, sys
data = json.load(sys.stdin)
for s in data:
    if s.get('key') == '$SECRET_NAME':
        print(s.get('id', ''))
        break
")
    echo "✅ Secret creado con id: $NEW_ID"
  fi
fi

if $DRY_RUN; then
  echo ""
  echo "🔍 DRY-RUN completado. Para aplicar:"
  echo "   $0 --apply"
  echo ""
  echo "Keys que se subirán:"
  echo "$SECRET_JSON" | python3 -c "
import json, sys
data = json.load(sys.stdin)
for k in sorted(data.keys()):
    val = data[k]
    masked = val[:4] + '***' + val[-2:] if len(val) > 8 else '***'
    print(f'  {k} = {masked}')
" | head -20
  echo "  ..."
fi
