"""
VERA Bot — Magicpin AI Challenge Submission
Pure Python HTTP server (zero external dependencies) implementing 5 endpoints:
  - GET  /v1/healthz
  - GET  /v1/metadata
  - POST /v1/context
  - POST /v1/tick
  - POST /v1/reply

When FastAPI/uvicorn are available, will use those instead for production.
"""

import json
import time
import logging
import os
import sys
import re
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, timezone
from typing import Optional, Any
from urllib.parse import urlparse

import threading
import urllib.request
import urllib.error

from context_store import ContextStore
from composer import compose
from reply_handler import ReplyHandler


# ── Keep-alive self-ping (prevents Render free tier from sleeping) ──

def _keep_alive_loop():
    """Background thread that pings our own healthz every 10 minutes."""
    port = int(os.environ.get("PORT", 8080))
    url = f"http://localhost:{port}/v1/healthz"
    while True:
        time.sleep(600)  # 10 minutes
        try:
            urllib.request.urlopen(url, timeout=5)
            logger.debug("Keep-alive ping OK")
        except Exception:
            pass  # Server might not be up yet

def start_keep_alive():
    """Start the keep-alive background thread."""
    t = threading.Thread(target=_keep_alive_loop, daemon=True)
    t.start()
    logger.info("Keep-alive self-ping started (every 10 min)")

# ── Logging ──

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s"
)
logger = logging.getLogger("vera.bot")

# ── Global state ──

store = ContextStore()
reply_handler = ReplyHandler(store)
START_TIME = time.time()


class VeraHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the VERA bot."""

    def _send_json(self, data: dict, status: int = 200):
        """Send a JSON response."""
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> dict:
        """Read and parse JSON request body."""
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            return {}
        raw = self.rfile.read(content_length)
        return json.loads(raw.decode("utf-8"))

    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        """Handle GET requests."""
        path = urlparse(self.path).path

        if path == "/v1/healthz":
            self._handle_healthz()
        elif path == "/v1/metadata":
            self._handle_metadata()
        elif path == "/":
            self._send_json({"message": "VERA Bot is running", "version": "1.0.0"})
        else:
            self._send_json({"error": "not_found"}, 404)

    def do_POST(self):
        """Handle POST requests."""
        path = urlparse(self.path).path

        try:
            body = self._read_body()
        except Exception as e:
            self._send_json({"error": f"invalid_json: {e}"}, 400)
            return

        if path == "/v1/context":
            self._handle_context(body)
        elif path == "/v1/tick":
            self._handle_tick(body)
        elif path == "/v1/reply":
            self._handle_reply(body)
        else:
            self._send_json({"error": "not_found"}, 404)

    def log_message(self, format, *args):
        """Suppress default logging, use our logger instead."""
        logger.info(f"{self.client_address[0]} - {format % args}")

    # ═══════════════════════════════════════════════
    # ENDPOINT HANDLERS
    # ═══════════════════════════════════════════════

    def _handle_healthz(self):
        """GET /v1/healthz — Health check."""
        self._send_json({
            "status": "ok",
            "uptime_seconds": int(time.time() - START_TIME),
            "contexts_loaded": store.counts()
        })

    def _handle_metadata(self):
        """GET /v1/metadata — Team and approach metadata."""
        self._send_json({
            "team_name": "Solo Gunner",
            "team_members": ["Gugan K"],
            "model": "gemini-2.0-flash",
            "approach": (
                "4-context LLM composer with trigger-kind routing, auto-reply detection, "
                "intent transition handling. 21 trigger-kind-specific prompt templates + "
                "post-LLM validation guards for anti-fabrication and CTA enforcement."
            ),
            "contact_email": "gugank@example.com",
            "version": "1.0.0",
            "submitted_at": datetime.now(timezone.utc).isoformat()
        })

    def _handle_context(self, body: dict):
        """POST /v1/context — Idempotent context upsert."""
        scope = body.get("scope", "")
        context_id = body.get("context_id", "")
        version = body.get("version", 0)
        payload = body.get("payload", {})

        if not scope or not context_id or not version:
            self._send_json({"error": "missing required fields: scope, context_id, version"}, 400)
            return

        accepted, reason, current_version = store.upsert(scope, context_id, version, payload)

        if not accepted:
            if reason == "stale_version":
                self._send_json({
                    "accepted": False,
                    "reason": "stale_version",
                    "current_version": current_version
                }, 409)
            else:
                self._send_json({"accepted": False, "reason": reason}, 400)
            return

        stored_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        ack_id = f"ack_{context_id}_v{version}"

        logger.info(f"Context accepted: scope={scope}, id={context_id}, v={version}")

        self._send_json({
            "accepted": True,
            "ack_id": ack_id,
            "stored_at": stored_at
        })

    def _handle_tick(self, body: dict):
        """POST /v1/tick — Evaluate triggers and compose messages."""
        now = body.get("now", datetime.now(timezone.utc).isoformat())
        available_triggers = body.get("available_triggers", [])

        actions = []
        seen_merchants = set()

        for trigger_id in available_triggers:
            trigger = store.get("trigger", trigger_id)
            if not trigger:
                logger.warning(f"Trigger not found: {trigger_id}")
                continue

            merchant_id = trigger.get("merchant_id", "")
            customer_id = trigger.get("customer_id")

            # Skip if we already have an action for this merchant
            if merchant_id in seen_merchants:
                continue

            # Skip if suppressed
            suppression_key = trigger.get("suppression_key", "")
            if suppression_key and store.is_suppressed(merchant_id, suppression_key):
                logger.info(f"Skipping suppressed trigger: {trigger_id}")
                continue

            # Get merchant context
            merchant = store.get("merchant", merchant_id)
            if not merchant:
                logger.warning(f"Merchant not found: {merchant_id}")
                continue

            # Get category context
            category_slug = merchant.get("category_slug", "")
            category = store.get("category", category_slug) or {}

            # Get customer context (optional)
            customer = store.get("customer", customer_id) if customer_id else None

            try:
                # Compose the message
                result = compose(
                    category=category,
                    merchant=merchant,
                    trigger=trigger,
                    customer=customer
                )

                if not result.get("body"):
                    continue

                # Generate conversation ID
                trigger_kind = trigger.get("kind", "general")
                conv_id = f"conv_{merchant_id[:20]}_{trigger_kind}_{trigger_id[-8:]}"

                # Check for ended conversations
                if store.is_conversation_ended(conv_id):
                    continue

                # Build template params
                body_text = result["body"]
                owner = merchant.get("identity", {}).get("owner_first_name", "")
                template_params = [owner, body_text[:100], result.get("cta", "open_ended")]

                # Mark suppression
                if suppression_key:
                    store.add_suppression(merchant_id, suppression_key)

                # Record the sent message
                store.add_conversation_turn(conv_id, "vera", body_text, now)
                store.is_body_repeated(conv_id, body_text)

                action = {
                    "conversation_id": conv_id,
                    "merchant_id": merchant_id,
                    "customer_id": customer_id,
                    "send_as": result.get("send_as", "vera"),
                    "trigger_id": trigger_id,
                    "template_name": f"vera_{trigger_kind}_v1",
                    "template_params": template_params,
                    "body": body_text,
                    "cta": result.get("cta", "open_ended"),
                    "suppression_key": suppression_key,
                    "rationale": result.get("rationale", "")
                }

                actions.append(action)
                seen_merchants.add(merchant_id)
                logger.info(f"Composed action for trigger={trigger_id}, merchant={merchant_id}")

            except Exception as e:
                logger.error(f"Error composing for trigger {trigger_id}: {e}")
                continue

        self._send_json({"actions": actions})

    def _handle_reply(self, body: dict):
        """POST /v1/reply — Handle a reply in an ongoing conversation."""
        conversation_id = body.get("conversation_id", "")
        merchant_id = body.get("merchant_id", "")
        customer_id = body.get("customer_id")
        from_role = body.get("from_role", "merchant")
        message = body.get("message", "")
        received_at = body.get("received_at")
        turn_number = body.get("turn_number", 0)

        if not conversation_id or not message:
            self._send_json({"error": "missing conversation_id or message"}, 400)
            return

        try:
            result = reply_handler.handle_reply(
                conversation_id=conversation_id,
                merchant_id=merchant_id,
                customer_id=customer_id,
                from_role=from_role,
                message=message,
                turn_number=turn_number,
                received_at=received_at
            )

            response = {
                "action": result.get("action", "send"),
                "rationale": result.get("rationale", "")
            }

            if result.get("body"):
                response["body"] = result["body"]
            if result.get("cta"):
                response["cta"] = result["cta"]
            if result.get("wait_seconds"):
                response["wait_seconds"] = result["wait_seconds"]

            logger.info(f"Reply: conv={conversation_id}, action={response['action']}")
            self._send_json(response)

        except Exception as e:
            logger.error(f"Reply error for conv={conversation_id}: {e}")
            self._send_json({
                "action": "send",
                "body": "Let me look into that and get back to you.",
                "cta": "open_ended",
                "rationale": f"Fallback due to error: {str(e)[:100]}"
            })


def run_server(port: int = 8080):
    """Start the VERA bot HTTP server."""
    server = HTTPServer(("0.0.0.0", port), VeraHandler)
    logger.info(f"VERA Bot running on http://0.0.0.0:{port}")
    logger.info(f"Health: http://localhost:{port}/v1/healthz")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        server.server_close()


# ═══════════════════════════════════════════════
# TRY FASTAPI FIRST, FALLBACK TO STDLIB
# ═══════════════════════════════════════════════

try:
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel, Field

    app = FastAPI(title="VERA Bot", version="1.0.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
    )

    @app.get("/v1/healthz")
    async def healthz():
        return {
            "status": "ok",
            "uptime_seconds": int(time.time() - START_TIME),
            "contexts_loaded": store.counts()
        }

    @app.get("/v1/metadata")
    async def metadata():
        return {
            "team_name": "Solo Gunner",
            "team_members": ["Gugan K"],
            "model": "gemini-2.0-flash",
            "approach": (
                "4-context LLM composer with trigger-kind routing, auto-reply detection, "
                "intent transition handling. 21 trigger-kind-specific prompt templates + "
                "post-LLM validation guards."
            ),
            "contact_email": "gugank@example.com",
            "version": "1.0.0",
            "submitted_at": datetime.now(timezone.utc).isoformat()
        }

    @app.post("/v1/context")
    async def push_context(req: dict):
        scope = req.get("scope", "")
        context_id = req.get("context_id", "")
        version = req.get("version", 0)
        payload = req.get("payload", {})

        accepted, reason, current_version = store.upsert(scope, context_id, version, payload)

        if not accepted:
            if reason == "stale_version":
                from fastapi.responses import JSONResponse
                return JSONResponse(
                    content={"accepted": False, "reason": "stale_version", "current_version": current_version},
                    status_code=409
                )
            from fastapi.responses import JSONResponse
            return JSONResponse(content={"accepted": False, "reason": reason}, status_code=400)

        stored_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        return {"accepted": True, "ack_id": f"ack_{context_id}_v{version}", "stored_at": stored_at}

    @app.post("/v1/tick")
    async def tick(req: dict):
        handler = VeraHandler.__new__(VeraHandler)
        # Use the stdlib handler's tick logic but return directly
        now = req.get("now", datetime.now(timezone.utc).isoformat())
        available_triggers = req.get("available_triggers", [])

        actions = []
        seen_merchants = set()

        for trigger_id in available_triggers:
            trigger = store.get("trigger", trigger_id)
            if not trigger:
                continue
            merchant_id = trigger.get("merchant_id", "")
            customer_id = trigger.get("customer_id")
            if merchant_id in seen_merchants:
                continue
            suppression_key = trigger.get("suppression_key", "")
            if suppression_key and store.is_suppressed(merchant_id, suppression_key):
                continue
            merchant = store.get("merchant", merchant_id)
            if not merchant:
                continue
            category_slug = merchant.get("category_slug", "")
            category = store.get("category", category_slug) or {}
            customer = store.get("customer", customer_id) if customer_id else None

            try:
                result = compose(category=category, merchant=merchant, trigger=trigger, customer=customer)
                if not result.get("body"):
                    continue
                trigger_kind = trigger.get("kind", "general")
                conv_id = f"conv_{merchant_id[:20]}_{trigger_kind}_{trigger_id[-8:]}"
                if store.is_conversation_ended(conv_id):
                    continue
                body_text = result["body"]
                owner = merchant.get("identity", {}).get("owner_first_name", "")
                if suppression_key:
                    store.add_suppression(merchant_id, suppression_key)
                store.add_conversation_turn(conv_id, "vera", body_text, now)
                store.is_body_repeated(conv_id, body_text)
                actions.append({
                    "conversation_id": conv_id,
                    "merchant_id": merchant_id,
                    "customer_id": customer_id,
                    "send_as": result.get("send_as", "vera"),
                    "trigger_id": trigger_id,
                    "template_name": f"vera_{trigger_kind}_v1",
                    "template_params": [owner, body_text[:100], result.get("cta", "open_ended")],
                    "body": body_text,
                    "cta": result.get("cta", "open_ended"),
                    "suppression_key": suppression_key,
                    "rationale": result.get("rationale", "")
                })
                seen_merchants.add(merchant_id)
            except Exception as e:
                logger.error(f"Error composing for trigger {trigger_id}: {e}")
                continue

        return {"actions": actions}

    @app.post("/v1/reply")
    async def reply(req: dict):
        try:
            result = reply_handler.handle_reply(
                conversation_id=req.get("conversation_id", ""),
                merchant_id=req.get("merchant_id", ""),
                customer_id=req.get("customer_id"),
                from_role=req.get("from_role", "merchant"),
                message=req.get("message", ""),
                turn_number=req.get("turn_number", 0),
                received_at=req.get("received_at")
            )
            response = {"action": result.get("action", "send"), "rationale": result.get("rationale", "")}
            if result.get("body"):
                response["body"] = result["body"]
            if result.get("cta"):
                response["cta"] = result["cta"]
            if result.get("wait_seconds"):
                response["wait_seconds"] = result["wait_seconds"]
            return response
        except Exception as e:
            return {"action": "send", "body": "Let me look into that.", "cta": "open_ended", "rationale": f"Fallback: {e}"}

    @app.get("/")
    async def root():
        return {"message": "VERA Bot is running", "version": "1.0.0"}

    HAS_FASTAPI = True
    logger.info("FastAPI available — using ASGI mode")

    @app.on_event("startup")
    async def on_startup():
        start_keep_alive()

except ImportError:
    HAS_FASTAPI = False
    app = None
    logger.info("FastAPI not available — using stdlib HTTP server")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))

    if HAS_FASTAPI:
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=port)
    else:
        start_keep_alive()
        run_server(port)

