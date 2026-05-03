# VERA Bot — Render Deployment Architecture Diagram

**Last Updated**: May 3, 2026

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         VERA Bot System                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Merchant/Customer Request                                      │
│           ↓                                                      │
│  ┌────────────────────────────────────────────────────────┐    │
│  │ FastAPI Application (bot.py)                           │    │
│  │ ├─ GET /v1/healthz        → 200 OK                    │    │
│  │ ├─ GET /v1/metadata       → Service info             │    │
│  │ ├─ POST /v1/context       → Store contexts           │    │
│  │ ├─ POST /v1/tick          → Compose message          │    │
│  │ └─ POST /v1/reply         → Handle reply             │    │
│  └────────────────────────────────────────────────────────┘    │
│           ↓                                                      │
│  ┌────────────────────────────────────────────────────────┐    │
│  │ 4-Context Composition Pipeline                         │    │
│  │ ├─ composer.py                                         │    │
│  │ │  ├─ Route to trigger-specific prompt                │    │
│  │ │  ├─ Call LLM provider (Gemini/OpenAI/etc)          │    │
│  │ │  ├─ Parse JSON response                             │    │
│  │ │  └─ Validate & fix output                           │    │
│  │ ├─ prompt_templates.py                                │    │
│  │ │  ├─ 21 trigger-specific templates                   │    │
│  │ │  └─ Category-aware vocabulary                       │    │
│  │ ├─ reply_handler.py                                   │    │
│  │ │  ├─ Auto-reply detection                            │    │
│  │ │  ├─ Hostile/opt-out detection                       │    │
│  │ │  └─ Intent transition detection                     │    │
│  │ └─ context_store.py                                   │    │
│  │    └─ Version-based conflict resolution               │    │
│  └────────────────────────────────────────────────────────┘    │
│           ↓                                                      │
│  ┌────────────────────────────────────────────────────────┐    │
│  │ LLM Provider Selection (via urllib)                    │    │
│  │ ┌──────────────────────────────────────────────────┐  │    │
│  │ │ LLM_PROVIDER = gemini (default)                 │  │    │
│  │ │ ├─ Gemini API (Google, free tier)             │  │    │
│  │ │ ├─ OpenAI API (GPT-4o-mini)                   │  │    │
│  │ │ ├─ Anthropic API (Claude 3.5)                 │  │    │
│  │ │ └─ DeepSeek API (DeepSeek Chat)               │  │    │
│  │ └──────────────────────────────────────────────────┘  │    │
│  └────────────────────────────────────────────────────────┘    │
│           ↓                                                      │
│  Composed Message Response                                      │
│                                                                 │
│  Background Service:                                            │
│  └─ Keep-Alive Thread                                           │
│     └─ Pings /v1/healthz every 10 minutes                      │
│        └─ Prevents free tier 15-minute sleep                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Deployment Architecture (Render)

```
┌──────────────────────────────────────────────────────────────────┐
│                         Render.com                               │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ Web Service: vera-bot                                      │ │
│  │ ├─ Runtime: Python 3.11                                   │ │
│  │ ├─ Region: Virginia (default, free tier)                 │ │
│  │ ├─ Memory: 0.5 GB (shared)                               │ │
│  │ ├─ CPU: Shared                                           │ │
│  │ ├─ Plan: Free ($0/month)                                 │ │
│  │ └─ Hours: 750/month max                                  │ │
│  └────────────────────────────────────────────────────────────┘ │
│           ↓                                                      │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ Build Process                                              │ │
│  │ ├─ Clone from GitHub (main branch)                       │ │
│  │ ├─ Install dependencies: pip install -r requirements.txt │ │
│  │ └─ ~20 seconds                                           │ │
│  └────────────────────────────────────────────────────────────┘ │
│           ↓                                                      │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ Startup Command                                            │ │
│  │ └─ uvicorn bot:app --host 0.0.0.0 --port $PORT         │ │
│  │    └─ ~15-20 seconds                                     │ │
│  └────────────────────────────────────────────────────────────┘ │
│           ↓                                                      │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ Health Check                                               │ │
│  │ ├─ Endpoint: /v1/healthz                                 │ │
│  │ ├─ Timeout: 1 minute                                     │ │
│  │ ├─ Interval: 10 seconds                                  │ │
│  │ └─ Success → Service live                                │ │
│  └────────────────────────────────────────────────────────────┘ │
│           ↓                                                      │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ Environment & Secrets                                      │ │
│  │ ├─ LLM_PROVIDER: gemini                                  │ │
│  │ ├─ LLM_MODEL: gemini-2.0-flash                          │ │
│  │ ├─ PYTHON_VERSION: 3.11                                 │ │
│  │ └─ GEMINI_API_KEY: *** (set manually)                   │ │
│  └────────────────────────────────────────────────────────────┘ │
│           ↓                                                      │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ Running Service                                            │ │
│  │ ├─ URL: https://vera-bot-<random-id>.onrender.com       │ │
│  │ ├─ Status: Running                                        │ │
│  │ ├─ Keep-Alive: Active (pings every 10 min)              │ │
│  │ └─ Inactivity Sleep: 15 minutes (free tier)             │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## Request Flow

```
Client Request
     │
     ↓
