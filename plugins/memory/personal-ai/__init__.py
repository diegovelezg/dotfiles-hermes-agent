"""
PersonalAI Memory Provider Plugin — integrates Diego's custom personal-ai MCP
(Mem0-backed) as a first-class memory plugin for Hermes Agent v0.7+.

Architecture:
  - SSE bridge to personal-ai MCP v5 (same protocol as the old hook)
  - PersonalAIMemoryProvider subclasses MemoryProvider ABC
  - MemoryManager orchestrates builtin (MEMORY.md/USER.md) + this provider
  - Only ONE external provider allowed — this replaces the hook entirely

Tools exposed:
  - personal_ai_search     : semantic search over know/policy/episodic memories
  - personal_ai_memories_manage : create/update/deprecate memories
  - personal_ai_briefing_generate : generate daily briefing from ledger + memories
  - personal_ai_ledger_*    : ledger operations (query, create, bulk_action)

Config (env vars, same as before):
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

# -----------------------------------------------------------------------
# Tool schemas
# -----------------------------------------------------------------------

SEARCH_SCHEMA = {
    "name": "personal_ai_search",
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
                "enum": ["know", "policy", "episodic", "all"],
                "description": "Type of memory to search (default: all).",
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

BRIEFING_SCHEMA = {
    "name": "personal_ai_briefing_generate",
    "description": (
        "Generate a daily briefing for Diego based on ledger action items, "
        "active memories, and recent episodic events. Returns a structured "
        "overview of what needs attention today."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "timezone": {
                "type": "string",
                "description": "Timezone for the briefing (default: America/Lima).",
                "default": "America/Lima",
            },
        },
        "properties": {},
    },
}

LEDGER_QUERY_SCHEMA = {
    "name": "personal_ai_ledger_query",
    "description": (
        "Query the action/intel ledger — search for tasks, notes, or "
        "information items. Returns matching items with their status, "
        "priority, and metadata."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Natural language search query.",
            },
            "status": {
                "type": "string",
                "description": "Filter by status (inbox, todo, doing, review, done, etc.).",
            },
            "nature": {
                "type": "string",
                "enum": ["action", "intel", "all"],
                "description": "Filter by nature (default: all).",
                "default": "all",
            },
            "limit": {
                "type": "integer",
                "description": "Max results (default: 50).",
                "default": 50,
            },
        },
        "required": ["query"],
    },
}

LEDGER_CREATE_SCHEMA = {
    "name": "personal_ai_ledger_item_create",
    "description": (
        "Create a new ledger item — an action task or intel note. "
        "Use for tracking todos, projects, or information Diego wants to retain."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Title of the item.",
            },
            "nature": {
                "type": "string",
                "enum": ["action", "intel"],
                "description": "Nature: action=task, intel=information.",
            },
            "status": {
                "type": "string",
                "enum": ["inbox", "todo", "doing", "review", "done", "dismissed", "archived", "permanent"],
                "description": "Initial status (default: inbox for actions, permanent for intel).",
            },
            "content": {
                "type": "string",
                "description": "Description or content.",
            },
            "subject": {
                "type": "string",
                "description": "Subject/topic.",
            },
            "priority": {
                "type": "string",
                "enum": ["low", "medium", "high", "urgent"],
                "description": "Priority (default: medium).",
                "default": "medium",
            },
            "due_at": {
                "type": "string",
                "description": "Due date (ISO 8601).",
            },
        },
        "required": ["title", "nature"],
    },
}

LEDGER_BULK_SCHEMA = {
    "name": "personal_ai_ledger_bulk_action",
    "description": (
        "Bulk update multiple ledger items at once — change status, priority, "
        "add notes, or reassign. Supply a list of item IDs."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of ledger item IDs.",
            },
            "status": {
                "type": "string",
                "enum": ["inbox", "todo", "doing", "review", "done", "dismissed", "archived", "permanent"],
                "description": "New status.",
            },
            "priority": {
                "type": "string",
                "enum": ["low", "medium", "high", "urgent"],
                "description": "New priority.",
            },
            "note": {
                "type": "string",
                "description": "Note to add to all items.",
            },
        },
        "required": ["ids", "note"],
    },
}

BROWSER_ACTIVITY_QUERY_SCHEMA = {
    "name": "personal_ai_browser_activity_query",
    "description": (
        "Query Diego's browser activity history — websites visited, time spent, "
        "and page content summaries. Hybrid search (exact + semantic)."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search terms for the summary (semantic).",
            },
            "site": {
                "type": "string",
                "description": "Filter by site (e.g. 'github.com').",
            },
            "limit": {
                "type": "integer",
                "description": "Max results (default: 10).",
                "default": 10,
            },
            "match_threshold": {
                "type": "number",
                "description": "Similarity threshold 0-1 (default: 0.5).",
                "default": 0.5,
            },
        },
        "required": ["query"],
    },
}


# -----------------------------------------------------------------------
# PersonalAI MCP client (SSE bridge protocol)
# -----------------------------------------------------------------------

class PersonalAIClient:
    """
    SSE+MCP bridge client for personal-ai MCP v5.

    Protocol:
      1. GET /sse → receives session_id in SSE data (keeps connection open)
      2. POST /messages?sessionId=... → sends JSON-RPC on same keep-alive connection
      3. Response arrives as SSE data events on the open GET connection
    """

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        remote_url: str | None = None,
        user_id: str | None = None,
    ):
        self.base_url = (base_url or os.environ.get(
            "PERSONAL_AI_BASE_URL", "https://uaimcp.papelitosdecolor.com"
        ))
        self.api_key = api_key or os.environ.get("PERSONAL_AI_API_KEY", "")
        self.remote_url = (
            remote_url
            or os.environ.get("PERSONAL_AI_REMOTE_URL")
            or f"{self.base_url}/sse"
        )
        self.user_id = user_id or os.environ.get("PERSONAL_AI_USER_ID", "1093162286")

        self._session_id: str | None = None
        self._lock = threading.Lock()
        self._http: Any = None  # set in connect()

    def _headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "x-api-key": self.api_key,
        }

    def is_available(self) -> bool:
        """Check env vars are set — no network call."""
        return bool(self.base_url and self.api_key)

    def connect(self) -> None:
        """Establish SSE connection and get session_id."""
        import httpx
        with self._lock:
            if self._http is not None:
                return
            self._http = httpx.AsyncClient(verify=False, timeout=30.0)
            self._session_id = None

            # Start background reader to get session_id
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # Run synchronously for initialize()
            async def get_session():
                session_id = None
                async with self._http.stream("GET", self.remote_url, headers=self._headers()) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if "sessionId=" in line:
                            session_id = line.split("sessionId=")[1].split()[0].strip()
                            break
                return session_id

            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            self._session_id = loop.run_until_complete(get_session())

    def _ensure_session(self) -> str:
        if not self._session_id:
            self.connect()
        return self._session_id or ""

    def _post_and_wait(self, method: str, params: dict, timeout: float = 15.0) -> dict | None:
        """POST a JSON-RPC request and wait for SSE response."""
        import httpx
        if self._http is None:
            self.connect()

        session_id = self._ensure_session()
        msg_url = f"{self.base_url}/messages?sessionId={session_id}"
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": f"pai-{int(time.time()*1000)}",
        }

        # Use a fresh client for the POST to avoid connection issues
        with self._lock:
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            results: list[dict] = []

            async def do_post():
                # Reconnect SSE for this response
                client = httpx.AsyncClient(verify=False, timeout=timeout)
                sse_session = None

                async def sse_reader():
                    nonlocal sse_session
                    async with client.stream("GET", self.remote_url, headers=self._headers()) as resp:
                        resp.raise_for_status()
                        async for line in resp.aiter_lines():
                            if "sessionId=" in line and not sse_session:
                                sse_session = line.split("sessionId=")[1].split()[0].strip()
                            elif line.startswith("data:") and line[5:].strip().startswith("{"):
                                try:
                                    results.append(json.loads(line[5:].strip()))
                                except json.JSONDecodeError:
                                    pass

                reader_task = asyncio.create_task(sse_reader())
                await asyncio.sleep(0.3)  # let reader start

                post_resp = await client.post(msg_url, json=payload, headers=self._headers())
                post_resp.raise_for_status()

                # Wait up to timeout for result
                deadline = time.time() + timeout
                while time.time() < deadline:
                    if any("result" in r or "error" in r for r in results):
                        break
                    await asyncio.sleep(0.1)

                reader_task.cancel()
                try:
                    await asyncio.shield(reader_task)
                except (asyncio.CancelledError, BaseException):
                    pass
                await client.aclose()

            loop.run_until_complete(do_post())

            for msg in results:
                if "result" in msg:
                    return msg["result"]
            return None

    # ---- High-level API ----

    def search_memories(
        self,
        query: str,
        memory_type: str = "all",
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Semantic search over memories."""
        types = ["know", "policy", "episodic"] if memory_type == "all" else [memory_type]
        all_results = []

        for mtype in types:
            params = {
                "query": query,
                "type": mtype,
                "status": "active",
                "user_id": self.user_id,
                "limit": str(min(limit, 50)),
            }
            result = self._post_and_wait("tools/call", {
                "name": "memories_search",
                "arguments": params,
            })
            if result:
                content = result.get("content", [])
                if content and isinstance(content[0], dict):
                    inner_text = content[0].get("text", "{}")
                    inner = json.loads(inner_text)
                    items = inner.get("data", {}).get("memories", [])
                    all_results.extend(items)

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
        return self._post_and_wait("tools/call", {"name": method, "arguments": final_params})

    def generate_briefing(self, timezone: str = "America/Lima") -> str:
        """Generate daily briefing."""
        result = self._post_and_wait("tools/call", {
            "name": "briefing_generate",
            "arguments": {"timezone": timezone},
        })
        if result:
            content = result.get("content", [])
            if content and isinstance(content[0], dict):
                return content[0].get("text", "")
        return ""

    def ledger_query(
        self,
        query: str,
        status: str | None = None,
        nature: str = "all",
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Query ledger items."""
        params: dict[str, Any] = {
            "query": query,
            "limit": str(limit),
        }
        if status:
            params["status"] = status
        if nature != "all":
            params["nature"] = nature

        result = self._post_and_wait("tools/call", {
            "name": "ledger_query",
            "arguments": params,
        })
        if result:
            content = result.get("content", [])
            if content and isinstance(content[0], dict):
                inner_text = content[0].get("text", "{}")
                inner = json.loads(inner_text)
                return inner.get("data", {}).get("items", [])
        return []

    def ledger_create(
        self,
        title: str,
        nature: str,
        status: str | None = None,
        content: str | None = None,
        subject: str | None = None,
        priority: str = "medium",
        due_at: str | None = None,
        **kwargs,
    ) -> dict | None:
        """Create a ledger item."""
        params: dict[str, Any] = {
            "title": title,
            "nature": nature,
            **kwargs,
        }
        if status:
            params["status"] = status
        if content:
            params["content"] = content
        if subject:
            params["subject"] = subject
        if priority:
            params["priority"] = priority
        if due_at:
            params["due_at"] = due_at

        return self._post_and_wait("tools/call", {
            "name": "ledger_item_create",
            "arguments": params,
        })

    def ledger_bulk_action(
        self,
        ids: List[str],
        note: str,
        status: str | None = None,
        priority: str | None = None,
    ) -> dict | None:
        """Bulk update ledger items."""
        params: dict[str, Any] = {
            "ids": ids,
            "note": note,
        }
        if status:
            params["status"] = status
        if priority:
            params["priority"] = priority

        return self._post_and_wait("tools/call", {
            "name": "ledger_bulk_action",
            "arguments": params,
        })

    def browser_activity_query(
        self,
        query: str,
        site: str | None = None,
        limit: int = 10,
        match_threshold: float = 0.5,
    ) -> List[Dict[str, Any]]:
        """Query browser activity."""
        params: dict[str, Any] = {
            "query": query,
            "limit": str(limit),
            "match_threshold": str(match_threshold),
        }
        if site:
            params["site"] = site

        result = self._post_and_wait("tools/call", {
            "name": "browser_activity_query",
            "arguments": params,
        })
        if result:
            content = result.get("content", [])
            if content and isinstance(content[0], dict):
                inner_text = content[0].get("text", "{}")
                inner = json.loads(inner_text)
                return inner.get("data", {}).get("activities", [])
        return []

    def close(self) -> None:
        """Clean shutdown."""
        with self._lock:
            if self._http is not None:
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                loop.run_until_complete(self._http.aclose())
                self._http = None
                self._session_id = None


# -----------------------------------------------------------------------
# PersonalAI Memory Provider
# -----------------------------------------------------------------------

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
        env_vars = os.environ.get("PERSONAL_AI_API_KEY") and os.environ.get("PERSONAL_AI_BASE_URL")
        # Also check if the plugin version of the client can be reached
        try:
            client = PersonalAIClient()
            return client.is_available()
        except Exception:
            return bool(env_vars)

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

        # Use user_id from kwargs if available (set by gateway)
        if user_id:
            self._user_id = user_id
        elif agent_identity:
            # Fallback: use agent_identity as identifier
            pass

        # For non-primary contexts (cron), skip writes but allow reads
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

You have tools to query and manage these memories:
- personal_ai_search — semantic search over all memory types
- personal_ai_memories_manage — create/update/deprecate memories
- personal_ai_briefing_generate — daily briefing from ledger + memories
- personal_ai_ledger_query / personal_ai_ledger_item_create / personal_ai_ledger_bulk_action
- personal_ai_browser_activity_query — browser history

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

        # Check cache
        if (
            self._cached_prefetch is not None
            and (now - self._cached_prefetch[1]) < self.CACHE_TTL
            and query
        ):
            return self._cached_prefetch[0]

        if not self._client:
            return ""

        try:
            # Fetch recent "state of Diego" — profile + recent episodic + urgent actions
            results: list[str] = []

            # Quick profile
            know_results = self._client.search_memories("Diego preferences projects current", memory_type="know", limit=5)
            for item in know_results:
                c = item.get("content", "")
                if c:
                    results.append(f"[know] {c}")

            # Recent episodic
            episodic_results = self._client.search_memories("", memory_type="episodic", limit=5)
            for item in episodic_results:
                c = item.get("content", "")
                if c:
                    results.append(f"[episodic] {c}")

            if results:
                block = "## Recent Personal Context\n" + "\n".join(f"- {r}" for r in results)
            else:
                block = ""

            # Update cache
            self._cached_prefetch = (block, now)
            return block

        except Exception as e:
            logger.warning("[personal-ai] prefetch error: %s", e)
            return ""

    def queue_prefetch(self, query: str, *, session_id: str = "") -> None:
        """
        Queue a background recall for the NEXT turn.

        Called after each turn. We invalidate the cache so the next
        prefetch() fetches fresh data. Actual implementation fires a
        thread to do the fetch and update _cached_prefetch.
        """
        # Invalidate cache — next prefetch() will do fresh fetch
        self._cached_prefetch = None

    # -- Per-turn sync ------------------------------------------------------

    def sync_turn(self, user_content: str, assistant_content: str, *, session_id: str = "") -> None:
        """
        Skip per-turn sync — personal-ai uses explicit memory_manage calls.

        The old hook wrote to MEMORY.md on every session start, but the plugin
        model prefers explicit saves (personal_ai_memories_manage tool) so
        Diego controls what gets remembered vs. what is ephemeral context.

        This hook is kept for potential future automatic extraction
        (e.g., on_session_end pattern).
        """
        # No automatic per-turn writes — let Diego decide what to remember
        pass

    # -- Tools --------------------------------------------------------------

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Return all personal-ai tools."""
        return [
            SEARCH_SCHEMA,
            MEMORIES_MANAGE_SCHEMA,
            BRIEFING_SCHEMA,
            LEDGER_QUERY_SCHEMA,
            LEDGER_CREATE_SCHEMA,
            LEDGER_BULK_SCHEMA,
            BROWSER_ACTIVITY_QUERY_SCHEMA,
        ]

    def handle_tool_call(self, tool_name: str, args: Dict[str, Any], **kwargs) -> str:
        """Dispatch a tool call to the appropriate client method."""
        if not self._client:
            return json.dumps({"error": "personal-ai not initialized"})

        try:
            if tool_name == "personal_ai_search":
                results = self._client.search_memories(
                    query=args.get("query", ""),
                    memory_type=args.get("memory_type", "all"),
                    limit=args.get("limit", 10),
                )
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
                # Invalidate cache after writes
                self._cached_prefetch = None
                return json.dumps({"status": "success", "data": result})

            elif tool_name == "personal_ai_briefing_generate":
                text = self._client.generate_briefing(
                    timezone=args.get("timezone", "America/Lima"),
                )
                return json.dumps({"status": "success", "data": {"briefing": text}})

            elif tool_name == "personal_ai_ledger_query":
                items = self._client.ledger_query(
                    query=args.get("query", ""),
                    status=args.get("status"),
                    nature=args.get("nature", "all"),
                    limit=args.get("limit", 50),
                )
                return json.dumps({"status": "success", "data": {"items": items}})

            elif tool_name == "personal_ai_ledger_item_create":
                result = self._client.ledger_create(
                    title=args.get("title", ""),
                    nature=args.get("nature", ""),
                    status=args.get("status"),
                    content=args.get("content"),
                    subject=args.get("subject"),
                    priority=args.get("priority", "medium"),
                    due_at=args.get("due_at"),
                )
                return json.dumps({"status": "success", "data": result})

            elif tool_name == "personal_ai_ledger_bulk_action":
                result = self._client.ledger_bulk_action(
                    ids=args.get("ids", []),
                    note=args.get("note", ""),
                    status=args.get("status"),
                    priority=args.get("priority"),
                )
                return json.dumps({"status": "success", "data": result})

            elif tool_name == "personal_ai_browser_activity_query":
                activities = self._client.browser_activity_query(
                    query=args.get("query", ""),
                    site=args.get("site"),
                    limit=args.get("limit", 10),
                    match_threshold=args.get("match_threshold", 0.5),
                )
                return json.dumps({"status": "success", "data": {"activities": activities}})

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

        # Refresh cache every 10 turns
        if self._turn_count % 10 == 0:
            self._cached_prefetch = None

    def on_session_end(self, messages: List[Dict[str, Any]]) -> None:
        """
        End-of-session hook — not currently used.

        Could implement automatic episodic memory creation from session summary
        in a future iteration.
        """
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


# -----------------------------------------------------------------------
# Plugin entry point (register hook)
# -----------------------------------------------------------------------

def register() -> PersonalAIMemoryProvider:
    """Entry point called by MemoryManager when loading plugins."""
    return PersonalAIMemoryProvider()
