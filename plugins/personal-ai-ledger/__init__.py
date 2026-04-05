"""
PersonalAI Ledger Provider Plugin — exposes ledger, briefing & browser activity
tools from Diego's personal-ai MCP v5 server.

Tools exposed (all except memory):
  - ledger_query          : search ledger items
  - ledger_item_create    : create a ledger item
  - ledger_bulk_action    : bulk update/archive items
  - briefing_generate     : generate structured briefing
  - browser_activity_add  : log browser activity
  - browser_activity_query: query browser history

Shares the MCP server connection with the personal-ai-memory plugin (SSOT).

Config (env vars):
  PERSONAL_AI_BASE_URL    : MCP server base URL
  PERSONAL_AI_API_KEY     : API key
  PERSONAL_AI_REMOTE_URL  : SSE endpoint
  PERSONAL_AI_USER_ID     : platform user ID (default: 1093162286)
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tool schemas (non-memory)
# ---------------------------------------------------------------------------

LEDGER_QUERY_SCHEMA = {
    "name": "ledger_query",
    "description": "Query ledger items from personal-ai. Returns matching items with relevance scores.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Natural language query."},
            "limit": {"type": "integer", "default": 10, "description": "Max results (default: 10)."},
            "status": {"type": "string", "description": "Filter by status (e.g. 'permanent', 'active')."},
            "nature": {"type": "string", "description": "Filter by nature (e.g. 'intel', 'project', 'person')."},
        },
        "required": ["query"],
    },
}

LEDGER_ITEM_CREATE_SCHEMA = {
    "name": "ledger_item_create",
    "description": "Create a ledger item in personal-ai (note, task, project, person, intel, etc).",
    "parameters": {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Item title."},
            "content": {"type": "string", "description": "Optional detailed content/description."},
            "nature": {"type": "string", "enum": ["action", "intel"], "default": "action", "description": "Type: 'action' (tasks/projects) or 'intel' (notes/info). Intel must have status='permanent'."},
            "status": {"type": "string", "description": "Status: permanent (intel), active (action). Intel nature requires permanent."},
            "subject": {"type": "string", "description": "Subject/tag (e.g. @proyecto, @persona)."},
            "priority": {"type": "string", "description": "Priority: low, medium, high, urgent."},
            "due_at": {"type": "string", "description": "Due date (ISO format)."},
        },
        "required": ["title", "nature"],
    },
}

LEDGER_BULK_ACTION_SCHEMA = {
    "name": "ledger_bulk_action",
    "description": "Bulk update or archive multiple ledger items by ID. IDs come from ledger_query results.",
    "parameters": {
        "type": "object",
        "properties": {
            "ids": {"type": "array", "items": {"type": "string"}, "description": "List of ledger item IDs (from ledger_query)."},
            "note": {"type": "string", "description": "Note/reason for the action."},
            "status": {"type": "string", "description": "New status: active, archived, etc."},
            "priority": {"type": "string", "description": "New priority to set."},
        },
        "required": ["ids", "note"],
    },
}

BRIEFING_GENERATE_SCHEMA = {
    "name": "briefing_generate",
    "description": "Generate a structured briefing from ledger items matching a query.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Query to select relevant ledger items."},
            "format": {"type": "string", "default": "text", "description": "Format: text, markdown, html."},
            "max_items": {"type": "integer", "default": 20, "description": "Max ledger items to include."},
        },
        "required": ["query"],
    },
}

BROWSER_ACTIVITY_ADD_SCHEMA = {
    "name": "browser_activity_add",
    "description": "Log a browser activity (URL, title, action) to personal-ai.",
    "parameters": {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "URL of the page."},
            "title": {"type": "string", "description": "Page title."},
            "summary": {"type": "string", "description": "Brief summary of the activity (required for vectorization)."},
            "action": {"type": "string", "default": "visit", "description": "Action: visit, search, click, submit, scroll."},
            "site": {"type": "string", "description": "Site/domain name."},
        },
        "required": ["url", "summary"],
    },
}

BROWSER_ACTIVITY_QUERY_SCHEMA = {
    "name": "browser_activity_query",
    "description": "Query browser activity history from personal-ai.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query."},
            "site": {"type": "string", "description": "Filter by site/domain."},
            "limit": {"type": "integer", "default": 10, "description": "Max results."},
            "match_threshold": {"type": "number", "default": 0.5, "description": "Relevance threshold (0-1)."},
        },
        "required": ["query"],
    },
}


# ---------------------------------------------------------------------------
# PersonalAIClient (same implementation as memory plugin — connects to same MCP server)
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

    def _call_tool_sync(self, tool_name: str, arguments: dict, timeout: float = 15.0) -> dict | None:
        import asyncio
        import httpx
        from mcp.client.sse import sse_client
        from mcp import ClientSession

        result_container: list = [None]
        error_container: list = [None]

        async def _call():
            try:
                def http_factory(**kw) -> httpx.AsyncClient:
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
                        if result and hasattr(result, 'content') and result.content:
                            text = result.content[0].text if hasattr(result.content[0], 'text') else str(result.content[0])
                            data = json.loads(text)
                            result_container[0] = data
                        else:
                            result_container[0] = {"status": "success", "data": None}
            except Exception as e:
                error_container[0] = e
                logger.error("[personal-ai-ledger] call_tool %s error: %s", tool_name, e)

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        timeout_thread = threading.Thread(target=lambda: loop.run_until_complete(_call()), daemon=True)
        timeout_thread.start()
        timeout_thread.join(timeout=timeout)

        if error_container[0]:
            raise error_container[0]
        return result_container[0]

    def call_tool(self, tool_name: str, arguments: dict, timeout: float = 20.0) -> dict | None:
        return self._call_tool_sync(tool_name, arguments, timeout)

    def close(self) -> None:
        with self._lock:
            self._closed = True


# ---------------------------------------------------------------------------
# PersonalAI Ledger Provider
# ---------------------------------------------------------------------------

LEDGER_TOOLS = [
    LEDGER_QUERY_SCHEMA,
    LEDGER_ITEM_CREATE_SCHEMA,
    LEDGER_BULK_ACTION_SCHEMA,
    BRIEFING_GENERATE_SCHEMA,
    BROWSER_ACTIVITY_ADD_SCHEMA,
    BROWSER_ACTIVITY_QUERY_SCHEMA,
]


class PersonalAILedgerProvider:
    """
    Provider for ledger, briefing & browser activity tools from personal-ai MCP.

    Lifecycle hooks (called by Hermes Agent):
      initialize()         — connect to personal-ai MCP
      get_tool_schemas()   — expose ledger tools to the model
      handle_tool_call()   — dispatch tool calls
      shutdown()            — cleanup

    Shares the same MCP server as personal-ai-memory (SSOT).
    """

    name = "personal-ai-ledger"

    def __init__(self):
        self._client: PersonalAIClient | None = None
        self._user_id: str = "1093162286"

    def is_available(self) -> bool:
        if os.environ.get("PERSONAL_AI_API_KEY") and os.environ.get("PERSONAL_AI_BASE_URL"):
            return True
        try:
            from hermes_cli.config import load_config
            config = load_config()
            mcp_cfg = config.get("mcp_servers", {}).get("personal-ai", {})
            env_cfg = mcp_cfg.get("env", {})
            if env_cfg.get("PERSONAL_AI_API_KEY") and env_cfg.get("PERSONAL_AI_BASE_URL"):
                return True
        except Exception:
            pass
        return False

    def initialize(
        self,
        session_id: str,
        *,
        hermes_home: str = "",
        platform: str = "",
        agent_context: str = "primary",
        agent_identity: str = "",
        agent_workspace: str = "",
        parent_session_id: str = "",
        user_id: str = "",
        **kwargs,
    ) -> None:
        logger.info(
            "[personal-ai-ledger] initialize session=%s platform=%s context=%s",
            session_id, platform, agent_context,
        )
        if user_id:
            self._user_id = user_id
        self._client = PersonalAIClient(user_id=self._user_id)
        self._client.connect()
        logger.info("[personal-ai-ledger] initialized (user_id=%s)", self._user_id)

    def system_prompt_block(self) -> str:
        return """\
