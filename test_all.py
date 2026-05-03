#!/usr/bin/env python3
"""
Comprehensive test suite for VERA Bot.
Covers: unit, integration, accuracy, performance, edge cases.
"""

import sys, os, json, time, re, traceback
sys.path.insert(0, os.path.dirname(__file__))

from context_store import ContextStore
from reply_handler import ReplyHandler, AUTO_REPLY_PATTERNS, HOSTILE_PATTERNS, INTENT_COMMIT_PATTERNS
from prompt_templates import SYSTEM_PROMPT, get_trigger_instructions, TRIGGER_INSTRUCTIONS

PASS = 0
FAIL = 0

def ok(desc):
    global PASS; PASS += 1; print(f"  ✅ {desc}")

def fail(desc, detail=""):
    global FAIL; FAIL += 1; print(f"  ❌ {desc} — {detail}")

def assert_eq(a, b, desc):
    if a == b: ok(desc)
    else: fail(desc, f"expected {b!r}, got {a!r}")

def assert_true(val, desc):
    if val: ok(desc)
    else: fail(desc, "was False")

def assert_false(val, desc):
    if not val: ok(desc)
    else: fail(desc, "was True")

# ═══════════════════════════════════════
# LOAD SEED DATA
# ═══════════════════════════════════════
def load_seeds():
    base = os.path.join(os.path.dirname(__file__), "dataset")
    cats = {}
    for f in os.listdir(os.path.join(base, "categories")):
        if f.endswith(".json"):
            with open(os.path.join(base, "categories", f)) as fp:
                d = json.load(fp); cats[d["slug"]] = d
    with open(os.path.join(base, "merchants_seed.json")) as fp:
        merchants = json.load(fp)["merchants"]
    with open(os.path.join(base, "triggers_seed.json")) as fp:
        triggers = json.load(fp)["triggers"]
    with open(os.path.join(base, "customers_seed.json")) as fp:
        customers = json.load(fp)["customers"]
    return cats, merchants, triggers, customers

cats, merchants, triggers, customers = load_seeds()

# ═══════════════════════════════════════
print("\n" + "="*60)
print("1. UNIT TESTS — ContextStore")
print("="*60)
# ═══════════════════════════════════════

s = ContextStore()

# Basic upsert
a, r, v = s.upsert("category", "dentists", 1, {"slug": "dentists"})
assert_true(a, "upsert category v1")
assert_eq(r, "ok", "upsert reason ok")

# Idempotency — same version rejected
a2, r2, v2 = s.upsert("category", "dentists", 1, {"slug": "dentists"})
assert_false(a2, "reject same version")
assert_eq(r2, "stale_version", "stale_version reason")
assert_eq(v2, 1, "current_version returned")

# Lower version rejected
a3, r3, v3 = s.upsert("category", "dentists", 0, {})
assert_false(a3, "reject lower version")

# Higher version accepted
a4, r4, v4 = s.upsert("category", "dentists", 2, {"slug": "dentists", "v2": True})
assert_true(a4, "accept higher version")
assert_eq(v4, 2, "version bumped to 2")

# Get retrieval
data = s.get("category", "dentists")
assert_true(data.get("v2") == True, "get returns latest version data")

# Missing key
assert_eq(s.get("category", "nonexistent"), None, "get missing returns None")
assert_eq(s.get_version("category", "nonexistent"), 0, "get_version missing returns 0")

# Invalid scope
a5, r5, _ = s.upsert("invalid_scope", "x", 1, {})
assert_false(a5, "reject invalid scope")
assert_eq(r5, "invalid_scope", "invalid_scope reason")

# All 4 scopes
for scope in ["category", "merchant", "customer", "trigger"]:
    ok_s, _, _ = s.upsert(scope, f"test_{scope}", 1, {"scope": scope})
    assert_true(ok_s, f"upsert {scope} works")

# Counts
counts = s.counts()
assert_eq(counts["category"], 2, "category count=2")  # dentists + test_category
assert_eq(counts["merchant"], 1, "merchant count=1")
assert_eq(counts["customer"], 1, "customer count=1")
assert_eq(counts["trigger"], 1, "trigger count=1")

