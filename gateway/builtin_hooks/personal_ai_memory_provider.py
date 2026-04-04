"""
Built-in hook: personal-ai-memory-provider

Injects personal-ai memories into the gateway's MemoryStore on session:start
and session:reset events. MemoryStore is the in-memory context injected into
every agent turn.

This is the "MemoryStore provider" path — distinct from the user hook
(personal-ai-memory-loader) which writes to ~/.hermes/memories/MEMORY.md.
"""

import logging
from typing import Any, Dict

from gateway.builtin_hooks.personal_ai_client import (
    async_fetch_all_memories,
    async_fetch_know_memories,
)

logger = logging.getLogger("gateway.builtin_hooks.personal_ai_memory_provider")


def handle(event_type: str, context: Dict[str, Any]) -> None:
    """
    Hook handler for session:start and session:reset.

    Fetches memories from personal-ai and injects them into MemoryStore
    so the agent has them in context for every turn.
    """
    if event_type not in ("session:start", "session:reset"):
        return

    user_id = context.get("user_id", "")
    if user_id != "1093162286":
        return

    session_id = context.get("session_id", "")

    try:
        import asyncio
        from gateway.memory_store import MemoryStore

        memories = asyncio.run(async_fetch_all_memories(
            query="Diego context preferences",
            limit=20,
            user_id=user_id,
        ))

        if not memories:
            logger.debug(f"[memory-provider] No memories found for user {user_id}")
            return

        ms = MemoryStore.get()
        injected_count = 0

        for mem in memories:
            content = mem.get("content", "")
            mem_type = mem.get("type", "know")
            if content:
                ms.inject(
                    source="personal-ai",
                    content=f"[{mem_type.upper()}] {content}",
                    transient=False,
                )
                injected_count += 1

        logger.info(
            f"[memory-provider] Injected {injected_count} memories into MemoryStore "
            f"for session {session_id}"
        )

    except Exception as e:
        # Never let a memory provider error break the gateway
        logger.error(f"[memory-provider] Failed to inject memories: {e}")
