"""
In-memory context store for VERA bot.
Handles versioned context upserts with idempotency.
"""

import time
from datetime import datetime, timezone
from typing import Any, Optional


class ContextStore:
    """Thread-safe in-memory store for all 4 context scopes."""

    def __init__(self):
        # (scope, context_id) -> {"version": int, "payload": dict}
        self._contexts: dict[tuple[str, str], dict] = {}
        # conversation_id -> [{"from": str, "body": str, "ts": str, "action_data": dict}]
        self._conversations: dict[str, list[dict]] = {}
        # conversation_id -> set of sent body hashes (anti-repetition)
        self._sent_bodies: dict[str, set[str]] = {}
        # merchant_id -> set of suppression_keys that have been fired
        self._suppressed: dict[str, set[str]] = {}
        # merchant_id -> set of conversation_ids that are ended
        self._ended_conversations: set[str] = set()

    def upsert(self, scope: str, context_id: str, version: int, payload: dict) -> tuple[bool, str, int]:
        """
        Insert or update context.
        Returns: (accepted, reason, current_version)
        """
        valid_scopes = {"category", "merchant", "customer", "trigger"}
        if scope not in valid_scopes:
            return False, "invalid_scope", 0

        if version <= 0:
            return False, "invalid_version", 0

        key = (scope, context_id)
        current = self._contexts.get(key)

        if current and current["version"] >= version:
            return False, "stale_version", current["version"]

        self._contexts[key] = {"version": version, "payload": payload}
        return True, "ok", version

    def get(self, scope: str, context_id: str) -> Optional[dict]:
        """Get the payload for a given scope and context_id."""
        entry = self._contexts.get((scope, context_id))
        return entry["payload"] if entry else None

    def get_version(self, scope: str, context_id: str) -> int:
        """Get current version for a context."""
        entry = self._contexts.get((scope, context_id))
        return entry["version"] if entry else 0

    def counts(self) -> dict[str, int]:
        """Count contexts by scope."""
        counts = {"category": 0, "merchant": 0, "customer": 0, "trigger": 0}
        for (scope, _), _ in self._contexts.items():
            if scope in counts:
                counts[scope] += 1
        return counts

    def get_all_by_scope(self, scope: str) -> dict[str, dict]:
        """Get all payloads for a given scope. Returns {context_id: payload}."""
        result = {}
        for (s, cid), entry in self._contexts.items():
            if s == scope:
                result[cid] = entry["payload"]
        return result

    # ── Conversation tracking ──

    def add_conversation_turn(self, conversation_id: str, from_role: str, body: str, ts: str = None, action_data: dict = None):
        """Record a turn in a conversation."""
        if conversation_id not in self._conversations:
            self._conversations[conversation_id] = []
        self._conversations[conversation_id].append({
            "from": from_role,
            "body": body,
            "ts": ts or datetime.now(timezone.utc).isoformat(),
            "action_data": action_data or {}
        })

    def get_conversation(self, conversation_id: str) -> list[dict]:
        """Get all turns for a conversation."""
        return self._conversations.get(conversation_id, [])

    def is_body_repeated(self, conversation_id: str, body: str) -> bool:
        """Check if this exact body was already sent in this conversation."""
        if conversation_id not in self._sent_bodies:
            self._sent_bodies[conversation_id] = set()
        body_hash = hash(body.strip().lower())
        if body_hash in self._sent_bodies[conversation_id]:
            return True
        self._sent_bodies[conversation_id].add(body_hash)
        return False

    # ── Suppression tracking ──

    def is_suppressed(self, merchant_id: str, suppression_key: str) -> bool:
        """Check if a suppression key has already fired for this merchant."""
        return suppression_key in self._suppressed.get(merchant_id, set())

    def add_suppression(self, merchant_id: str, suppression_key: str):
        """Mark a suppression key as fired."""
        if merchant_id not in self._suppressed:
            self._suppressed[merchant_id] = set()
        self._suppressed[merchant_id].add(suppression_key)

    # ── Ended conversation tracking ──

    def end_conversation(self, conversation_id: str):
        """Mark a conversation as ended."""
        self._ended_conversations.add(conversation_id)

    def is_conversation_ended(self, conversation_id: str) -> bool:
        """Check if a conversation has been ended."""
        return conversation_id in self._ended_conversations