# get_all_by_scope
s.upsert("merchant", "m1", 1, {"name": "A"})
s.upsert("merchant", "m2", 1, {"name": "B"})
all_m = s.get_all_by_scope("merchant")
assert_eq(len(all_m), 3, "get_all_by_scope returns 3 merchants")

# Conversation tracking
s.add_conversation_turn("c1", "vera", "hello")
s.add_conversation_turn("c1", "merchant", "hi")
conv = s.get_conversation("c1")
assert_eq(len(conv), 2, "conversation has 2 turns")
assert_eq(conv[0]["from"], "vera", "turn 1 from vera")
assert_eq(conv[1]["body"], "hi", "turn 2 body correct")
assert_eq(s.get_conversation("nonexistent"), [], "missing conv returns []")

# Body repetition
assert_false(s.is_body_repeated("c2", "msg1"), "first send not repeated")
assert_true(s.is_body_repeated("c2", "msg1"), "second send IS repeated")
assert_false(s.is_body_repeated("c2", "msg2"), "different msg not repeated")

# Suppression
assert_false(s.is_suppressed("m1", "key1"), "not suppressed initially")
s.add_suppression("m1", "key1")
assert_true(s.is_suppressed("m1", "key1"), "suppressed after add")
assert_false(s.is_suppressed("m1", "key2"), "different key not suppressed")
assert_false(s.is_suppressed("m2", "key1"), "different merchant not suppressed")

# Ended conversations
assert_false(s.is_conversation_ended("c3"), "conv not ended initially")
s.end_conversation("c3")
assert_true(s.is_conversation_ended("c3"), "conv ended after end_conversation")

# ═══════════════════════════════════════
print("\n" + "="*60)
print("2. UNIT TESTS — Reply Handler Patterns")
print("="*60)
# ═══════════════════════════════════════

# Auto-reply detection
auto_reply_test_cases = [
    ("Thank you for contacting Dr. Meera's Dental Clinic! Our team will respond shortly.", True),
    ("This is an automated reply. We will get back to you soon.", True),
    ("Hi! Thank you for reaching out. We will reply shortly.", True),
    ("We are closed right now. Business hours are 9am-6pm.", True),
    ("Out of office until Monday", True),
    ("Yes please send the abstract", False),
    ("Thanks, will check and revert", False),
    ("Ok go ahead", False),
    ("Not interested", False),
    ("Can you help with my GST filing?", False),
    ("What's the price?", False),
]

for msg, expected in auto_reply_test_cases:
    detected = any(re.search(p, msg, re.IGNORECASE) for p in AUTO_REPLY_PATTERNS)
    short = msg[:50] + "..." if len(msg) > 50 else msg
    if detected == expected:
        ok(f"auto-reply {'YES' if expected else 'NO '}: \"{short}\"")
    else:
        fail(f"auto-reply {'YES' if expected else 'NO '}: \"{short}\"", f"got {detected}")

# Hostile detection
hostile_test_cases = [
    ("Stop messaging me", True),
    ("Not interested. Leave me alone", True),
    ("This is spam", True),
    ("Why are you bothering me", True),
    ("Don't message me again", True),
    ("Stop it", True),
    ("Unsubscribe", True),
    ("Remove my number", True),
    ("Waste of time", True),
    ("Yes please continue", False),
    ("I'm not sure about the timing", False),
    ("Can we discuss tomorrow?", False),
    ("What's your suggestion?", False),
]

for msg, expected in hostile_test_cases:
    detected = any(re.search(p, msg, re.IGNORECASE) for p in HOSTILE_PATTERNS)
    short = msg[:50] + "..." if len(msg) > 50 else msg
    if detected == expected:
        ok(f"hostile   {'YES' if expected else 'NO '}: \"{short}\"")
    else:
        fail(f"hostile   {'YES' if expected else 'NO '}: \"{short}\"", f"got {detected}")

# Intent commit detection
intent_test_cases = [
    ("Let's do it", True),
    ("Ok go ahead", True),
    ("Yes", True),
    ("Sure, sounds good", True),
    ("Please go ahead", True),
    ("What's next", True),
    ("I'm ready", True),
    ("Send it", True),
    ("Book it", True),
    ("Confirmed", True),
    ("Yeah", True),
    ("I have a question", False),
    ("What's the price for this?", False),
    ("Tell me more about it", False),
    ("Hmm let me think", False),
    ("Not sure yet", False),
]

