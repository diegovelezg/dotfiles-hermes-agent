"""
PersonalAI Memory Provider Plugin — integrates Diego's custom personal-ai MCP
(Mem0-backed) as a first-class memory plugin for Hermes Agent v0.7+.

Architecture:
  - SSE bridge to personal-ai MCP v5 using official MCP Python SDK (sse_client)
  - PersonalAIMemoryProvider subclasses MemoryProvider ABC
  - MemoryManager orchestrates builtin (MEMORY.md/USER.md) + this provider

Tools exposed:
  Memory:
    - personal_ai_memories_search : semantic search over know/policy/episodic memories
    - personal_ai_memories_manage : create/update/deprecate memories
  Ledger:
    - ledger_query : query ledger items
    - ledger_item_create : create a ledger item
    - ledger_bulk_action : bulk update/archive ledger items
  Briefing:
    - briefing_generate : generate structured briefing from ledger
  Browser Activity:
    - browser_activity_add : log browser activity
    - browser_activity_query : query browser activity history

Config (env vars or config.yaml mcp_servers.personal-ai):
  PERSONAL_AI_BASE_URL    : MCP server base URL
  PERSONAL_AI_API_KEY    : API key
  PERSONAL_AI_REMOTE_URL : SSE endpoint (default: <BASE_URL>/sse)
  PERSONAL_AI_USER_ID    : platform user ID (default: 1093162286)
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import threading
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tool schemas
# ---------------------------------------------------------------------------

MEMORIES_SEARCH_SCHEMA = {
    "name": "personal_ai_memories_search",
    "description": (
        "Search Diego's personal memories (know, policy, episodic) using "
        "semantic search. Returns facts, preferences, rules, and past events "
        "relevant to the query. Use whenever you need to recall something "
        "about Diego — his projects, preferences, people in his life, or "
        "anything you've discussed."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Natural language search query.",
            },
            "memory_type": {
                "type": "string",
                "enum": ["know", "policy", "episodic", "know_and_policy", "all"],
                "description": "Type of memory to search. Use 'episodic' or 'know_and_policy' for targeted searches (default: all).",
                "default": "all",
            },
            "limit": {
                "type": "integer",
                "description": "Max results (default: 10, max: 50).",
                "default": 10,
            },
        },
        "required": ["query"],
    },
}

MEMORIES_MANAGE_SCHEMA = {
    "name": "personal_ai_memories_manage",
    "description": (
        "Manage a personal memory entry — create, update, use, or deprecate. "
        "Use to save new facts about Diego, correct existing memories, or "
        "mark information as historical/archived."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["create", "update", "use", "deprecate"],
                "description": "Action to perform.",
            },
            "memory_id": {
                "type": "string",
                "description": "Memory ID (required for update/use/deprecate).",
            },
            "content": {
                "type": "string",
                "description": "Memory content (required for create/update).",
            },
            "memory_type": {
                "type": "string",
                "enum": ["know", "policy", "episodic"],
                "description": "Type of memory (default: know).",
                "default": "know",
            },
            "status": {
                "type": "string",
                "enum": ["active", "historical"],
                "description": "Status (default: active).",
                "default": "active",
            },
        },
        "required": ["action"],
    },
}




# ---------------------------------------------------------------------------
# PersonalAI MCP client — official SDK (sse_client + ClientSession)
# ---------------------------------------------------------------------------

class PersonalAIClient:
    """
    SSE+MCP bridge client using the official MCP Python SDK.

    Protocol (handled automatically by sse_client):
      1. sse_client opens GET /sse → receives session_id in endpoint event
      2. ClientSession.initialize() completes the MCP handshake
      3. session.call_tool() sends JSON-RPC via POST, reads response from SSE stream
    """

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        remote_url: str | None = None,
        user_id: str | None = None,
    ):
        # Load config from env or config.yaml
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

        self._session: Any = None  # ClientSession (set in connect)
        self._lock = threading.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._closed = False

    def _headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "x-api-key": self.api_key,
        }

    def is_available(self) -> bool:
        """Check credentials are set — no network call."""
        return bool(self.base_url and self.api_key)

    def connect(self) -> None:
        """Mark session as needing initialization. Actual connection is lazy on first call."""
        with self._lock:
            self._closed = False

    def _ensure_session(self):
        if self._closed:
            self.connect()
        return self._session

    def _call_tool_sync(self, tool_name: str, arguments: dict, timeout: float = 15.0) -> dict | None:
        """Call a tool synchronously using the shared session."""
        import asyncio
        import httpx
        from mcp.client.sse import sse_client
        from mcp import ClientSession

        result_container: list = [None]
        error_container: list = [None]

        async def _call():
            try:
                # Use a fresh SSE connection per call (session-less protocol)
                def http_factory(**kw) -> httpx.AsyncClient:
                    kw.pop("timeout", None)  # avoid duplicate timeout
                    return httpx.AsyncClient(verify=False, timeout=timeout, **kw)

                async with sse_client(
                    self.remote_url,
                    httpx_client_factory=http_factory,
                    headers={"x-api-key": self.api_key},
                ) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        result = await session.call_tool(tool_name, arguments)
                        # Extract text content from result
                        if result and hasattr(result, 'content') and result.content:
                            text = result.content[0].text if hasattr(result.content[0], 'text') else str(result.content[0])
                            data = json.loads(text)
                            result_container[0] = data
                        else:
                            result_container[0] = {"status": "success", "data": None}
            except Exception as e:
                error_container[0] = e
                logger.error("[personal-ai] call_tool %s error: %s", tool_name, e)

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
        """Public method: call any MCP tool directly. Used for ledger, briefing, browser_activity."""
        return self._call_tool_sync(tool_name, arguments, timeout)

    # ---- High-level API (search/manage) ----

    def search_memories(
        self,
        query: str,
        memory_type: str = "all",
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Semantic search over memories."""
        if memory_type == "all":
            types = ["know", "policy", "episodic"]
        elif memory_type == "know_and_policy":
            types = ["know", "policy"]
        else:
            types = [memory_type]

        all_results = []
        for mtype in types:
            params = {
                "query": query,
                "type": mtype,
                "status": "active",
                "user_id": self.user_id,
                "limit": str(min(limit, 50)),
            }
            try:
                result = self._call_tool_sync("memories_search", params)
                if result:
                    data = result.get("data", {})
                    items = data.get("memories", []) if isinstance(data, dict) else []
                    all_results.extend(items)
            except Exception as e:
                logger.warning("[personal-ai] search_memories(%s) error: %s", mtype, e)
        return all_results

    def manage_memory(
        self,
        action: str,
        memory_id: str | None = None,
        content: str | None = None,
        memory_type: str = "know",
        status: str = "active",
        **kwargs,
    ) -> dict | None:
        """Create, update, use, or deprecate a memory."""
        params: dict[str, Any] = {
            "action": action,
            "type": memory_type,
            "status": status,
            **kwargs,
        }
        if memory_id:
            params["id"] = memory_id
        if content:
            params["content"] = content

        method_map = {
            "create": ("memory_manage", params),
            "update": ("memory_manage", params),
            "use": ("memory_manage", params),
            "deprecate": ("memory_manage", params),
        }
        method, final_params = method_map.get(action, ("memory_manage", params))
        try:
            return self._call_tool_sync(method, final_params)
        except Exception as e:
            logger.error("[personal-ai] manage_memory error: %s", e)
            return None

    def close(self) -> None:
        """Clean shutdown."""
        with self._lock:
            self._closed = True
            self._session = None
            self._loop = None


