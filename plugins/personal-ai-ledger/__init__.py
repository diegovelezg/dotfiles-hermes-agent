"""
PersonalAI Ledger Provider Plugin — exposes ledger, briefing & browser activity
tools from Diego's personal-ai MCP v5 server.

Tools exposed:
  - ledger_query          : search ledger items (hybrid lexical + graph)
  - ledger_item_create    : create a ledger item (action or intel)
  - ledger_bulk_action    : bulk update/archive items
  - briefing_generate     : generate structured executive briefing
  - browser_activity_add  : log browser activity (Chrome Extension)
  - browser_activity_query: query browser history (semantic search)

Shares the MCP server connection with the personal-ai-memory plugin (SSOT).

Config (env vars):
  PERSONAL_AI_BASE_URL    : MCP server base URL
  PERSONAL_AI_API_KEY     : API key
  PERSONAL_AI_REMOTE_URL  : SSE endpoint
  PERSONAL_AI_USER_ID     : platform user ID (default: 1093162286)

Schema reference: schemas.py
Handler reference: tools.py
"""

from __future__ import annotations

import json
import logging
import os
import threading
from typing import Any

from .schemas import (
    BRIEFING_GENERATE_SCHEMA,
    BROWSER_ACTIVITY_ADD_SCHEMA,
    BROWSER_ACTIVITY_QUERY_SCHEMA,
    LEDGER_BULK_ACTION_SCHEMA,
    LEDGER_ITEM_CREATE_SCHEMA,
    LEDGER_QUERY_SCHEMA,
)
from .tools import (
    briefing_generate,
    browser_activity_add,
    browser_activity_query,
    ledger_bulk_action,
    ledger_item_create,
    ledger_query,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# PersonalAIClient — SSE+MCP bridge (shared with personal-ai-memory plugin)
# ---------------------------------------------------------------------------

class PersonalAIClient:
    """
    SSE+MCP bridge client using the official MCP Python SDK.
    Shares same server config as the memory plugin (SSOT).
    """

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        remote_url: str | None = None,
        user_id: str | None = None,
    ):
        _cfg_base_url: str | None = None
        _cfg_api_key: str | None = None
        _cfg_remote_url: str | None = None
        try:
            from hermes_cli.config import load_config

            mcp_cfg = load_config().get("mcp_servers", {}).get("personal-ai", {})
            env_cfg = mcp_cfg.get("env", {})
            _cfg_base_url = env_cfg.get("PERSONAL_AI_BASE_URL")
            _cfg_api_key = env_cfg.get("PERSONAL_AI_API_KEY")
            _cfg_remote_url = env_cfg.get("PERSONAL_AI_REMOTE_URL")
        except Exception:
            pass

        self.base_url: str = (
            base_url
            or _cfg_base_url
            or os.environ.get("PERSONAL_AI_BASE_URL")
            or "https://uaimcp.papelitosdecolor.com"
        )
        self.api_key: str = (
            api_key
            or _cfg_api_key
            or os.environ.get("PERSONAL_AI_API_KEY")
            or ""
        )
        self.remote_url: str = (
            remote_url
            or _cfg_remote_url
            or os.environ.get("PERSONAL_AI_REMOTE_URL")
            or f"{self.base_url}/sse"
        )
        self.user_id: str = user_id or os.environ.get("PERSONAL_AI_USER_ID", "1093162286")

        self._lock = threading.Lock()
        self._closed = False

    def is_available(self) -> bool:
        return bool(self.base_url and self.api_key)

    def connect(self) -> None:
        with self._lock:
            self._closed = False

    def _call_tool_sync(
        self, tool_name: str, arguments: dict, timeout: float = 15.0
    ) -> dict | None:
        import asyncio
        import httpx

        from mcp.client.sse import sse_client
        from mcp import ClientSession

        result_container: list[dict | None] = [None]
        error_container: list[Exception | None] = [None]

        async def _call() -> None:
            try:

                def http_factory(**kw: Any) -> httpx.AsyncClient:
                    kw.pop("timeout", None)
                    return httpx.AsyncClient(verify=False, timeout=timeout, **kw)

                async with sse_client(
                    self.remote_url,
                    httpx_client_factory=http_factory,
                    headers={"x-api-key": self.api_key},
                ) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        result = await session.call_tool(tool_name, arguments)
                        if result and hasattr(result, "content") and result.content:
                            text = (
                                result.content[0].text
                                if hasattr(result.content[0], "text")
                                else str(result.content[0])
                            )
                            data = json.loads(text)
                            result_container[0] = data
                        else:
                            result_container[0] = {"status": "success", "data": None}
            except Exception as e:
                error_container[0] = e
                logger.error(
                    "[personal-ai-ledger] call_tool %s error: %s", tool_name, e
                )

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        timeout_thread = threading.Thread(
            target=lambda: loop.run_until_complete(_call()), daemon=True
        )
        timeout_thread.start()
        timeout_thread.join(timeout=timeout)

        if error_container[0]:
            raise error_container[0]
        return result_container[0]

    def call_tool(
        self, tool_name: str, arguments: dict, timeout: float = 20.0
    ) -> dict | None:
        return self._call_tool_sync(tool_name, arguments, timeout)

    def close(self) -> None:
        with self._lock:
            self._closed = True


# ---------------------------------------------------------------------------
# Plugin entry point
# ---------------------------------------------------------------------------

def register(ctx) -> None:
    """Wire ledger tools to the Hermes plugin context."""
    ctx.register_tool(
        name="ledger_query",
        toolset="personal-ai-ledger",
        schema=LEDGER_QUERY_SCHEMA,
        handler=ledger_query,
        description="Search ledger items using hybrid (Lexical + Graph) search. "
        "Returns items with relevance scores.",
    )
    ctx.register_tool(
        name="ledger_item_create",
        toolset="personal-ai-ledger",
        schema=LEDGER_ITEM_CREATE_SCHEMA,
        handler=ledger_item_create,
        description="Create a ledger item (action or intel). "
        "Intel items must have status='permanent'.",
    )
    ctx.register_tool(
        name="ledger_bulk_action",
        toolset="personal-ai-ledger",
        schema=LEDGER_BULK_ACTION_SCHEMA,
        handler=ledger_bulk_action,
        description="Bulk update/archive ledger items. "
        "'ids' and 'note' (reason) are required.",
    )
    ctx.register_tool(
        name="briefing_generate",
        toolset="personal-ai-ledger",
        schema=BRIEFING_GENERATE_SCHEMA,
        handler=briefing_generate,
        description="Generate an executive briefing from ledger items. "
        "Persists a readable summary + semantic rational.",
    )
    ctx.register_tool(
        name="browser_activity_add",
        toolset="personal-ai-ledger",
        schema=BROWSER_ACTIVITY_ADD_SCHEMA,
        handler=browser_activity_add,
        description="Log a browser activity with semantic summary. "
        "Used by Chrome Extension. Auto-deletes after 30 days.",
    )
    ctx.register_tool(
        name="browser_activity_query",
        toolset="personal-ai-ledger",
        schema=BROWSER_ACTIVITY_QUERY_SCHEMA,
        handler=browser_activity_query,
        description="Search browser activity history using semantic embeddings.",
    )
