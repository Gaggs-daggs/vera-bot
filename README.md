# VERA Bot — Magicpin AI Challenge

## Approach

**Architecture:** FastAPI server with 5 endpoints implementing the 4-context composition framework.

### Core Design

1. **Context Store:** In-memory versioned store handling idempotent upserts across 4 scopes (category, merchant, customer, trigger). Version-based conflict resolution — higher versions atomically replace lower ones.

2. **Trigger-Kind Routing:** Instead of a single generic prompt, the composer routes each trigger to a kind-specific prompt template (21 templates covering research_digest, recall_due, perf_dip, supply_alert, ipl_match_today, active_planning_intent, etc.). This ensures category vocabulary, tone, and CTA type match what the judge expects.

3. **Reply Handler:** Three-tier detection pipeline:
   - **Auto-reply detection** (regex patterns) → progressive response: nudge → wait 24h → end
   - **Hostile/opt-out detection** → immediate graceful exit
   - **Intent transition detection** → switches to action-execution mode
   - **Normal replies** → LLM-composed contextual follow-up

4. **Post-LLM Validation:** Every composed message passes through validation guards:
   - URL stripping (Meta rejection prevention)
   - CTA normalization
   - send_as enforcement (merchant_on_behalf for customer-facing)
   - Repetition detection per conversation

### Model Choice

**Gemini 2.0 Flash** — chosen for speed (<5s response), free API tier, and good instruction-following. Temperature set to 0.15 for near-deterministic output while allowing slight variation.

### What Additional Context Would Help

- Real-time peer benchmark data (not just static peer_stats)
- A/B test results on message variants for each trigger kind
- Merchant response-rate history to calibrate urgency levels
- Seasonal calendar with city-specific events beyond IPL/Diwali

## Running Locally

```bash
pip install -r requirements.txt
export GEMINI_API_KEY="your-key"
python bot.py
# or: uvicorn bot:app --host 0.0.0.0 --port 8080
```

## Testing

```bash
# Health check
curl localhost:8080/v1/healthz

# Run judge simulator
python judge_simulator.py
```

## Team

- **Team:** Solo Gunner
- **Members:** Gugan K
