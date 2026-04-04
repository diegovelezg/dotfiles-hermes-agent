"""
Personal AI MCP Client — calls the personal-ai UIA MCP bridge via SSE+POST.

Shares the same SSE session protocol as personal-ai-memory-loader:
  1. GET /sse → receives session_id in SSE data (keeps connection open)
  2. POST /messages?sessionId=... → sends JSON-RPC on same keep-alive connection
  3. Response arrives as SSE data events on the open GET connection
"""

import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger("gateway.builtin_hooks.personal_ai_client")

REMOTE_URL = os.environ.get(
    "PERSONAL_AI_REMOTE_URL", "https://uaimcp.papelitosdecolor.com/sse"
)
BASE_URL = os.environ.get(
    "PERSONAL_AI_BASE_URL", "https://uaimcp.papelitosdecolor.com"
)
API_KEY = os.environ.get(
    "PERSONAL_AI_API_KEY", ""
)


def _headers() -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "x-api-key": API_KEY,
    }


async def async_fetch_know_memories(
    query: str = "",
    limit: int = 10,
    user_id: str = "1093162286",
) -> List[Dict[str, Any]]:
    """
    Fetch active 'know' memories from personal-ai via SSE MCP protocol.

    Returns a list of memory dicts with at least 'content' and 'type' keys.
    """
    return await _fetch_memories(
        mem_types=("know",),
        query=query,
        limit=limit,
        user_id=user_id,
    )


async def async_fetch_all_memories(
    query: str = "",
    limit: int = 20,
    user_id: str = "1093162286",
) -> List[Dict[str, Any]]:
    """
    Fetch all active memories (know + policy) from personal-ai.
    """
    return await _fetch_memories(
        mem_types=("know", "policy"),
        query=query,
        limit=limit,
        user_id=user_id,
    )


async def _fetch_memories(
    mem_types: tuple[str, ...],
    query: str,
    limit: int,
    user_id: str,
) -> List[Dict[str, Any]]:
    """Internal SSE fetch implementation shared by all public functions."""
    session_id: Optional[str] = None
    messages_queue: List[Dict[str, Any]] = []

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
        except Exception as e:
            logger.debug(f"SSE reader error: {e}")

    try:
        http = httpx.AsyncClient(verify=False, timeout=60.0)

        reader_task = asyncio.create_task(sse_reader(http))

        # Wait for session_id
        for _ in range(200):
            if session_id:
                break
            await asyncio.sleep(0.1)
        else:
            raise RuntimeError("Timeout waiting for sessionId from SSE")

        if not session_id:
            return []

        msg_url = f"{BASE_URL}/messages?sessionId={session_id}"
        all_results: List[Dict[str, Any]] = []

        for mem_type in mem_types:
            messages_queue.clear()

            search_query = query if query else f"memories {mem_type} {user_id}"
            payload = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "memories_search",
                    "arguments": {
                        "type": mem_type,
                        "status": "active",
                        "user_id": user_id,
                        "limit": limit,
                        "query": search_query,
                    },
                },
                "id": f"client-{mem_type}",
            }

            post_resp = await http.post(
                msg_url,
                json=payload,
                headers=_headers(),
            )
            post_resp.raise_for_status()

            # Wait for response in SSE queue
            for _ in range(100):
                if any("result" in m or "error" in m for m in messages_queue):
                    break
                await asyncio.sleep(0.1)

            for msg in messages_queue:
                if "result" in msg:
                    content_list = msg["result"].get("content", [])
                    if content_list and isinstance(content_list[0], dict):
                        try:
                            inner = json.loads(content_list[0].get("text", "{}"))
                            items = inner.get("data", {}).get("memories", [])
                            for item in items:
                                c = item.get("content", "")
                                m_type = item.get("type", mem_type)
                                if c:
                                    all_results.append({
                                        "content": c,
                                        "type": m_type,
                                    })
                        except (json.JSONDecodeError, KeyError, IndexError):
                            pass

        # Cleanup
        reader_task.cancel()
        try:
            await asyncio.shield(reader_task)
        except (asyncio.CancelledError, BaseException):
            pass
        await http.aclose()

        return all_results

    except Exception as e:
        logger.error(f"Failed to fetch memories from personal-ai: {e}")
        return []