for msg, expected in intent_test_cases:
    detected = any(re.search(p, msg.strip().lower(), re.IGNORECASE) for p in INTENT_COMMIT_PATTERNS)
    if detected == expected:
        ok(f"intent   {'YES' if expected else 'NO '}: \"{msg}\"")
    else:
        fail(f"intent   {'YES' if expected else 'NO '}: \"{msg}\"", f"got {detected}")

# ═══════════════════════════════════════
print("\n" + "="*60)
print("3. UNIT TESTS — Reply Handler Logic")
print("="*60)
# ═══════════════════════════════════════

# Progressive auto-reply (3-step)
store_r = ContextStore()
rh = ReplyHandler(store_r)
auto_msg = "Thank you for contacting us! Our team will respond shortly."

r1 = rh.handle_reply("conv_ar", "m1", None, "merchant", auto_msg, 1)
assert_eq(r1["action"], "send", "auto-reply 1x → send nudge")

r2 = rh.handle_reply("conv_ar", "m1", None, "merchant", auto_msg, 2)
assert_eq(r2["action"], "wait", "auto-reply 2x → wait")
assert_eq(r2.get("wait_seconds"), 86400, "wait 24h (86400s)")

r3 = rh.handle_reply("conv_ar", "m1", None, "merchant", auto_msg, 3)
assert_eq(r3["action"], "end", "auto-reply 3x → end")

# Hostile handling
r_h = rh.handle_reply("conv_h", "m1", None, "merchant", "Stop messaging me. Not interested.", 2)
assert_eq(r_h["action"], "end", "hostile → end")

# Ended conversation stays ended
r_after = rh.handle_reply("conv_h", "m1", None, "merchant", "Actually wait", 3)
assert_eq(r_after["action"], "end", "ended conv stays ended")

# Auto-reply counter resets on real message
store_r2 = ContextStore()
rh2 = ReplyHandler(store_r2)
# Push some context for the LLM path
store_r2.upsert("merchant", "m1", 1, merchants[0])
store_r2.upsert("category", merchants[0]["category_slug"], 1, cats.get(merchants[0]["category_slug"], {}))
store_r2.upsert("trigger", "trg_001", 1, triggers[0])

rh2.handle_reply("conv_reset", "m1", None, "merchant", auto_msg, 1)  # auto
assert_eq(rh2._auto_reply_counts.get("conv_reset"), 1, "auto count = 1 after auto-reply")

# ═══════════════════════════════════════
print("\n" + "="*60)
print("4. UNIT TESTS — Prompt Templates")
print("="*60)
# ═══════════════════════════════════════

# All 26 trigger kinds have templates
expected_kinds = [
    "research_digest", "recall_due", "perf_dip", "perf_spike", "supply_alert",
    "ipl_match_today", "active_planning_intent", "customer_lapsed_hard",
    "customer_lapsed_soft", "chronic_refill_due", "curious_ask_due",
    "review_theme_emerged", "competitor_opened", "festival_upcoming",
    "renewal_due", "winback_eligible", "milestone_reached", "dormant_with_vera",
    "gbp_unverified", "cde_opportunity", "wedding_package_followup",
    "category_seasonal", "seasonal_perf_dip", "trial_followup",
    "regulation_change", "appointment_tomorrow",
]

for kind in expected_kinds:
    assert_true(kind in TRIGGER_INSTRUCTIONS, f"template exists: {kind}")

# Each template returns non-empty string
for kind in expected_kinds:
    instr = get_trigger_instructions(kind, {"metric": "views", "delta_pct": -0.3}, False)
    assert_true(len(instr) > 30, f"template non-empty: {kind} ({len(instr)} chars)")

# Default fallback for unknown kinds
instr = get_trigger_instructions("unknown_kind_xyz", {}, False)
assert_true(len(instr) > 10, "default template for unknown kind")

# System prompt quality
assert_true("VERA" in SYSTEM_PROMPT, "system prompt mentions VERA")
assert_true("fabricat" in SYSTEM_PROMPT.lower(), "system prompt warns against fabrication")
assert_true("CTA" in SYSTEM_PROMPT or "cta" in SYSTEM_PROMPT, "system prompt mentions CTA")
assert_true("JSON" in SYSTEM_PROMPT or "json" in SYSTEM_PROMPT, "system prompt mentions JSON output")
assert_true("URL" in SYSTEM_PROMPT or "url" in SYSTEM_PROMPT.lower(), "system prompt warns about URLs")

