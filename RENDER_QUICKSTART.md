# 🚀 VERA Bot — Render Deployment Quick Start

**Status**: ✅ Ready to deploy  
**Last Updated**: May 3, 2026

---

## TL;DR — Deploy in 5 Minutes

### Prerequisites
- Render account (https://render.com)
- Gemini API key (https://aistudio.google.com/apikey) — FREE
- Render CLI installed

### Deploy

```bash
# 1. Install Render CLI (if not already installed)
brew install render-cli

# 2. Authenticate
render login

# 3. Deploy from project root
render deploy --blueprint

# 4. Set the API key secret
render secret set --service vera-bot GEMINI_API_KEY "your-key-here"

# 5. View logs
render service logs --name vera-bot

# 6. Test (after ~30 seconds)
curl https://vera-bot-<random>.onrender.com/v1/healthz
```

---

## Project Architecture

### Core Stack
- **Language**: Python 3.11
- **Framework**: FastAPI + Uvicorn
- **LLM Provider**: Gemini 2.0 Flash (configurable)
- **Deployment**: Render (free tier supported)

### Key Features
✅ Multi-LLM support (Gemini, OpenAI, Anthropic, DeepSeek)  
✅ Raw HTTP API calls (no heavy SDKs)  
✅ Keep-alive thread (prevents free tier sleep)  
✅ Health check endpoint (`/v1/healthz`)  
✅ Context-aware message composition  
✅ Reply handler with intent detection  

### 5 Endpoints
```
GET  /v1/healthz       → Health check (200 OK)
GET  /v1/metadata      → Service metadata
POST /v1/context       → Store context (merchant, category, trigger, customer)
POST /v1/tick          → Compose next message
POST /v1/reply         → Handle merchant/customer reply
```

---

## Render Configuration Details

### render.yaml (Blueprint)
- **Service Type**: Web
- **Runtime**: Python 3.11
- **Start Command**: `uvicorn bot:app --host 0.0.0.0 --port $PORT`
- **Build Command**: `pip install -r requirements.txt`
- **Health Check**: `/v1/healthz`
- **Plan**: Free tier

### Requirements
```
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
pydantic>=2.0.0
```

**Note**: No external LLM SDKs needed — uses raw HTTP calls via `urllib` (Python stdlib).

---

## Environment Variables

### Required (Set after deployment)
```
GEMINI_API_KEY=your-api-key-from-aistudio.google.com
```

### Optional (Pre-configured)
```
LLM_PROVIDER=gemini          # Options: gemini, openai, anthropic, deepseek
LLM_MODEL=gemini-2.0-flash   # Model name
PYTHON_VERSION=3.11          # Python version
```

### Auto-Managed by Render
```
PORT=10000  # Render assigns dynamically
```

---

## Get Gemini API Key (Free)

1. Go to https://aistudio.google.com/apikey
2. Click "Create API key"
3. Copy the key
4. Paste into Render environment secrets

**Limitations**: 15 requests per minute, but more than enough for typical merchant bot usage.

---

## Testing

### Local Testing (Before Deploy)
```bash
# Start server
python bot.py

# In another terminal
# Test health
curl http://localhost:8080/v1/healthz

# Test metadata
curl http://localhost:8080/v1/metadata
```

### Remote Testing (After Deploy)
```bash
# Replace <random> with your actual service URL
ENDPOINT="https://vera-bot-<random>.onrender.com"

# Health check
curl $ENDPOINT/v1/healthz

# Metadata
curl $ENDPOINT/v1/metadata

# Compose message (sample)
curl -X POST $ENDPOINT/v1/tick \
  -H "Content-Type: application/json" \
  -d @sample_payload.json
```

---

## Performance Expectations

### Cold Start
- **Time**: 15-20 seconds
- **Reason**: Python + FastAPI + Gemini SDK initialization

### Request Latency
- **Health check**: <50ms (instant)
- **LLM composition**: 2-5s (Gemini API)
- **Total round-trip**: 2-6s

### Resource Usage
- **Memory**: ~150-200 MB
- **CPU**: Low for I/O, variable for LLM
- **Render Free Tier**: 750 hours/month, 0.5GB RAM, shared CPU

### Keep-Alive
- Pings healthz every 10 minutes
- Prevents 15-minute inactivity sleep
- Runs as background daemon thread

---

## Troubleshooting

### Service won't start
- Check logs: `render service logs --name vera-bot`
- Verify Python version: 3.11+
- Check Procfile format

### ImportError: No module named 'X'
- Run: `pip install -r requirements.txt` locally
- Verify requirements.txt syntax

### GEMINI_API_KEY not found
- Set secret: `render secret set --service vera-bot GEMINI_API_KEY "your-key"`
- Verify it's set: `render env list --service vera-bot`

### Service keeps sleeping
- Keep-alive should prevent this
- Check that `/v1/healthz` is returning 200
- Free tier still has 15-min inactivity limit

### Timeouts on long-running endpoints
- `/v1/tick` has 25-second LLM timeout
- Render default is 30 seconds
- Should be fine, but monitor if issues arise

### Health check failing
- Service needs time to start (up to 20 seconds)
- Check if FastAPI is binding to $PORT
- Verify requirements installed: `pip install -r requirements.txt`

---

## Monitoring

### View Logs
```bash
render service logs --name vera-bot
render service logs --name vera-bot --tail 50  # Last 50 lines
render service logs --name vera-bot --follow   # Stream in real-time
```

### Check Service Status
```bash
render service list
render service get --name vera-bot
```

### Manual Restart
```bash
render service restart --name vera-bot
```

---

## Next Steps

1. **Deploy**: `render deploy --blueprint`
2. **Set Secret**: `render secret set --service vera-bot GEMINI_API_KEY "key"`
3. **Test**: `curl https://vera-bot-<id>.onrender.com/v1/healthz`
4. **Monitor**: `render service logs --name vera-bot --follow`
5. **Scale**: Upgrade to paid plan if needed (currently on free)

---

## Useful Links

- **Render Dashboard**: https://dashboard.render.com
- **Render Docs**: https://render.com/docs
- **Render CLI Docs**: https://render.com/docs/cli
- **Gemini API**: https://ai.google.dev/
- **FastAPI**: https://fastapi.tiangolo.com/
- **Uvicorn**: https://www.uvicorn.org/

---

**Need help?**  
Check `DEPLOYMENT_ANALYSIS.md` for detailed architecture and troubleshooting.

---

*Generated: 2026-05-03 | Repository: https://github.com/Gaggs-daggs/vera-bot*
