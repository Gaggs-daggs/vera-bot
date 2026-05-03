"""
Reply handler for VERA bot.
Handles multi-turn conversation logic:
- Auto-reply detection
- Intent transitions
- Hostile/opt-out handling
- Normal conversational replies
"""

import re
import logging
from typing import Optional

from composer import compose_reply

logger = logging.getLogger("vera.reply_handler")

# ── Auto-reply detection patterns ──

AUTO_REPLY_PATTERNS = [
    r"thank\s*you\s+for\s+(contacting|reaching\s+out|your\s+message)",
    r"our\s+team\s+will\s+(respond|get\s+back|reply)\s+(shortly|soon)",
    r"we\s+(will|shall)\s+(get\s+back|respond|reply)\s+to\s+you",
    r"this\s+is\s+an?\s+(auto|automated)\s*(matic)?\s*(reply|response|message)",
    r"out\s+of\s+office",
    r"currently\s+(unavailable|away|busy)",
    r"leave\s+a\s+message\s+and\s+we",
    r"business\s+hours\s+are",
    r"we\s+are\s+closed",
    r"please\s+(call|visit)\s+us\s+during",
    r"(?:hello|hi)!?\s*(?:thank\s+you|thanks)\s+for\s+(?:contacting|messaging|reaching)",
]

# ── Hostile/opt-out patterns ──

HOSTILE_PATTERNS = [
    r"stop\s+(messaging|sending|texting|contacting)\s+(me|us)",
    r"not\s+interested",
    r"leave\s+me\s+alone",
    r"don'?t\s+(message|contact|send|text)\s+(me|us)",
    r"unsubscribe",
    r"remove\s+(me|my\s+number)",
    r"(?:this|you)\s+(?:is|are)\s+(?:useless|spam|annoying|irritating)",
    r"stop\s+(?:it|this|now)",
    r"go\s+away",
    r"block(?:ed|ing)?",
    r"report(?:ed|ing)?\s+(?:you|this|spam)",
    r"why\s+are\s+you\s+bothering",
    r"waste\s+of\s+(?:time|my\s+time)",
]

# ── Intent transition signals (merchant is ready to act) ──

INTENT_COMMIT_PATTERNS = [
    r"(?:let'?s|lets)\s+do\s+(?:it|this|that)",
    r"(?:ok|okay|sure|yes)\s*,?\s*(?:go\s+ahead|do\s+it|proceed|let'?s\s+go|start)",
    r"^(?:yes|yep|yeah|yup|ya|haan|ok|okay|sure|confirm|confirmed|go\s+ahead)\s*[.!]?\s*$",
    r"sounds?\s+(?:good|great|perfect)",
    r"(?:please|pls)\s+(?:go\s+ahead|do\s+it|proceed|send|draft)",
    r"what'?s?\s+next",
    r"how\s+do\s+(?:we|i)\s+(?:start|begin|proceed)",
    r"(?:i'?m|we'?re|i\s+am)\s+(?:ready|in|interested|on\s+board)",
    r"(?:send|share|draft)\s+(?:it|them|the)",
    r"book\s+(?:it|me|my)",
]