┌─────────────────────────────────────────┐
│ HTTP Request (POST /v1/tick)            │
│ {                                       │
│   "category": {...},                    │
│   "merchant": {...},                    │
│   "trigger": {...},                     │
│   "customer": {...} (optional)          │
│ }                                       │
└─────────────────────────────────────────┘
     │
     ↓ (FastAPI routing)
┌─────────────────────────────────────────┐
│ Context Store (context_store.py)        │
│ ├─ Validate inputs                      │
│ ├─ Check versions                       │
│ └─ Store/merge contexts                 │
└─────────────────────────────────────────┘
     │
     ↓ (compose() called)
┌─────────────────────────────────────────┐
│ Prompt Template Selection               │
│ ├─ Get trigger kind (e.g., "perf_dip") │
│ ├─ Get category vocab                  │
│ └─ Build system + user prompts          │
└─────────────────────────────────────────┘
     │
     ↓ (_call_llm())
┌─────────────────────────────────────────┐
│ LLM API Call (via urllib)               │
│ ├─ Build JSON request                   │
│ ├─ Set temperature: 0.15                │
│ ├─ Timeout: 25 seconds                  │
│ └─ POST to LLM endpoint                 │
└─────────────────────────────────────────┘
     │
     ↓ (LLM processes)
     │ (2-5 seconds typical)
     │
     ↓ (Response received)
┌─────────────────────────────────────────┐
│ Response Parsing                        │
│ ├─ Extract JSON                         │
│ ├─ Handle markdown fences               │
│ └─ Return structured response           │
└─────────────────────────────────────────┘
     │
     ↓
┌─────────────────────────────────────────┐
│ Post-LLM Validation (_validate_and_fix) │
│ ├─ Remove URLs (Meta rejection)         │
│ ├─ Normalize CTA values                 │
│ ├─ Enforce send_as format               │
│ └─ Check for repetition                 │
└─────────────────────────────────────────┘
     │
     ↓
┌─────────────────────────────────────────┐
│ HTTP Response (200 OK)                  │
│ {                                       │
│   "body": "...",                        │
│   "send_as": "merchant_on_behalf",      │
│   "cta": "binary_yes_no",               │
│   "suppression_key": "...",             │
│   "debug_info": {...}                   │
│ }                                       │
└─────────────────────────────────────────┘
     │
     ↓
Client receives composed message
```

---

## Deployment Timeline

```
Time    Event
────    ─────────────────────────────────────────────────────────
0:00    $ render deploy --blueprint
        └─ Render CLI parses render.yaml
        
0:05    GitHub clone starts
        └─ vera-bot repository downloaded
        
0:15    Build starts
        ├─ Python 3.11 initialized
        ├─ pip install -r requirements.txt
        │  ├─ fastapi
        │  ├─ uvicorn[standard]
        │  └─ pydantic
        └─ ~20 seconds
        
0:35    Startup command runs
        ├─ uvicorn bot:app --host 0.0.0.0 --port $PORT
        ├─ FastAPI initializes
        ├─ Keep-alive thread starts
        └─ ~15-20 seconds
        
0:55    Health check passes
        ├─ GET /v1/healthz → 200 OK
        └─ Service marked "Running"
        
1:00    ✅ DEPLOYMENT COMPLETE
        ├─ Service live at https://vera-bot-<id>.onrender.com
        ├─ Ready to receive requests
        └─ Awaiting API key secret setup
        