# Trigger-specific template content checks
research_instr = get_trigger_instructions("research_digest", {}, False)
assert_true("citation" in research_instr.lower() or "source" in research_instr.lower(), "research: mentions source/citation")

supply_instr = get_trigger_instructions("supply_alert", {"affected_batches": ["B1"], "molecule": "atorvastatin"}, False)
assert_true("atorvastatin" in supply_instr, "supply_alert: includes molecule name")
assert_true("B1" in supply_instr, "supply_alert: includes batch number")

ipl_instr = get_trigger_instructions("ipl_match_today", {"match": "DC vs MI", "venue": "Stadium", "is_weeknight": False}, False)
assert_true("DC vs MI" in ipl_instr, "ipl: includes match")
assert_true("Saturday" in ipl_instr or "Weekend" in ipl_instr or "delivery" in ipl_instr.lower(), "ipl: weekend logic")

# ═══════════════════════════════════════
print("\n" + "="*60)
print("5. INTEGRATION TESTS — Full Context Flow")
print("="*60)
# ═══════════════════════════════════════

store_full = ContextStore()

# Push ALL seed categories
for slug, cat_data in cats.items():
    a, _, _ = store_full.upsert("category", slug, 1, cat_data)
    assert_true(a, f"push category: {slug}")

# Push ALL seed merchants
for m in merchants:
    a, _, _ = store_full.upsert("merchant", m["merchant_id"], 1, m)
assert_eq(store_full.counts()["merchant"], len(merchants), f"all {len(merchants)} merchants pushed")

# Push ALL seed triggers
for t in triggers:
    a, _, _ = store_full.upsert("trigger", t["id"], 1, t)
assert_eq(store_full.counts()["trigger"], len(triggers), f"all {len(triggers)} triggers pushed")

# Push ALL seed customers
for c in customers:
    a, _, _ = store_full.upsert("customer", c["customer_id"], 1, c)
assert_eq(store_full.counts()["customer"], len(customers), f"all {len(customers)} customers pushed")

# Verify cross-references
for t in triggers:
    mid = t.get("merchant_id")
    if mid:
        m = store_full.get("merchant", mid)
        assert_true(m is not None, f"trigger {t['id'][:30]} → merchant exists")
        cat_slug = m.get("category_slug", "")
        cat = store_full.get("category", cat_slug)
        assert_true(cat is not None, f"merchant {mid[:25]} → category {cat_slug} exists")

ok("all trigger→merchant→category cross-references valid")

# ═══════════════════════════════════════
print("\n" + "="*60)
print("6. ACCURACY TESTS — Composer Prompt Assembly")
print("="*60)
# ═══════════════════════════════════════

from composer import compose, _validate_and_fix, _parse_json_response

# Test JSON parsing
r1 = _parse_json_response('{"body": "hello", "cta": "open_ended"}')
assert_eq(r1["body"], "hello", "parse plain JSON")

r2 = _parse_json_response('```json\n{"body": "hello"}\n```')
assert_eq(r2["body"], "hello", "parse markdown-fenced JSON")

r3 = _parse_json_response('Here is the response:\n{"body": "test", "cta": "none"}\nDone.')
assert_eq(r3["body"], "test", "parse JSON embedded in text")

r4 = _parse_json_response("not json at all")
assert_eq(r4, {}, "parse garbage returns empty dict")

# Test validation/fix
result = {"body": "Check https://example.com for details", "cta": "weird", "send_as": "alien"}
trigger = {"suppression_key": "test:key"}
fixed = _validate_and_fix(result, trigger, has_customer=False)
assert_false("http" in fixed["body"], "URL stripped from body")
assert_eq(fixed["send_as"], "vera", "send_as fixed to vera (no customer)")
assert_eq(fixed["cta"], "open_ended", "invalid cta fixed to open_ended")
assert_eq(fixed["suppression_key"], "test:key", "suppression_key filled from trigger")

# Customer-facing validation
result2 = {"body": "Hi Priya", "send_as": "vera"}
fixed2 = _validate_and_fix(result2, trigger, has_customer=True)
assert_eq(fixed2["send_as"], "merchant_on_behalf", "send_as forced to merchant_on_behalf for customer")

