#!/usr/bin/env python3
"""MCP HTTP+SSE client para Intelligence MCP v5 - UIA Personal AI de Diego.

El servidor MCP usa HTTP+SSE. Para cada llamada:
1. Se abre GET /sse en un thread que consume eventos
2. Se extrae el sessionId del primer evento endpoint
3. Se hace POST a /messages?sessionId=<id> mientras el thread corre
4. Se recoge la respuesta del stream SSE
"""
import json
import sys
import time
import threading
import requests
from sseclient import SSEClient

BASE_URL = "https://uaimcp.papelitosdecolor.com"
USER_ID = "1093162286"


def create_client():
    """Abre SSE y retorna (session_id_holder, results_holder, client)."""
    r = requests.get(f"{BASE_URL}/sse", stream=True, timeout=10)
    r.raise_for_status()
    client = SSEClient(r)
    session_id = [None]
    results = []

    def consume():
        for event in client.events():
            if event.data.startswith("/messages"):
                session_id[0] = event.data.split("sessionId=")[1]
                print(f"[SSE] Session: {session_id[0]}", file=sys.stderr)
            elif event.event == "message" or event.data.startswith("{"):
                try:
                    results.append(json.loads(event.data))
                except Exception as e:
                    print(f"[SSE] Parse error: {e}", file=sys.stderr)

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


def get_session_init():
    sid, res = create_client()
    time.sleep(0.3)
    post(sid[0], "prompts/get", {"name": "session_init"})
    time.sleep(3)
    return next((r["result"] for r in res if "result" in r), None)


def get_constitution():
    sid, res = create_client()
    time.sleep(0.3)
    post(sid[0], "resources/read", {"uri": "instructions://inbox-sop"})
    time.sleep(3)
    return next((r["result"] for r in res if "result" in r), None)


def get_policies(limit=15):
    sid, res = create_client()
    time.sleep(0.3)
    post(sid[0], "tools/call", {
        "name": "memories_search",
        "arguments": {"type": "policy", "user_id": USER_ID, "limit": limit}
    })
    time.sleep(3)
    return next((r["result"] for r in res if "result" in r), None)


def get_memories(query="proyectos activos tareas prioridades", limit=30):
    sid, res = create_client()
    time.sleep(0.3)
    post(sid[0], "tools/call", {
        "name": "memories_search",
        "arguments": {"user_id": USER_ID, "query": query, "limit": limit}
    })
    time.sleep(3)
    return next((r["result"] for r in res if "result" in r), None)


def bootstrap():
    """Obtiene todo lo necesario al inicio de sesión."""
    print("=== BOOTSTRAPPING UIA PERSONAL AI ===", file=sys.stderr)
    
    session_init = get_session_init()
    print(f"session_init: {'OK' if session_init else 'EMPTY'}", file=sys.stderr)
    
    constitution = get_constitution()
    print(f"constitution: {'OK' if constitution else 'EMPTY'}", file=sys.stderr)
    
    policies = get_policies()
    print(f"policies: {'OK' if policies else 'EMPTY'}", file=sys.stderr)
    
    memories = get_memories()
    print(f"memories: {'OK' if memories else 'EMPTY'}", file=sys.stderr)
    
    return {
        "session_init": session_init,
        "constitution": constitution,
        "policies": policies,
        "memories": memories,
    }


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--bootstrap":
        result = bootstrap()
        print(json.dumps(result, indent=2, ensure_ascii=False))
    elif len(sys.argv) == 3:
        # Direct call: python mcp_sse_client.py <method> <params_json>
        method = sys.argv[1]
        params = json.loads(sys.argv[2]) if sys.argv[2] != "{}" else None
        sid, res = create_client()
        time.sleep(0.3)
        post(sid[0], method, params)
        time.sleep(3)
        result = next((r["result"] for r in res if "result" in r), None)
        print(json.dumps(result, indent=2, ensure_ascii=False) if result else "No response")
    else:
        # Solo bootstrap
        result = bootstrap()
        print(json.dumps(result, indent=2, ensure_ascii=False))