1:05    $ render secret set --service vera-bot GEMINI_API_KEY "..."
        └─ Service restarts with secret
        
1:15    ✅ FULLY OPERATIONAL
        └─ Ready for production traffic
```

---

## LLM Integration Flow

```
┌──────────────────────┐
│  Environment Check   │
│  LLM_PROVIDER: ?     │
│  LLM_API_KEY: ?      │
│  LLM_MODEL: ?        │
└──────────────────────┘
         │
         ↓
    ┌─────────────────────────────────────┐
    │ Provider Router                     │
    ├─────────────────────────────────────┤
    │ if provider == "gemini":            │
    │   model = "gemini-2.0-flash"        │
    │   endpoint = Google API v1beta      │
    │   key = GEMINI_API_KEY              │
    ├─────────────────────────────────────┤
    │ elif provider == "openai":          │
    │   model = "gpt-4o-mini"             │
    │   endpoint = OpenAI v1              │
    │   key = OPENAI_API_KEY              │
    ├─────────────────────────────────────┤
    │ elif provider == "anthropic":       │
    │   model = "claude-3-5-sonnet"       │
    │   endpoint = Anthropic v1           │
    │   key = ANTHROPIC_API_KEY           │
    ├─────────────────────────────────────┤
    │ elif provider == "deepseek":        │
    │   model = "deepseek-chat"           │
    │   endpoint = DeepSeek v1            │
    │   key = DEEPSEEK_API_KEY            │
    └─────────────────────────────────────┘
         │
         ↓
    ┌─────────────────────────────────────┐
    │ Build Request                       │
    ├─────────────────────────────────────┤
    │ {                                   │
    │   "prompt": user_prompt,            │
    │   "system": system_prompt,          │
    │   "temperature": 0.15,              │
    │   "max_tokens": 2000,               │
    │   "timeout": 25                     │
    │ }                                   │
    └─────────────────────────────────────┘
         │
         ↓
    ┌─────────────────────────────────────┐
    │ HTTP Call (via urllib)              │
    │ POST to LLM endpoint                │
    │ + Authorization headers             │
    │ + JSON body                         │
    └─────────────────────────────────────┘
         │
         ├─ 2-5 seconds (LLM processing)
         │
         ↓
    ┌─────────────────────────────────────┐
    │ Parse Response                      │
    ├─────────────────────────────────────┤
    │ Extract model output                │
    │ Strip markdown if present           │
    │ Extract JSON structure              │
    └─────────────────────────────────────┘
         │
         ↓
    Composed Message Ready