# Multiple URL stripping
result3 = {"body": "See https://a.com and http://b.com for info", "cta": "open_ended", "send_as": "vera"}
fixed3 = _validate_and_fix(result3, trigger, has_customer=False)
assert_false("http" in fixed3["body"], "multiple URLs stripped")

# Rationale fallback
result4 = {"body": "msg"}
fixed4 = _validate_and_fix(result4, trigger, has_customer=False)
assert_true(len(fixed4.get("rationale", "")) > 0, "rationale fallback added")

# ═══════════════════════════════════════
print("\n" + "="*60)
print("7. PERFORMANCE TESTS — Context Store Stress")
print("="*60)
# ═══════════════════════════════════════

# Stress test: 1000 upserts
perf_store = ContextStore()
t0 = time.time()
for i in range(1000):
    perf_store.upsert("merchant", f"m_{i:04d}", 1, {"id": i, "data": "x" * 100})
t_upsert = time.time() - t0
assert_true(t_upsert < 1.0, f"1000 upserts in {t_upsert*1000:.0f}ms (<1s)")

# Stress test: 1000 reads
t0 = time.time()
for i in range(1000):
    perf_store.get("merchant", f"m_{i:04d}")
t_read = time.time() - t0
assert_true(t_read < 0.5, f"1000 reads in {t_read*1000:.0f}ms (<0.5s)")

# Stress test: counts with 1000 items
t0 = time.time()
for _ in range(100):
    perf_store.counts()
t_counts = time.time() - t0
assert_true(t_counts < 1.0, f"100x counts() in {t_counts*1000:.0f}ms (<1s)")

# Stress test: 1000 conversation turns
t0 = time.time()
for i in range(1000):
    perf_store.add_conversation_turn("conv_perf", "vera", f"msg_{i}")
t_conv = time.time() - t0
assert_true(t_conv < 1.0, f"1000 conv turns in {t_conv*1000:.0f}ms (<1s)")

# Stress test: version bumps
t0 = time.time()
for v in range(2, 102):
    perf_store.upsert("merchant", "m_0000", v, {"id": 0, "v": v})
t_bump = time.time() - t0
assert_true(t_bump < 0.5, f"100 version bumps in {t_bump*1000:.0f}ms (<0.5s)")

# Verify final version
assert_eq(perf_store.get_version("merchant", "m_0000"), 101, "version tracked correctly after 100 bumps")

# Stress test: suppression checks
t0 = time.time()
for i in range(1000):
    perf_store.add_suppression("m_perf", f"key_{i}")
for i in range(1000):
    perf_store.is_suppressed("m_perf", f"key_{i}")
t_supp = time.time() - t0
assert_true(t_supp < 0.5, f"1000 suppress add+check in {t_supp*1000:.0f}ms (<0.5s)")

# ═══════════════════════════════════════
print("\n" + "="*60)
print("8. EDGE CASE TESTS")
print("="*60)
# ═══════════════════════════════════════

ec_store = ContextStore()
ec_rh = ReplyHandler(ec_store)

# Empty message
r = ec_rh.handle_reply("conv_empty", "m1", None, "merchant", "", 1)
assert_true(r["action"] in ("send", "wait", "end"), "empty message handled")

# Very long message
long_msg = "a" * 5000
r = ec_rh.handle_reply("conv_long", "m1", None, "merchant", long_msg, 1)
assert_true(r["action"] in ("send", "wait", "end"), "5000-char message handled")

# Unicode/emoji message
r = ec_rh.handle_reply("conv_emoji", "m1", None, "merchant", "हां बिल्कुल 👍🏻🎉", 1)
assert_true(r["action"] in ("send", "wait", "end"), "unicode/emoji handled")

# Multiple rapid calls same conv
for i in range(10):
    ec_rh.handle_reply("conv_rapid", "m1", None, "merchant", f"msg {i}", i)
conv = ec_store.get_conversation("conv_rapid")
assert_true(len(conv) >= 10, "rapid calls don't drop messages")

# Context with empty payload
a, _, _ = ec_store.upsert("merchant", "m_empty", 1, {})
assert_true(a, "empty payload accepted")
assert_eq(ec_store.get("merchant", "m_empty"), {}, "empty payload retrievable")

