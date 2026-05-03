#!/bin/bash
# VERA Bot — Local Test Script
# Usage: bash test_local.sh [port]
# Run this AFTER starting the server with: bash start.sh

PORT=${1:-8080}
BASE="http://localhost:$PORT"
PASS=0
FAIL=0

echo "🧪 VERA Bot — Local Tests"
echo "========================="
echo "Testing: $BASE"
echo ""

# Helper
test_endpoint() {
    local method=$1
    local path=$2
    local data=$3
    local expect=$4
    local desc=$5

    if [ "$method" = "GET" ]; then
        resp=$(curl -s -o /dev/null -w "%{http_code}" "$BASE$path" 2>/dev/null)
    else
        resp=$(curl -s -o /dev/null -w "%{http_code}" -X POST -H "Content-Type: application/json" -d "$data" "$BASE$path" 2>/dev/null)
    fi

    if [ "$resp" = "$expect" ]; then
        echo "  ✅ $desc (HTTP $resp)"
        PASS=$((PASS + 1))
    else
        echo "  ❌ $desc (expected $expect, got $resp)"
        FAIL=$((FAIL + 1))
    fi
}

# 1. Health check
echo "Phase 1: Health & Metadata"
test_endpoint GET /v1/healthz "" 200 "GET /v1/healthz"
test_endpoint GET /v1/metadata "" 200 "GET /v1/metadata"

# Show health response
echo ""
echo "  Health response:"
curl -s "$BASE/v1/healthz" 2>/dev/null | python3 -m json.tool 2>/dev/null || curl -s "$BASE/v1/healthz"
echo ""

# 2. Context push
echo ""
echo "Phase 2: Context Push"

# Push category
test_endpoint POST /v1/context \
    '{"scope":"category","context_id":"dentists","version":1,"payload":{"slug":"dentists","voice":{"tone":"peer_clinical"}}}' \
    200 "Push category (dentists v1)"

# Push merchant
test_endpoint POST /v1/context \
    '{"scope":"merchant","context_id":"m_001","version":1,"payload":{"merchant_id":"m_001","category_slug":"dentists","identity":{"name":"Dr. Meera Dental","owner_first_name":"Meera","city":"Delhi","locality":"Lajpat Nagar","languages":["en","hi"],"verified":true},"performance":{"views":2410,"calls":18,"ctr":0.021},"offers":[{"id":"o1","title":"Dental Cleaning @ ₹299","status":"active"}],"signals":["stale_posts:22d","high_risk_adult_cohort"],"customer_aggregate":{"total_unique_ytd":540,"high_risk_adult_count":124}}}' \
    200 "Push merchant (m_001 v1)"

# Idempotency test (same version)
test_endpoint POST /v1/context \
    '{"scope":"merchant","context_id":"m_001","version":1,"payload":{}}' \
    409 "Idempotency (m_001 v1 re-push → 409)"

# Version bump
test_endpoint POST /v1/context \
    '{"scope":"merchant","context_id":"m_001","version":2,"payload":{"merchant_id":"m_001","category_slug":"dentists","identity":{"name":"Dr. Meera Dental","owner_first_name":"Meera","city":"Delhi","locality":"Lajpat Nagar","languages":["en","hi"],"verified":true},"performance":{"views":2580,"calls":20,"ctr":0.023},"offers":[],"signals":[],"customer_aggregate":{}}}' \
    200 "Version bump (m_001 v2)"

# Push trigger
test_endpoint POST /v1/context \
    '{"scope":"trigger","context_id":"trg_001","version":1,"payload":{"id":"trg_001","kind":"research_digest","source":"external","merchant_id":"m_001","customer_id":null,"payload":{"category":"dentists","top_item_id":"d_jida_fluoride"},"urgency":2,"suppression_key":"research:dentists:2026-W17"}}' \
    200 "Push trigger (trg_001 v1)"

# 3. Tick
echo ""
echo "Phase 3: Tick"
echo "  Tick response:"
curl -s -X POST -H "Content-Type: application/json" \
    -d '{"now":"2026-04-26T10:35:00Z","available_triggers":["trg_001"]}' \
    "$BASE/v1/tick" 2>/dev/null | python3 -m json.tool 2>/dev/null || \
curl -s -X POST -H "Content-Type: application/json" \
    -d '{"now":"2026-04-26T10:35:00Z","available_triggers":["trg_001"]}' \
    "$BASE/v1/tick"
echo ""

# 4. Reply
echo ""
echo "Phase 4: Reply"
echo "  Normal reply:"
curl -s -X POST -H "Content-Type: application/json" \
    -d '{"conversation_id":"conv_test_001","merchant_id":"m_001","from_role":"merchant","message":"Yes please send the abstract","turn_number":2}' \
    "$BASE/v1/reply" 2>/dev/null | python3 -m json.tool 2>/dev/null
echo ""

echo "  Auto-reply:"
curl -s -X POST -H "Content-Type: application/json" \
    -d '{"conversation_id":"conv_test_002","merchant_id":"m_001","from_role":"merchant","message":"Thank you for contacting Dr. Meera Dental Clinic! Our team will respond shortly.","turn_number":2}' \
    "$BASE/v1/reply" 2>/dev/null | python3 -m json.tool 2>/dev/null
echo ""

echo "  Hostile:"
curl -s -X POST -H "Content-Type: application/json" \
    -d '{"conversation_id":"conv_test_003","merchant_id":"m_001","from_role":"merchant","message":"Stop messaging me. Not interested.","turn_number":2}' \
    "$BASE/v1/reply" 2>/dev/null | python3 -m json.tool 2>/dev/null
echo ""

# Health after context push
echo ""
echo "Phase 5: Post-push Health"
curl -s "$BASE/v1/healthz" 2>/dev/null | python3 -m json.tool 2>/dev/null
echo ""

# Summary
echo ""
echo "========================="
echo "Results: $PASS passed, $FAIL failed"
if [ $FAIL -eq 0 ]; then
    echo "🎉 ALL TESTS PASSED!"
else
    echo "⚠️  Some tests failed. Check the output above."
fi