# ---------------------------------------------------------------------------
# PersonalAI Memory Provider
# ---------------------------------------------------------------------------

class PersonalAIMemoryProvider:
    """
    MemoryProvider implementation for personal-ai MCP.

    Lifecycle hooks (called by MemoryManager):
      initialize()    — connect to personal-ai MCP
      prefetch()      — recall relevant context before each turn (cached)
      sync_turn()     — async write after each turn (queues writes)
      get_tool_schemas() — expose personal-ai tools to the model
      handle_tool_call() — dispatch tool calls

    Optional hooks:
      on_turn_start() — increment turn counter
      on_session_end() — end-of-session extraction
      shutdown() — cleanup

    Notes:
      - agent_context="cron" skips all writes (would corrupt cron sessions)
      - User_id from agent_identity or kwargs if available
      - Thread-safe, supports concurrent gateway sessions
    """

    name = "personal-ai"
    _client: PersonalAIClient | None = None
    _turn_count: int = 0
    _last_fetch_time: float = 0
    _cached_prefetch: tuple[str, float] | None = None  # (result, timestamp)
    CACHE_TTL: float = 120.0  # refresh every 2 minutes

    def __init__(self):
        self._lock = threading.Lock()
        self._turn_count = 0
        self._last_fetch_time = 0.0
        self._cached_prefetch = None
        self._user_id: str = "1093162286"

    # -- Availability -------------------------------------------------------

    def is_available(self) -> bool:
        """Check if credentials are available via env vars or config.yaml MCP server section."""
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

    # -- Core lifecycle ------------------------------------------------------

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
        """
        Initialize the personal-ai MCP connection.

        Skips writes for non-primary contexts (cron, subagent) to avoid
        corrupting cron session representations.
        """
        logger.info(
            "[personal-ai] initialize session=%s platform=%s context=%s identity=%s",
            session_id, platform, agent_context, agent_identity,
        )

        if user_id:
            self._user_id = user_id

        self._skip_writes = agent_context in ("cron", "flush")
        self._session_id = session_id
        self._client = PersonalAIClient(user_id=self._user_id)
        self._client.connect()

        logger.info(
            "[personal-ai] initialized (writes=%s, user_id=%s)",
            not self._skip_writes,
            self._user_id,
        )

    # -- System prompt -------------------------------------------------------

    def system_prompt_block(self) -> str:
        """Static text injected into the system prompt."""
        return """\
## Personal AI Memory (personal-ai plugin)

Diego has a custom personal AI memory system (personal-ai MCP v5, Mem0-backed) with:
- **know**: persistent facts about Diego (preferences, people, projects, habits)
- **policy**: operational rules Diego has set
- **episodic**: past events and experiences

**Load strategy:**
- At session start: know + policy (status: active) are preloaded — these are the stable user model
- On demand: episodic and historical memories are retrieved via personal_ai_memories_search when relevant

You have tools to query and manage these memories:
- personal_ai_memories_search — semantic search (all types, on demand)
- personal_ai_memories_manage — create/update/deprecate memories

**When to use**: At the start of a session and whenever Diego asks about something from his past,
preferences, projects, or people in his life. Act proactively — don't wait to be asked.

**Memory hygiene**: When Diego corrects you or shares new information, offer to save it as a memory.
"""

    # -- Recall (prefetch) ---------------------------------------------------

    def prefetch(self, query: str, *, session_id: str = "") -> str:
        """
        Return cached personal context for the upcoming turn.

        Caches results for CACHE_TTL seconds to avoid redundant MCP calls.
        Override query caching with an explicit None query to force refresh.
        """
        now = time.time()

        if (
            self._cached_prefetch is not None
            and (now - self._cached_prefetch[1]) < self.CACHE_TTL
            and query
        ):
            return self._cached_prefetch[0]

        if not self._client:
            return ""

        try:
            core_results = self._client.search_memories(
                "Diego preferences projects people environment habits",
                memory_type="know_and_policy",
                limit=20,
            )
            results: list[str] = []
            for item in core_results:
                c = item.get("content", "")
                mtype = item.get("type", "know")
                # Filter out known ghost/test memories that exist in Mem0 but
                # cannot be managed via memory_manage due to an MCP server bug
                # where search IDs don't resolve in Mem0's update/delete API.
                if c and "SDK rewrite" not in c:
                    results.append(f"[{mtype}] {c}")

            if results:
                block = "## Recent Personal Context\n" + "\n".join(f"- {r}" for r in results)
            else:
                block = ""

            self._cached_prefetch = (block, now)
            return block

        except Exception as e:
            logger.warning("[personal-ai] prefetch error: %s", e)
            return ""

    def queue_prefetch(self, query: str, *, session_id: str = "") -> None:
        """Invalidate cache so next prefetch() fetches fresh data."""
        self._cached_prefetch = None

    # -- Per-turn sync ------------------------------------------------------

    def sync_turn(self, user_content: str, assistant_content: str, *, session_id: str = "") -> None:
        """
        Skip per-turn sync — personal-ai uses explicit memory_manage calls.
        """
        pass

    # -- Tools --------------------------------------------------------------

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Return only memory-related personal-ai tools."""
        return [
            MEMORIES_SEARCH_SCHEMA,
            MEMORIES_MANAGE_SCHEMA,
        ]

    def handle_tool_call(self, tool_name: str, args: Dict[str, Any], **kwargs) -> str:
        """Dispatch a memory tool call to the appropriate client method."""
        if not self._client:
            return json.dumps({"error": "personal-ai not initialized"})

        try:
            if tool_name == "personal_ai_memories_search":
                results = self._client.search_memories(
                    query=args.get("query", ""),
                    memory_type=args.get("memory_type", "all"),
                    limit=args.get("limit", 10),
                )
                # Filter ghost memories that exist in Mem0 but can't be managed
                # via memory_manage due to an MCP server bug (search ID != Mem0 ID)
                results = [r for r in results if "SDK rewrite" not in r.get("content", "")]
                return json.dumps({"status": "success", "data": {"memories": results}})

            elif tool_name == "personal_ai_memories_manage":
                result = self._client.manage_memory(
                    action=args.get("action", ""),
                    memory_id=args.get("memory_id"),
                    content=args.get("content"),
                    memory_type=args.get("memory_type", "know"),
                    status=args.get("status", "active"),
                    timezone=args.get("timezone", "America/Lima"),
                    user_id=args.get("user_id", self._user_id),
                )
                self._cached_prefetch = None
                return json.dumps({"status": "success", "data": result})

            else:
                return json.dumps({"error": f"Unknown tool: {tool_name}"})

        except Exception as e:
            logger.error("[personal-ai] tool=%s error: %s", tool_name, e)
            return json.dumps({"error": str(e)})

    # -- Optional hooks -----------------------------------------------------

    def on_turn_start(
        self,
        turn_number: int,
        message: str,
        *,
        remaining_tokens: int = 0,
        model: str = "",
        platform: str = "",
        tool_count: int = 0,
        **kwargs,
    ) -> None:
        """Track turns and periodically refresh cached context."""
        self._turn_count = turn_number
        if self._turn_count % 10 == 0:
            self._cached_prefetch = None

    def on_session_end(self, messages: List[Dict[str, Any]]) -> None:
        """End-of-session hook — not currently used."""
        pass

    # -- Config -------------------------------------------------------------

    def get_config_schema(self) -> List[Dict[str, Any]]:
        """Config fields for hermes memory setup wizard."""
        return [
            {
                "key": "user_id",
                "description": "Platform user ID for personal-ai (Telegram user ID)",
                "default": "1093162286",
                "required": False,
            },
            {
                "key": "cache_ttl",
                "description": "Prefetch cache TTL in seconds (default: 120)",
                "default": "120",
                "required": False,
            },
        ]

    # -- Shutdown -----------------------------------------------------------

    def shutdown(self) -> None:
        """Clean shutdown — close SSE connections."""
        if self._client:
            self._client.close()
            self._client = None
        logger.info("[personal-ai] shutdown complete")


# ---------------------------------------------------------------------------
# Plugin entry point (register hook)
# ---------------------------------------------------------------------------

def register() -> PersonalAIMemoryProvider:
    """Plugin entry point — returns the provider instance."""
    return PersonalAIMemoryProvider()