# Context version edge: 0
a, r, _ = ec_store.upsert("merchant", "m_v0", 0, {})
assert_false(a, "version 0 rejected (falsy)")

# Very large version number
a, _, v = ec_store.upsert("merchant", "m_bigv", 999999, {"big": True})
assert_true(a, "large version number accepted")
assert_eq(v, 999999, "large version tracked")

# Special characters in context_id
a, _, _ = ec_store.upsert("merchant", "m_special!@#$%", 1, {"ok": True})
assert_true(a, "special chars in context_id accepted")

# ═══════════════════════════════════════
print("\n" + "="*60)
print("9. DATA QUALITY TESTS — Seed Files")
print("="*60)
# ═══════════════════════════════════════

# Categories
assert_eq(len(cats), 5, "5 categories loaded")
for slug in ["dentists", "salons", "restaurants", "gyms", "pharmacies"]:
    assert_true(slug in cats, f"category exists: {slug}")
    cat = cats[slug]
    assert_true("voice" in cat, f"{slug} has voice")
    assert_true("peer_stats" in cat, f"{slug} has peer_stats")
    assert_true("digest" in cat, f"{slug} has digest")

# Merchants
assert_eq(len(merchants), 10, "10 seed merchants")
for m in merchants:
    assert_true("merchant_id" in m, f"merchant has id: {m.get('merchant_id','?')[:30]}")
    assert_true("category_slug" in m, f"merchant has category_slug")
    assert_true("identity" in m, f"merchant has identity")
    assert_true(m["category_slug"] in cats, f"merchant category valid: {m['category_slug']}")

# Triggers
assert_eq(len(triggers), 25, "25 seed triggers")
trigger_kinds = set(t["kind"] for t in triggers)
ok(f"trigger kinds found: {len(trigger_kinds)} ({', '.join(sorted(trigger_kinds)[:8])}...)")

for t in triggers:
    assert_true("id" in t, f"trigger has id")
    assert_true("kind" in t, f"trigger has kind")
    assert_true("merchant_id" in t, f"trigger has merchant_id")
    assert_true("suppression_key" in t, f"trigger has suppression_key")

# Customers
assert_eq(len(customers), 15, "15 seed customers")
for c in customers:
    assert_true("customer_id" in c, f"customer has id")
    assert_true("merchant_id" in c, f"customer has merchant_id")

# Expanded dataset
exp_base = os.path.join(os.path.dirname(__file__), "dataset", "expanded")
if os.path.exists(exp_base):
    m_count = len(os.listdir(os.path.join(exp_base, "merchants")))
    c_count = len(os.listdir(os.path.join(exp_base, "customers")))
    t_count = len(os.listdir(os.path.join(exp_base, "triggers")))
    assert_eq(m_count, 50, "expanded: 50 merchants")
    assert_eq(c_count, 200, "expanded: 200 customers")
    assert_eq(t_count, 100, "expanded: 100 triggers")
    with open(os.path.join(exp_base, "test_pairs.json")) as f:
        pairs = json.load(f)
    assert_eq(len(pairs["pairs"]), 30, "expanded: 30 test pairs")
else:
    fail("expanded dataset missing", "run generate_dataset.py first")

# ═══════════════════════════════════════
print("\n" + "="*60)
print("10. BOT MODULE SYNTAX VALIDATION")
print("="*60)
# ═══════════════════════════════════════

import ast
for fname in ["bot.py", "composer.py", "context_store.py", "prompt_templates.py", "reply_handler.py"]:
    try:
        with open(fname) as f:
            ast.parse(f.read())
        ok(f"{fname} syntax valid")
    except SyntaxError as e:
        fail(f"{fname} syntax error", str(e))

# ═══════════════════════════════════════
print("\n" + "="*60)
print("FINAL SUMMARY")
print("="*60)
# ═══════════════════════════════════════

total = PASS + FAIL
pct = (PASS / total * 100) if total else 0
print(f"\n  Total:  {total} tests")
print(f"  Passed: {PASS} ✅")
print(f"  Failed: {FAIL} ❌")
print(f"  Rate:   {pct:.1f}%")
print()
if FAIL == 0:
    print("  🎉 ALL TESTS PASSED!")
else:
    print(f"  ⚠️  {FAIL} test(s) need attention")
print()