class ReplyHandler:
    """Handles multi-turn conversation reply logic."""

    def __init__(self, context_store):
        self.store = context_store
        # Track auto-reply counts per conversation
        self._auto_reply_counts: dict[str, int] = {}

    def handle_reply(
        self,
        conversation_id: str,
        merchant_id: str,
        customer_id: Optional[str],
        from_role: str,
        message: str,
        turn_number: int,
        received_at: str = None
    ) -> dict:
        """
        Process an incoming reply and determine the bot's response.

        Returns:
            dict with: action ("send"|"wait"|"end"), body (if send), cta, rationale
            Optional: wait_seconds (if wait)
        """
        msg_lower = message.strip().lower()

        # ── Check if conversation is already ended ──
        if self.store.is_conversation_ended(conversation_id):
            return {
                "action": "end",
                "rationale": "Conversation was previously closed."
            }

        # ── Record the incoming message ──
        self.store.add_conversation_turn(
            conversation_id, from_role, message, received_at
        )

        # ── Priority 1: Detect auto-reply ──
        if self._is_auto_reply(message):
            return self._handle_auto_reply(conversation_id, message)

        # ── Priority 2: Detect hostile/opt-out ──
        if self._is_hostile(message):
            return self._handle_hostile(conversation_id, merchant_id)

        # ── Priority 3: Detect intent commitment ──
        if self._is_intent_commit(message):
            # Don't handle internally — let LLM compose action-mode reply
            # But pass a hint to the composer
            pass

        # ── Reset auto-reply counter on real message ──
        self._auto_reply_counts[conversation_id] = 0

        # ── Normal reply: compose via LLM ──
        return self._compose_contextual_reply(
            conversation_id, merchant_id, customer_id, message
        )

    def _is_auto_reply(self, message: str) -> bool:
        """Detect WhatsApp Business auto-reply patterns."""
        msg_lower = message.strip().lower()
        for pattern in AUTO_REPLY_PATTERNS:
            if re.search(pattern, msg_lower, re.IGNORECASE):
                return True
        return False

    def _is_hostile(self, message: str) -> bool:
        """Detect hostile or opt-out signals."""
        msg_lower = message.strip().lower()
        for pattern in HOSTILE_PATTERNS:
            if re.search(pattern, msg_lower, re.IGNORECASE):
                return True
        return False

    def _is_intent_commit(self, message: str) -> bool:
        """Detect when merchant signals commitment to act."""
        msg_lower = message.strip().lower()
        for pattern in INTENT_COMMIT_PATTERNS:
            if re.search(pattern, msg_lower, re.IGNORECASE):
                return True
        return False

    def _handle_auto_reply(self, conversation_id: str, message: str) -> dict:
        """
        Progressive auto-reply handling:
        1st auto-reply: send a brief nudge
        2nd auto-reply: wait 24h
        3rd+ auto-reply: end conversation
        """
        count = self._auto_reply_counts.get(conversation_id, 0) + 1
        self._auto_reply_counts[conversation_id] = count

        if count == 1:
            return {
                "action": "send",
                "body": "Looks like an auto-reply 😊 When the owner sees this, just reply 'Yes' to continue.",
                "cta": "binary_yes_no",
                "rationale": f"Detected auto-reply (attempt {count}). Sending one explicit nudge for the owner."
            }
        elif count == 2:
            return {
                "action": "wait",
                "wait_seconds": 86400,
                "rationale": f"Same auto-reply {count}x in a row → owner not at phone. Waiting 24h before retry."
            }
        else:
            self.store.end_conversation(conversation_id)
            return {
                "action": "end",
                "rationale": f"Auto-reply {count}x in a row, no real reply. Zero engagement signal; closing conversation."
            }

    def _handle_hostile(self, conversation_id: str, merchant_id: str) -> dict:
        """Graceful exit on hostile or opt-out signal."""
        self.store.end_conversation(conversation_id)
        return {
            "action": "end",
            "rationale": "Merchant explicitly opted out or expressed frustration. Closing conversation; suppressing future triggers for this merchant."
        }

    def _compose_contextual_reply(
        self,
        conversation_id: str,
        merchant_id: str,
        customer_id: Optional[str],
        message: str
    ) -> dict:
        """Use LLM to compose a contextual reply."""
        # Gather all relevant contexts
        merchant = self.store.get("merchant", merchant_id) or {}
        category_slug = merchant.get("category_slug", "")
        category = self.store.get("category", category_slug) or {}
        customer = self.store.get("customer", customer_id) if customer_id else None

        # Find the trigger that started this conversation
        # (look through conversation history for context)
        trigger = self._find_conversation_trigger(conversation_id, merchant_id)

        # Get conversation history
        conv_history = self.store.get_conversation(conversation_id)

        # Compose via LLM
        result = compose_reply(
            category=category,
            merchant=merchant,
            trigger=trigger,
            customer=customer,
            conversation_history=conv_history,
            merchant_message=message
        )

        # Record our response if we're sending
        if result.get("action") == "send" and result.get("body"):
            # Check for repetition
            if self.store.is_body_repeated(conversation_id, result["body"]):
                # If we'd repeat, modify the message
                result["body"] = result["body"] + " Let me know your thoughts."

            self.store.add_conversation_turn(
                conversation_id, "vera", result.get("body", ""), action_data=result
            )

        if result.get("action") == "end":
            self.store.end_conversation(conversation_id)

        return result

    def _find_conversation_trigger(self, conversation_id: str, merchant_id: str) -> dict:
        """Try to find the trigger context for this conversation."""
        # Look through all triggers to find one matching this merchant
        triggers = self.store.get_all_by_scope("trigger")
        for tid, trigger in triggers.items():
            if trigger.get("merchant_id") == merchant_id:
                return trigger

        # Fallback: return a minimal trigger
        return {"kind": "general", "payload": {}, "scope": "merchant", "suppression_key": ""}
