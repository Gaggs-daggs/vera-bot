"""
LLM-powered message composer for VERA bot.
Takes 4 contexts and produces a composed message.
"""

import json
import os
import re
import logging
from typing import Optional

from prompt_templates import SYSTEM_PROMPT, get_trigger_instructions

logger = logging.getLogger("vera.composer")

# ── LLM Configuration ──

LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "gemini")
LLM_API_KEY = os.environ.get("LLM_API_KEY", os.environ.get("GEMINI_API_KEY", ""))
LLM_MODEL = os.environ.get("LLM_MODEL", "")


def _call_llm(prompt: str, system: str = None) -> str:
    """Call the configured LLM provider and return text response."""
    import urllib.request
    import urllib.error

    if LLM_PROVIDER == "gemini":
        model = LLM_MODEL or "gemini-2.0-flash"
        api_key = LLM_API_KEY or os.environ.get("GEMINI_API_KEY", "")
        full_prompt = f"{system}\n\n{prompt}" if system else prompt
        body = json.dumps({
            "contents": [{"parts": [{"text": full_prompt}]}],
            "generationConfig": {"temperature": 0.15, "maxOutputTokens": 2000}
        }).encode("utf-8")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
        resp = urllib.request.urlopen(req, timeout=25)
        data = json.loads(resp.read().decode("utf-8"))
        return data["candidates"][0]["content"]["parts"][0]["text"]

    elif LLM_PROVIDER == "cerebras":
        model = LLM_MODEL or "llama3.1-8b"
        api_key = LLM_API_KEY or os.environ.get("CEREBRAS_API_KEY", "")
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        body = json.dumps({
            "model": model, 
            "messages": messages,
            "temperature": 0.15, 
            "max_tokens": 2000
        }).encode("utf-8")
        req = urllib.request.Request(
            "https://api.cerebras.ai/v1/chat/completions",
            data=body,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        )
        resp = urllib.request.urlopen(req, timeout=25)
        data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"]

    elif LLM_PROVIDER == "openai":
        model = LLM_MODEL or "gpt-4o-mini"
        api_key = LLM_API_KEY or os.environ.get("OPENAI_API_KEY", "")
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        body = json.dumps({
            "model": model, "messages": messages,
            "temperature": 0.15, "max_tokens": 2000
        }).encode("utf-8")
        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=body,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        )
        resp = urllib.request.urlopen(req, timeout=25)
        data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"]

    elif LLM_PROVIDER == "anthropic":
        model = LLM_MODEL or "claude-3-5-sonnet-20241022"
        api_key = LLM_API_KEY or os.environ.get("ANTHROPIC_API_KEY", "")
        body_dict = {
            "model": model, "max_tokens": 2000,
            "messages": [{"role": "user", "content": prompt}]
        }
        if system:
            body_dict["system"] = system
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=json.dumps(body_dict).encode("utf-8"),
            headers={
                "x-api-key": api_key,
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01"
            }
        )
        resp = urllib.request.urlopen(req, timeout=25)
        data = json.loads(resp.read().decode("utf-8"))
        return data["content"][0]["text"]

    elif LLM_PROVIDER == "deepseek":
        model = LLM_MODEL or "deepseek-chat"
        api_key = LLM_API_KEY or os.environ.get("DEEPSEEK_API_KEY", "")
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        body = json.dumps({
            "model": model, "messages": messages,
            "temperature": 0.15, "max_tokens": 2000
        }).encode("utf-8")
        req = urllib.request.Request(
            "https://api.deepseek.com/v1/chat/completions",
            data=body,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        )
        resp = urllib.request.urlopen(req, timeout=25)
        data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"]

    else:
        raise ValueError(f"Unknown LLM provider: {LLM_PROVIDER}")


def _parse_json_response(text: str) -> dict:
    """Extract JSON from LLM response, handling markdown code fences."""
    # Strip markdown code fences if present
    text = text.strip()
    if text.startswith("```"):
        # Remove ```json or ``` prefix and trailing ```
        text = re.sub(r'^```(?:json)?\s*', '', text)
        text = re.sub(r'\s*```$', '', text)

    # Try to find JSON object
    match = re.search(r'\{[\s\S]*\}', text)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    # Fallback
    return {}


