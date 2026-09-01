#!/usr/bin/env bash
# test-brave-x-auth.sh: arranca brave headless con perfil x, navega a x.com/home,
# verifica si esta autenticado mirando el titulo o la url, y deja screenshot.
# Uso:
#   ~/.hermes/bin/test-brave-x-auth.sh            # test
set -euo pipefail

PROFILE="${HERMES_BRAVE_PROFILE:-$HOME/.hermes/browser-data/agent}"
PORT="${HERMES_BRAVE_PORT:-9223}"
mkdir -p /tmp/hermes-brave-x-test

export HERMES_BRAVE_PROFILE="$PROFILE"
export HERMES_BRAVE_PORT="$PORT"

# Stop test anterior si quedo
pkill -f "remote-debugging-port=$PORT" 2>/dev/null || true
sleep 1

echo "== Lanzando brave headless =="
hermes-brave-x start "https://x.com/home" >/dev/null

echo "== Esperando CDP =="
CDP_URL=$(hermes-brave-x cdp)
echo "CDP: $CDP_URL"

echo "== Listando tabs (raw JSON, sin jq) =="
curl -sf "http://127.0.0.1:$PORT/json" | python3 -c "
import json,sys
for t in json.load(sys.stdin):
    print(f'  - {t.get(\"title\",\"\")} :: {t.get(\"url\",\"\")}')
"

echo ""
echo "== Esperando 8s a que cargue =="
sleep 8

echo "== Estado final =="
RAW=$(curl -sf "http://127.0.0.1:$PORT/json")
echo "$RAW" | python3 -c "
import json,sys
data = json.load(sys.stdin)
for t in data:
    title = t.get('title','')
    url = t.get('url','')
    print(f'  - TITLE: {title}')
    print(f'    URL:   {url}')
    if '/login' in url or '/i/flow/login' in url:
        print('    >>> NO autenticado (login page)')
    elif '/home' in url or '/compose' in url or 'twitter.com' in url and '/login' not in url:
        print('    >>> Posible sesion activa')
"

echo ""
echo "== Apagando =="
hermes-brave-x stop

echo ""
echo "Interpretacion:"
echo "  URL '/home' o sin /login  -> autenticado"
echo "  URL '/login' o '/i/flow/login' -> NO autenticado, volve a hacer login manual"
