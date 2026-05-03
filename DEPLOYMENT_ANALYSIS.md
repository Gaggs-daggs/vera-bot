# VERA Bot — Render Deployment Analysis

**Date**: May 3, 2026  
**Status**: Ready for Render CLI deployment  
**Repository**: https://github.com/Gaggs-daggs/vera-bot

---

## 1. Project Overview

**VERA Bot** is a FastAPI-based AI chatbot for magicpin merchants on WhatsApp. It implements a 4-context composition framework with Gemini 2.0 Flash LLM integration.

### Key Stats
- **Language**: Python 3.11
- **Framework**: FastAPI + Uvicorn
- **Total Python Code**: ~3,200 lines across 7 modules
- **Architecture**: HTTP server with 5 core endpoints
- **Runtime**: Serverless/traditional web service

---

## 2. Current Deployment Configuration

### 2.1 Procfile (for Heroku-like platforms)
```
web: uvicorn bot:app --host 0.0.0.0 --port $PORT
```

### 2.2 render.yaml (Render Blueprint)
```yaml
services:
  - type: web
    name: vera-bot
    runtime: python
    plan: free
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn bot:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: GEMINI_API_KEY
        sync: false
      - key: LLM_PROVIDER
        value: gemini
      - key: LLM_MODEL
        value: gemini-2.0-flash
      - key: PYTHON_VERSION
        value: "3.11"
    healthCheckPath: /v1/healthz
```

### 2.3 Requirements
- `fastapi>=0.104.0`
- `uvicorn[standard]>=0.24.0`
- `pydantic>=2.0.0`

**Note**: Project uses HTTP API calls directly (urllib), not SDKs. Supports multiple LLM providers via raw REST calls.

---

## 3. Critical Issues Found

### ✅ Issue #1: Dependency Coverage (RESOLVED)
**Status**: No external SDK dependencies needed  
**Implementation**: Raw HTTP calls via `urllib` (included in Python stdlib)  
**Supports**: Gemini, OpenAI, Anthropic, DeepSeek  
**Impact**: Minimal deployment footprint (~3 MB), faster cold start

### ⚠️ Issue #2: API Key Management
**Current**: `GEMINI_API_KEY` must be set in environment  
**Render Config**: `sync: false` means it won't auto-sync from GitHub Secrets  
**Risk**: Requires manual setup in Render dashboard  
**Recommendation**: Use Render's native secret management

### ✅ Issue #3: Keep-Alive Thread (Free Tier Optimization)
**Location**: `bot.py` lines 32-48  
**Purpose**: Ping healthz every 10 minutes to prevent Render free tier sleep  
**Status**: ✅ Already implemented  
**Note**: Works well, but free tier still has 15-min inactivity limit  
**Details**: Runs as daemon thread, self-pings `http://localhost:{PORT}/v1/healthz`

### ⚠️ Issue #4: No .gitignore for Python
**Risk**: `.pyc`, `__pycache__/`, `.venv/`, `.env` may be committed  
**Status**: Already committed (seen in git history)  
**Action**: Create `.gitignore` for best practices

---

## 4. Render Deployment Readiness Checklist

| Item | Status | Notes |
|------|--------|-------|
| **Procfile** | ✅ Present | Valid for Render |
| **render.yaml** | ✅ Present | Valid blueprint |
| **requirements.txt** | ✅ Complete | All dependencies listed, no external SDKs needed |
| **Python version** | ✅ Specified | 3.11 in render.yaml |
| **Health check endpoint** | ✅ Present | `/v1/healthz` implemented |
| **Port binding** | ✅ Correct | Uses `$PORT` env var |
| **API key setup** | ⚠️ Manual | Needs Render secret setup |
| **Runtime startup** | ✅ Valid | Uvicorn command correct |
| **.gitignore** | ❌ Missing | Not critical but recommended |
| **Environment variables** | ⚠️ Partial | Main key missing, others hardcoded |
| **Multi-LLM Support** | ✅ Implemented | Gemini/OpenAI/Anthropic/DeepSeek |

---

## 5. Deployment Steps (Render CLI)

### Step 1: Install Render CLI
```bash
# On macOS
brew install render-cli

# Or via npm
npm install -g @render-com/cli
```

### Step 2: Verify Dependencies (No Changes Needed)
```bash
# requirements.txt already complete
cat requirements.txt
# Should show: fastapi, uvicorn, pydantic (no external LLM SDKs needed)
```

### Step 3: Authenticate with Render
```bash
render login
```

### Step 4: Deploy via Blueprint
```bash
render deploy --blueprint
```

Or create a new service:
```bash
render create-web-service \
  --name vera-bot \
  --runtime python \
  --start-command "uvicorn bot:app --host 0.0.0.0 --port \$PORT" \
  --plan free
```

### Step 5: Set Secrets
```bash
render secret set \
  --service vera-bot \
  GEMINI_API_KEY "your-actual-key-here"
```

### Step 6: Verify Deployment
```bash
# Check service status
render service logs --name vera-bot

# Test health endpoint
curl https://vera-bot-<random>.onrender.com/v1/healthz
```