def _validate_and_fix(result: dict, trigger: dict, has_customer: bool) -> dict:
    """Post-LLM validation and fixes."""
    body = result.get("body", "")

    # Fix: remove URLs (penalty: -3 per URL)
    body = re.sub(r'https?://\S+', '', body).strip()

    # Fix: ensure send_as is correct for customer-facing messages
    if has_customer:
        result["send_as"] = "merchant_on_behalf"
    elif result.get("send_as") not in ("vera", "merchant_on_behalf"):
        result["send_as"] = "vera"

    # Fix: ensure suppression_key is present
    if not result.get("suppression_key"):
        result["suppression_key"] = trigger.get("suppression_key", "")

    # Fix: ensure cta is a valid value
    valid_ctas = {"binary_yes_no", "binary_confirm_cancel", "open_ended", "multi_choice_slot", "none"}
    if result.get("cta") not in valid_ctas:
        result["cta"] = "open_ended"

    # Fix: ensure rationale exists
    if not result.get("rationale"):
        result["rationale"] = "Composed from available context"

    result["body"] = body
    return result


def compose(
    category: dict,
    merchant: dict,
    trigger: dict,
    customer: Optional[dict] = None,
    conversation_history: list = None
) -> dict:
    """
    Core composition function.
    Takes 4 contexts and produces a composed message.

    Returns:
        dict with keys: body, cta, send_as, suppression_key, rationale
    """
    has_customer = customer is not None
    trigger_kind = trigger.get("kind", "general")
    trigger_payload = trigger.get("payload", {})

    # Get trigger-kind-specific instructions
    trigger_instructions = get_trigger_instructions(trigger_kind, trigger_payload, has_customer)

    # Build the context block for the prompt
    identity = merchant.get("identity", {})
    perf = merchant.get("performance", {})
    offers = merchant.get("offers", [])
    active_offers = [o for o in offers if o.get("status") == "active"]
    signals = merchant.get("signals", [])
    conv_hist = merchant.get("conversation_history", [])
    cust_agg = merchant.get("customer_aggregate", {})
    review_themes = merchant.get("review_themes", [])

    # Category context summary
    voice = category.get("voice", {})
    peer_stats = category.get("peer_stats", {})
    digest = category.get("digest", [])
    offer_catalog = category.get("offer_catalog", [])
    seasonal = category.get("seasonal_beats", [])
    trends = category.get("trend_signals", [])

    prompt = f"""=== COMPOSE A MESSAGE ===

{trigger_instructions}

=== CATEGORY CONTEXT ({category.get('slug', 'unknown')}) ===
Voice/Tone: {json.dumps(voice)}
Peer Stats: {json.dumps(peer_stats)}
Category Offer Catalog: {json.dumps(offer_catalog[:5])}
Recent Digest Items: {json.dumps(digest[:3])}
Seasonal Beats: {json.dumps(seasonal[:3])}
Trend Signals: {json.dumps(trends[:3])}

=== MERCHANT CONTEXT ===
Name: {identity.get('name', 'Unknown')}
Owner: {identity.get('owner_first_name', 'Unknown')}
City: {identity.get('city', '')}, Locality: {identity.get('locality', '')}
Languages: {identity.get('languages', ['en'])}
Established: {identity.get('established_year', '')}
Verified: {identity.get('verified', False)}
Subscription: {json.dumps(merchant.get('subscription', {}))}
Performance (30d): views={perf.get('views', '?')}, calls={perf.get('calls', '?')}, directions={perf.get('directions', '?')}, CTR={perf.get('ctr', '?')}, leads={perf.get('leads', '?')}
7-day delta: {json.dumps(perf.get('delta_7d', {}))}
Active Offers: {json.dumps(active_offers)}
Signals: {signals}
Customer Aggregate: {json.dumps(cust_agg)}
Review Themes: {json.dumps(review_themes[:3])}
Recent Conversation with Vera: {json.dumps(conv_hist[-3:]) if conv_hist else 'None'}

=== TRIGGER CONTEXT ===
Kind: {trigger_kind}
Source: {trigger.get('source', 'internal')}
Scope: {trigger.get('scope', 'merchant')}
Urgency: {trigger.get('urgency', 1)}/5
Payload: {json.dumps(trigger_payload)}
Suppression Key: {trigger.get('suppression_key', '')}
"""

    if customer:
        cust_identity = customer.get("identity", {})
        cust_rel = customer.get("relationship", {})
        prompt += f"""
=== CUSTOMER CONTEXT ===
Name: {cust_identity.get('name', 'Unknown')}
Language Pref: {cust_identity.get('language_pref', 'en')}
Age Band: {cust_identity.get('age_band', '')}
Relationship: first_visit={cust_rel.get('first_visit', '?')}, last_visit={cust_rel.get('last_visit', '?')}, visits={cust_rel.get('visits_total', '?')}
Services Received: {cust_rel.get('services_received', [])}
State: {customer.get('state', 'unknown')}
Preferences: {json.dumps(customer.get('preferences', {}))}
Consent: {json.dumps(customer.get('consent', {}))}
"""

    if conversation_history:
        prompt += f"""
=== ONGOING CONVERSATION (reply in context) ===
{json.dumps(conversation_history[-5:], indent=2)}
"""

    prompt += """
Now compose the message. Return ONLY the JSON object with body, cta, send_as, suppression_key, rationale.
"""

    try:
        raw_response = _call_llm(prompt, SYSTEM_PROMPT)
        result = _parse_json_response(raw_response)

        if not result or not result.get("body"):
            logger.warning(f"LLM returned empty/invalid JSON for trigger {trigger_kind}")
            # Fallback: use raw text as body
            result = {
                "body": raw_response[:500] if raw_response else f"Hi {identity.get('owner_first_name', '')}, checking in about your business.",
                "cta": "open_ended",
                "send_as": "merchant_on_behalf" if has_customer else "vera",
                "suppression_key": trigger.get("suppression_key", ""),
                "rationale": "Fallback composition — LLM response parsing failed"
            }

        return _validate_and_fix(result, trigger, has_customer)

    except Exception as e:
        logger.error(f"Composer error for trigger {trigger_kind}: {e}")
        # Absolute fallback
        owner = identity.get("owner_first_name", "")
        name = identity.get("name", "your business")
        return {
            "body": f"Hi {owner}, quick update about {name} — I noticed some new data worth reviewing. Want me to share the details?",
            "cta": "open_ended",
            "send_as": "merchant_on_behalf" if has_customer else "vera",
            "suppression_key": trigger.get("suppression_key", ""),
            "rationale": f"Fallback composition due to error: {str(e)[:100]}"
        }