```

---

## File Structure for Deployment

```
vera-bot/
├── .git/                          # Git repository
├── .gitignore                     # Git ignore rules
├── Procfile                       # Heroku-style config
├── render.yaml                    # ✅ Render Blueprint
│
├── requirements.txt               # Python dependencies
│   ├─ fastapi>=0.104.0
│   ├─ uvicorn[standard]>=0.24.0
│   └─ pydantic>=2.0.0
│
├── bot.py                         # ✅ Main application (527 lines)
│   ├─ FastAPI app
│   ├─ 5 endpoints
│   ├─ HTTP server fallback
│   └─ Keep-alive thread
│
├── composer.py                    # ✅ LLM composition (370 lines)
│   ├─ Multi-provider routing
│   ├─ Prompt templating
│   └─ Response validation
│
├── reply_handler.py               # Intent detection (247 lines)
├── prompt_templates.py            # 21 templates (405 lines)
├── context_store.py               # Context management (120 lines)
├── judge_simulator.py             # Test harness (962 lines)
├── test_all.py                    # Unit tests (582 lines)
│
├── dataset/                       # Training/test data
│   ├─ customers_seed.json
│   ├─ merchants_seed.json
│   ├─ triggers_seed.json
│   └─ expanded/
│       ├─ customers/
│       ├─ merchants/
│       ├─ triggers/
│       └─ categories/
│
├── examples/                      # Documentation
│   ├─ api-call-examples.md
│   └─ case-studies.md
│
├── README.md                      # Project overview
├── ANALYSIS_SUMMARY.md            # ✅ This analysis
├── DEPLOYMENT_ANALYSIS.md         # ✅ Deep dive (12 sections)
├── RENDER_QUICKSTART.md           # ✅ 5-min deployment
├── challenge-brief.md             # Challenge spec
├── challenge-testing-brief.md     # Testing rubric
├── engagement-design.md           # Design doc
└── engagement-research.md         # Research notes
```

---

## Monitoring & Logs

```
┌─────────────────────────────────────────┐
│ Render Dashboard                        │
│ https://dashboard.render.com            │
├─────────────────────────────────────────┤
│ ┌─────────────────────────────────────┐ │
│ │ vera-bot (Web Service)              │ │
│ ├─────────────────────────────────────┤ │
│ │ Status: ✅ Running                  │ │
│ │ Region: Virginia (US)               │ │
│ │ Memory: 150-200 MB used             │ │
│ │ Uptime: 99.9%                       │ │
│ │ CPU: Minimal (I/O bound)            │ │
│ │ Last Deploy: 2026-05-03 14:30 UTC   │ │
│ └─────────────────────────────────────┘ │
│ ┌─────────────────────────────────────┐ │
│ │ Logs (Real-time)                    │ │
│ ├─────────────────────────────────────┤ │
│ │ [INFO] Started server process       │ │
│ │ [INFO] Keep-alive thread started    │ │
│ │ [INFO] Listening on 0.0.0.0:10000   │ │
│ │ [DEBUG] Keep-alive ping OK          │ │
│ │ [200] GET /v1/healthz               │ │
│ │ [200] POST /v1/context              │ │
│ │ [200] POST /v1/tick (2.3s)          │ │
│ └─────────────────────────────────────┘ │
│ ┌─────────────────────────────────────┐ │
│ │ Metrics                             │ │
│ ├─────────────────────────────────────┤ │
│ │ Requests/min: 120                   │ │
│ │ Avg latency: 2.5s                   │ │
│ │ Error rate: 0.1%                    │ │
│ │ 5xx errors: 0                       │ │
│ └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘

CLI Commands:
$ render service logs --name vera-bot
$ render service logs --name vera-bot --follow  (stream)
$ render service logs --name vera-bot --tail 100
$ render service get --name vera-bot
$ render service restart --name vera-bot
$ render env list --service vera-bot
```

---

## Troubleshooting Decision Tree

```
Is service deployed?
├─ NO → Follow RENDER_QUICKSTART.md
│
└─ YES
   ├─ Is health check passing?
   │  ├─ NO → Wait 30s, then check logs
   │  │      $ render service logs --name vera-bot
   │  │      └─ Look for startup errors
   │  │
   │  └─ YES
   │     ├─ Is GEMINI_API_KEY set?
   │     │  ├─ NO → Set secret:
   │     │  │      $ render secret set --service vera-bot \
   │     │  │        GEMINI_API_KEY "your-key"
   │     │  │
   │     │  └─ YES
   │     │     ├─ Is response timeout?
   │     │     │  └─ Normal: 2-5s for LLM calls
   │     │     │
   │     │     └─ Is service sleeping?
   │     │        ├─ Check last activity log
   │     │        ├─ Free tier sleeps after 15 min
   │     │        └─ Keep-alive should help
   │
   └─ All checks passed → Service operational ✅
```

---

## Scale-Up Path (Future)

```
Free Tier (Current)
├─ Cost: $0/month
├─ Uptime: ~99% (with keep-alive)
├─ Memory: 0.5 GB shared
├─ Instances: 1
└─ Sleep: Yes (15 min inactivity)

         ↓ When: 1,000+ requests/day

Starter Plan
├─ Cost: $7/month
├─ Uptime: 99.9% (guaranteed)
├─ Memory: 0.5 GB dedicated
├─ Instances: 1
└─ Sleep: No
└─ Auto-restart: Yes

         ↓ When: 10,000+ requests/day

Standard Plan
├─ Cost: $12/month
├─ Uptime: 99.99%
├─ Memory: 1 GB dedicated
├─ CPU: 0.5 vCPU
└─ Auto-scaling: Up to 3 instances

         ↓ When: 100,000+ requests/day

Professional Plan
├─ Cost: $50+/month
├─ Uptime: 99.99%+
├─ Memory: 8+ GB
├─ CPU: Multiple vCPUs
├─ Auto-scaling: Unlimited
└─ High availability: Yes
```

---

*Diagram generated: 2026-05-03*  
*Repository: https://github.com/Gaggs-daggs/vera-bot*
