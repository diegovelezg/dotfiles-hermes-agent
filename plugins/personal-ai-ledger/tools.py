"""
Tool handlers for personal-ai-ledger plugin.
Each handler is a standalone callable: (args: dict, **kwargs) -> JSON string.
Based on Intelligence MCP (UIA Core) API spec.
"""

from __future__ import annotations

import json
import logging
import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from . import PersonalAIClient

logger = logging.getLogger(__name__)

# ─── Persistent client (lazy init, thread-safe) ─────────────────────────────

_client: "PersonalAIClient | None" = None
_client_lock = threading.Lock()


def _get_client() -> "PersonalAIClient":
    global _client
    with _client_lock:
        if _client is None:
            from . import PersonalAIClient

            _client = PersonalAIClient()
        return _client


# ─── Tool handlers ───────────────────────────────────────────────────────────


def ledger_query(args: dict, **kwargs) -> str:
    """Search ledger items using hybrid (Lexical + Graph) search."""
    client = _get_client()
    if not client.is_available():
        return json.dumps({"error": "personal-ai-ledger not available"})
    try:
        result = client.call_tool("ledger_query", args)
        return json.dumps({"status": "success", "data": result})
    except Exception as e:
        logger.error("ledger_query failed: %s", e)
        return json.dumps({"status": "error", "error": str(e)})


def ledger_item_create(args: dict, **kwargs) -> str:
    """Create a new ledger item (action or intel)."""
    client = _get_client()
    if not client.is_available():
        return json.dumps({"error": "personal-ai-ledger not available"})
    try:
        result = client.call_tool("ledger_item_create", args)
        return json.dumps({"status": "success", "data": result})
    except Exception as e:
        logger.error("ledger_item_create failed: %s", e)
        return json.dumps({"status": "error", "error": str(e)})


def ledger_bulk_action(args: dict, **kwargs) -> str:
    """Bulk update/archive ledger items. Note is required (logged as reason)."""
    client = _get_client()
    if not client.is_available():
        return json.dumps({"error": "personal-ai-ledger not available"})
    if "ids" not in args:
        return json.dumps({"error": "ledger_bulk_action requires 'ids' (list of UUIDs)"})
    if "note" not in args:
        return json.dumps({"error": "ledger_bulk_action requires 'note' (reason for change)"})
    try:
        result = client.call_tool("ledger_bulk_action", args)
        return json.dumps({"status": "success", "data": result})
    except Exception as e:
        logger.error("ledger_bulk_action failed: %s", e)
        return json.dumps({"status": "error", "error": str(e)})


def briefing_generate(args: dict, **kwargs) -> str:
    """Generate a structured executive briefing from ledger items."""
    client = _get_client()
    if not client.is_available():
        return json.dumps({"error": "personal-ai-ledger not available"})
    try:
        result = client.call_tool("briefing_generate", args)
        return json.dumps({"status": "success", "data": result})
    except Exception as e:
        logger.error("briefing_generate failed: %s", e)
        return json.dumps({"status": "error", "error": str(e)})


def browser_activity_add(args: dict, **kwargs) -> str:
    """Log a browser activity with vectorized summary (Chrome Extension data)."""
    client = _get_client()
    if not client.is_available():
        return json.dumps({"error": "personal-ai-ledger not available"})
    if "site" not in args or "summary" not in args:
        return json.dumps({"error": "browser_activity_add requires 'site' and 'summary'"})
    try:
        result = client.call_tool("browser_activity_add", args)
        return json.dumps({"status": "success", "data": result})
    except Exception as e:
        logger.error("browser_activity_add failed: %s", e)
        return json.dumps({"status": "error", "error": str(e)})


def browser_activity_query(args: dict, **kwargs) -> str:
    """Search browser activity history using semantic embeddings."""
    client = _get_client()
    if not client.is_available():
        return json.dumps({"error": "personal-ai-ledger not available"})
    try:
        result = client.call_tool("browser_activity_query", args)
        return json.dumps({"status": "success", "data": result})
    except Exception as e:
        logger.error("browser_activity_query failed: %s", e)
        return json.dumps({"status": "error", "error": str(e)})


# ─── Handler map (name -> callable) ─────────────────────────────────────────

HANDLERS = {
    "ledger_query": ledger_query,
    "ledger_item_create": ledger_item_create,
    "ledger_bulk_action": ledger_bulk_action,
    "briefing_generate": briefing_generate,
    "browser_activity_add": browser_activity_add,
    "browser_activity_query": browser_activity_query,
}
