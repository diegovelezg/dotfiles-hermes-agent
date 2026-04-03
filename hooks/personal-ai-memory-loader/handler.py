"""
Hook: session:start
Carga memories know+policy de personal-ai al inicio de cada sesión nueva.
Usa el protocolo SSE+POST del MCP bridge — MISMMO cliente para GET y POST.
"""
import asyncio
import json
import os
import re
import httpx
from pathlib import Path

REMOTE_URL = os.environ.get("PERSONAL_AI_REMOTE_URL", "https://uaimcp.papelitosdecolor.com/sse")
BASE_URL = os.environ.get("PERSONAL_AI_BASE_URL", "https://uaimcp.papelitosdecolor.com")
API_KEY = os.environ.get("PERSONAL_AI_API_KEY", "")
MEMORY_FILE = Path("/root/.hermes/memories/MEMORY.md")
SECTION_START = "<!-- PERSONAL-AI-INJECT-START -->"
SECTION_END = "<!-- PERSONAL-AI-INJECT-END -->"


def _headers() -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "x-api-key": API_KEY,
    }


async def handle(event_type: str, context: dict) -> None:
    """Load and inject memories on session:start event."""
    if event_type not in ("session:start", "session:reset"):
        return

    user_id = context.get("user_id", "")
    if user_id != "1093162286":
        return

    try:
        memories = await _fetch_memories()
        _inject_into_memory(memories)
    except Exception:
        pass


async def _fetch_memories() -> list[str]:
    """
    Personal-ai MCP protocol using SSE:
    1. GET /sse → receives session_id in SSE data (keeps connection open)
    2. POST /messages?sessionId=... → sends JSON-RPC on SAME keep-alive connection
    3. Response arrives as SSE data events on the open GET connection
    """
    session_id = None
    messages_queue: list[dict] = []

    async def sse_reader(http: httpx.AsyncClient):
        """Background task: reads SSE events until cancelled."""
        nonlocal session_id
        try:
            async with http.stream("GET", REMOTE_URL, headers=_headers()) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if "sessionId=" in line:
                        session_id = line.split("sessionId=")[1].split()[0].strip()
                    elif line.startswith("data:") and line[5:].strip().startswith("{"):
                        try:
                            messages_queue.append(json.loads(line[5:].strip()))
                        except json.JSONDecodeError:
                            pass
        except Exception:
            pass

    try:
        # Create ONE shared HTTP client (HTTP/1.1 keep-alive)
        http = httpx.AsyncClient(verify=False, timeout=30.0)

        # Start SSE reader in background — keeps GET connection open
        reader_task = asyncio.create_task(sse_reader(http))

        # Wait for session_id
        for _ in range(100):
            if session_id:
                break
            await asyncio.sleep(0.1)
        else:
            raise RuntimeError("Timeout waiting for sessionId")

        if not session_id:
            return []

        # POST requests on the SAME client (keep-alive)
        results = []
        msg_url = f"{BASE_URL}/messages?sessionId={session_id}"

        for mem_type in ("know", "policy"):
            payload = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "memories_search",
                    "arguments": {
                        "type": mem_type,
                        "status": "active",
                        "user_id": "1093162286",
                        "limit": 20,
                    },
                },
                "id": f"hook-{mem_type}",
            }

            messages_queue.clear()
            post_resp = await http.post(
                msg_url,
                json=payload,
                headers=_headers(),
            )
            post_resp.raise_for_status()

            # Wait for response in SSE queue
            for _ in range(50):
                if any("result" in m or "error" in m for m in messages_queue):
                    break
                await asyncio.sleep(0.1)

            for msg in messages_queue:
                if "result" in msg:
                    # Response is wrapped: result.content[0].text is a JSON string
                    content_list = msg["result"].get("content", [])
                    if content_list and isinstance(content_list[0], dict):
                        inner = json.loads(content_list[0].get("text", "{}"))
                        items = inner.get("data", {}).get("memories", [])
                        for item in items:
                            c = item.get("content", "")
                            if c:
                                results.append(f"[{mem_type.upper()}] {c}")

        # Cleanup
        reader_task.cancel()
        try:
            await asyncio.shield(reader_task)
        except (asyncio.CancelledError, BaseException):
            pass
        await http.aclose()

        return results

    except Exception:
        return []


def _inject_into_memory(results: list[str]) -> None:
    """Replace the PERSONAL-AI section in MEMORY.md."""
    if results:
        lines = [SECTION_START, ""]
        for m in results:
            lines.append(f"- {m}")
        lines.append("")
        lines.append(SECTION_END)
        new_section = "\n".join(lines)
    else:
        new_section = f"{SECTION_START}\n\n(Sin memories activas.)\n\n{SECTION_END}\n"

    if MEMORY_FILE.exists():
        content = MEMORY_FILE.read_text(encoding="utf-8")
    else:
        content = ""

    if SECTION_START in content:
        pattern = re.compile(
            r"\n*<!-- PERSONAL-AI-INJECT-START -->.*?<!-- PERSONAL-AI-INJECT-END -->\n*",
            re.DOTALL,
        )
        content = pattern.sub("\n" + new_section.strip() + "\n", content)
    else:
        if content and not content.endswith("\n"):
            content += "\n"
        content += "\n" + new_section

    MEMORY_FILE.write_text(content, encoding="utf-8")
