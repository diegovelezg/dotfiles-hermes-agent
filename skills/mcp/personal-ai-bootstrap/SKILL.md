---
name: personal-ai-bootstrap
description: Bootstrap del Intelligence MCP v5 — obtiene Constitution, Policies y Session Init del servidor MCP de la UIA Personal AI de Diego. Mantiene sesión SSE persistente para manejar el protocolo HTTP+SSE del servidor.
version: 1.0.0
author: hermes
license: MIT
metadata:
  hermes:
    tags: [MCP, personal-ai, bootstrap, memory]
    homepage: self
prerequisites:
  commands: ["python3"]
  packages: ["sseclient-py"]
---

# Personal AI Bootstrap Skill

Usa el cliente SSE HTTP nativo para obtener Constitution, Policies y Session Init del Intelligence MCP v5.

## Arquitectura del servidor

El servidor MCP de la UIA (`uaimcp.papelitosdecolor.com`) usa:
- `GET /sse` → establece sesión SSE, responde con `endpoint` event que contiene el `sessionId`
- `POST /messages?sessionId=<id>` → envía requests JSON-RPC al servidor

Las primitivas MCP nativas (`prompts/get`, `resources/read`) **NO son tools** — son primitivas de protocolo. No se llaman con `mcporter call`. Requieren el cliente HTTP+SSE completo.

## Cliente Python SSE (requerido)

El servidor responde a POST con eventos SSE, no JSON HTTP. El cliente debe:
1. Abrir `/sse` en un thread consumidor de eventos
2. Extraer el `sessionId` del primer evento `endpoint`
3. Hacer POST a `/messages?sessionId=<id>` mientras el thread SSE sigue corriendo
4. Recoger respuestas del stream SSE

Sin el thread consumidor manteniendo la conexión SSE viva, el servidor dice "No session".

## Script: mcp_sse_client.py

```python
#!/usr/bin/env python3
"""MCP HTTP+SSE client para Intelligence MCP v5."""
import json, sys, time, threading
import requests
from sseclient import SSEClient

BASE_URL = "https://uaimcp.papelitosdecolor.com"

def create_client():
    """Abre SSE y retorna (session_id_holder, results_holder)."""
    r = requests.get(f"{BASE_URL}/sse", stream=True, timeout=10)
    r.raise_for_status()
    client = SSEClient(r)
    session_id = [None]
    results = []

    def consume():
        for event in client.events():
            if event.data.startswith("/messages"):
                session_id[0] = event.data.split("sessionId=")[1]
            elif event.event == "message" or event.data.startswith("{"):
                try:
                    results.append(json.loads(event.data))
                except:
                    pass

    t = threading.Thread(target=consume, daemon=True)
    t.start()
    time.sleep(0.5)
    return session_id, results

def post(session_id, method, params=None):
    """Envía request JSON-RPC al servidor MCP."""
    payload = {"jsonrpc": "2.0", "id": 1, "method": method}
    if params:
        payload["params"] = params
    r = requests.post(
        f"{BASE_URL}/messages?sessionId={session_id}",
        json=payload,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        timeout=10
    )
    return r

# ── Llamadas bootstrap ────────────────────────────────────────────────

# 1. Session Init (system prompt template)
sid, res = create_client()
time.sleep(0.3)
post(sid[0], "prompts/get", {"name": "session_init"})
time.sleep(3)
session_init = next((r["result"] for r in res if "result" in r), None)

# 2. Constitution (recurso estático)
sid2, res2 = create_client()
time.sleep(0.3)
post(sid2[0], "resources/read", {"uri": "instructions://inbox-sop"})
time.sleep(3)
constitution = next((r["result"] for r in res2 if "result" in r), None)

# 3. Policies activas (Supabase operational_rules)
sid3, res3 = create_client()
time.sleep(0.3)
post(sid3[0], "tools/call", {
    "name": "memories_search",
    "arguments": {"type": "policy", "user_id": "1093162286", "limit": 15}
})
time.sleep(3)
policies = next((r["result"] for r in res3 if "result" in r), None)

# 4. Memories episódicas (Mem0 know + episodic) — para contexto de sesión
sid4, res4 = create_client()
time.sleep(0.3)
post(sid4[0], "tools/call", {
    "name": "memories_search",
    "arguments": {"user_id": "1093162286", "query": "proyectos activos tareas prioridades", "limit": 30}
})
time.sleep(3)
memories = next((r["result"] for r in res4 if "result" in r), None)

# Resultados
print("=== SESSION_INIT ===")
print(json.dumps(session_init, indent=2))
print("=== CONSTITUTION ===")
print(json.dumps(constitution, indent=2)[:2000])
print("=== POLICIES ===")
print(json.dumps(policies, indent=2)[:3000])
print("=== MEMORIES ===")
print(json.dumps(memories, indent=2)[:3000])
```

## Instalación de dependencias

```bash
uv pip install sseclient-py requests
# o
pip install sseclient-py requests
```

## Verificación

```bash
python3 mcp_sse_client.py
```

## Notas

- El servidor NO mantiene estado entre requests sin la conexión SSE abierta
- El bridge `personal-ai-bridge` permite invocar cualquier primitiva MCP de forma nativa via stdio
- El cliente SSE es stateful — mantiene la sesión HTTP viva durante toda la sesión de bootstrap
- Instalar `sseclient-py` (no `sseclient` que es otro paquete)