def compose_reply(
    category: dict,
    merchant: dict,
    trigger: dict,
    customer: Optional[dict],
    conversation_history: list,
    merchant_message: str
) -> dict:
    """
    Compose a reply to a merchant/customer message within an existing conversation.

    Returns:
        dict with keys: action, body, cta, rationale
        action is one of: "send", "wait", "end"
    """
    identity = merchant.get("identity", {})
    trigger_kind = trigger.get("kind", "general")

    prompt = f"""=== COMPOSE A REPLY ===

You are in an ongoing conversation. The merchant/customer just replied.

MERCHANT: {identity.get('name', 'Unknown')} ({identity.get('owner_first_name', '')})
CATEGORY: {category.get('slug', 'unknown')}
TRIGGER KIND: {trigger_kind}
LANGUAGE PREF: {identity.get('languages', ['en'])}

CONVERSATION SO FAR:
{json.dumps(conversation_history[-6:], indent=2)}

THEIR LATEST MESSAGE: "{merchant_message}"

RULES FOR REPLYING:
1. If they said YES/confirmed → EXECUTE the action immediately. Draft the artifact. Don't ask more questions.
2. If they asked a question → Answer it directly using available context, then offer the next step.
3. If they asked for something off-topic (GST, legal, etc.) → Politely decline ("I'll leave that to your CA") and redirect back to the trigger topic.
4. If they said they're not interested → Respect it. Action: "end".
5. Match their language style (if they wrote in Hindi, reply in Hindi-English mix).
6. DON'T repeat what you already said. Advance the conversation.

Return ONLY valid JSON:
{{
  "action": "send" | "wait" | "end",
  "body": "your reply text (only if action=send)",
  "cta": "binary_yes_no" | "open_ended" | "none",
  "wait_seconds": 1800,
  "rationale": "why this response"
}}
"""

    try:
        raw = _call_llm(prompt, SYSTEM_PROMPT)
        result = _parse_json_response(raw)

        if not result or "action" not in result:
            result = {
                "action": "send",
                "body": "Got it — let me work on that for you.",
                "cta": "open_ended",
                "rationale": "Fallback reply"
            }

        # Validate action
        if result["action"] not in ("send", "wait", "end"):
            result["action"] = "send"

        # Remove URLs from body
        if result.get("body"):
            result["body"] = re.sub(r'https?://\S+', '', result["body"]).strip()

        return result

    except Exception as e:
        logger.error(f"Reply composer error: {e}")
        return {
            "action": "send",
            "body": "Noted — let me follow up on that shortly.",
            "cta": "open_ended",
            "rationale": f"Fallback due to error: {str(e)[:100]}"
        }