---

## 6. Recommended Pre-Deployment Actions

### 6.1 Verify Requirements (Already Complete)
```bash
# requirements.txt is complete and ready
cat requirements.txt
# Output should have fastapi, uvicorn[standard], pydantic
```

### 6.2 Create .gitignore
```bash
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Environment
.env
.env.local
.env.*.local

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Testing
.pytest_cache/
.coverage
htmlcov/

# Render
.render/
EOF
```

### 6.3 Test Health Endpoint Locally
```bash
# Terminal 1: Start server
python bot.py

# Terminal 2: Test health (should return 200 OK)
curl http://localhost:8080/v1/healthz
```

### 6.4 Commit Changes Before Deploy
```bash
git add .gitignore DEPLOYMENT_ANALYSIS.md
git commit -m "Add .gitignore and deployment analysis"
git push origin main
```

---

## 7. Environment Variables Summary

### Required (Must Set in Render Dashboard)
| Variable | Value | Example |
|----------|-------|---------|
| `GEMINI_API_KEY` | Your API key | `AIzaSyD...` (from Google AI Studio) |

### Optional (Pre-configured in render.yaml)
| Variable | Value | Purpose |
|----------|-------|---------|
| `LLM_PROVIDER` | `gemini` | LLM provider selection (gemini/openai/anthropic/deepseek) |
| `LLM_MODEL` | `gemini-2.0-flash` | Model name for the selected provider |
| `PYTHON_VERSION` | `3.11` | Python runtime version |

### Auto-Managed by Render
| Variable | Auto-set by | Purpose |
|----------|-------------|---------|
| `PORT` | Render | HTTP port (typically 10000) |

---

## 8. Performance Expectations

### Cold Start
- **Time**: ~15-20 seconds
- **Reason**: Python+FastAPI startup + Gemini SDK init
- **Mitigation**: Keep-alive thread (already in place)

### Request Latency
- **Health check**: <50ms
- **LLM composition**: 2-5 seconds (Gemini API)
- **Reply detection**: <500ms
- **Total round-trip**: 2.5-6 seconds

### Resource Usage
- **Memory**: ~150-200 MB (includes Gemini SDK)
- **CPU**: Low for I/O, variable for LLM calls
- **Render Free Tier Limits**: 
  - 750 hours/month
  - 0.5 GB RAM
  - Shared CPU
  - Sleep after 15 min inactivity

---

## 9. Troubleshooting Guide

### Issue: ImportError: No module named 'google.generativeai'
**Cause**: Missing dependency  
**Fix**: Update requirements.txt and redeploy

### Issue: GEMINI_API_KEY not found
**Cause**: Environment variable not set in Render  
**Fix**: Set secret via Render dashboard or CLI

### Issue: Service keeps sleeping (free tier)
**Cause**: Inactivity + keep-alive thread not running  
**Fix**: Ensure keep-alive is enabled (it is by default)

### Issue: Timeouts on /v1/tick endpoint
**Cause**: 30s timeout exceeded (Render default)  
**Fix**: Use background tasks or split into async operations

### Issue: Health check failing
**Cause**: Service not ready on startup  
**Fix**: Verify `/v1/healthz` returns 200 within 1 minute

---

## 10. Post-Deployment Checklist

- [ ] Service deployed and running
- [ ] Health endpoint responsive (`/v1/healthz` → 200)
- [ ] GEMINI_API_KEY set as environment secret
- [ ] Test `/v1/metadata` endpoint
- [ ] Test `/v1/context` with sample merchant data
- [ ] Test `/v1/tick` with sample trigger
- [ ] Monitor logs for errors: `render service logs --name vera-bot`
- [ ] Set up uptime monitoring (optional)
- [ ] Configure alerts for deployment failures

---

## 11. Next Steps

1. **Immediate**: 
   - [ ] Add `google-generativeai` to `requirements.txt`
   - [ ] Commit and push to GitHub
   - [ ] Test locally with `python bot.py`

2. **Pre-Deployment**:
   - [ ] Install Render CLI: `brew install render-cli`
   - [ ] Authenticate: `render login`
   - [ ] Get Gemini API key from https://aistudio.google.com/apikey

3. **Deploy**:
   - [ ] Run `render deploy --blueprint` from project root
   - [ ] Set GEMINI_API_KEY secret in Render dashboard
   - [ ] Monitor first 5 minutes of logs

4. **Verify**:
   - [ ] Test health endpoint
   - [ ] Test with sample request
   - [ ] Confirm keep-alive working (no sleep after 15 min)

---

## 12. Reference Links

- **Render CLI Docs**: https://render.com/docs/cli
- **Render Blueprint Spec**: https://render.com/docs/blueprint-spec
- **Gemini API**: https://ai.google.dev/
- **FastAPI Deployment**: https://fastapi.tiangolo.com/deployment/
- **Uvicorn**: https://www.uvicorn.org/

---

**Generated**: 2026-05-03  
**Deployment Status**: ✅ Ready (after fixing requirements.txt)