## Personal AI Ledger (personal-ai-ledger plugin)

Diego has a personal-ai MCP server with ledger, briefing and browser activity tools:

**Ledger tools:**
- ledger_query — search ledger items (actions, intel, projects, people)
- ledger_item_create — create a new ledger item
- ledger_bulk_action — bulk update/archive items by ID

**Briefing:**
- briefing_generate — generate a structured briefing from ledger items

**Browser Activity:**
- browser_activity_add — log a browser activity
- browser_activity_query — query browser history

Use these tools when Diego asks about his tasks, projects, intel, daily briefings,
or browsing activity. The ledger is his second brain for actionable items and notes.
"""

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        return LEDGER_TOOLS

    def handle_tool_call(self, tool_name: str, args: Dict[str, Any], **kwargs) -> str:
        if not self._client:
            return json.dumps({"error": "personal-ai-ledger not initialized"})

        try:
            if tool_name in (
                "ledger_query", "ledger_item_create", "ledger_bulk_action",
                "briefing_generate", "browser_activity_add", "browser_activity_query",
            ):
                result = self._client.call_tool(tool_name, args)
                return json.dumps({"status": "success", "data": result})
            else:
                return json.dumps({"error": f"Unknown tool: {tool_name}"})

        except Exception as e:
            logger.error("[personal-ai-ledger] tool=%s error: %s", tool_name, e)
            return json.dumps({"error": str(e)})

    def get_config_schema(self) -> List[Dict[str, Any]]:
        return [
            {
                "key": "user_id",
                "description": "Platform user ID for personal-ai (Telegram user ID)",
                "default": "1093162286",
                "required": False,
            },
        ]

    def shutdown(self) -> None:
        if self._client:
            self._client.close()
            self._client = None
        logger.info("[personal-ai-ledger] shutdown complete")


# ---------------------------------------------------------------------------
# Plugin entry point
# ---------------------------------------------------------------------------

def register() -> PersonalAILedgerProvider:
    return PersonalAILedgerProvider()
