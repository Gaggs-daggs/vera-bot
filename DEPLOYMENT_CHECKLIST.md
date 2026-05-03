# 📋 VERA Bot — Render Deployment Checklist

**Project**: VERA Bot (Merchant AI Assistant)  
**Status**: ✅ READY FOR DEPLOYMENT  
**Date**: May 3, 2026

---

## Pre-Deployment Checklist (5 minutes)

- [ ] **Code is committed**
  ```bash
  git status  # Should show "nothing to commit"
  ```

- [ ] **Repository is clean**
  ```bash
  git log --oneline | head -3  # Latest commits visible
  ```

- [ ] **Gemini API key obtained (FREE)**
  - Visit: https://aistudio.google.com/apikey
  - Click "Create API key"
  - Copy the key (keep it safe)

- [ ] **Render CLI installed**
  ```bash
  brew install render-cli
  # Or: npm install -g @render-com/cli
  ```

- [ ] **Render account created**
  - Sign up: https://render.com
  - Verify email

- [ ] **Local test completed (optional)**
  ```bash
  python bot.py
  # In another terminal:
  curl http://localhost:8080/v1/healthz
  # Should return: {"status": "ok"}
  ```

---

## Deployment Steps (3 minutes)

### Step 1: Authenticate with Render
```bash
render login
# Follow prompts to log in
```
**Expected**: CLI shows "Logged in as: [your-email]"

### Step 2: Deploy via Blueprint
```bash
cd /Users/gugank/Downloads/magicpin-ai-challenge
render deploy --blueprint
```
**Expected Output**:
```
🚀 Deploying via blueprint...
✓ vera-bot created
✓ Build started
✓ Service deployed
```

**What happens**:
- [ ] Repository cloned from GitHub
- [ ] Dependencies installed (pip install -r requirements.txt)
- [ ] FastAPI server starts
- [ ] Health check passes
- [ ] Service goes live

**Time**: 2-3 minutes

### Step 3: Set API Key Secret
```bash
render secret set --service vera-bot GEMINI_API_KEY "your-api-key-here"
```
Replace `your-api-key-here` with actual key from Google AI Studio

**Expected**: "Secret set successfully"

**What happens**:
- Service restarts with the secret
- Service environment updated
- Ready to make LLM calls

**Time**: ~30 seconds

### Step 4: Verify Deployment
```bash
# Check service status
render service get --name vera-bot

# View logs
render service logs --name vera-bot

# Test health endpoint (wait 30s after secret set)
curl https://vera-bot-<random-id>.onrender.com/v1/healthz
```

**Expected**: 
- Status: "Running"
- Logs show: "Listening on 0.0.0.0:10000"
- Health check: 200 OK

---

## Deployment Verification Checklist (5 minutes)

### Endpoint Tests

- [ ] **Health Check** (Should be instant)
  ```bash
  curl https://vera-bot-<id>.onrender.com/v1/healthz
  ```
  Expected: `{"status":"ok"}` or `200 OK`

- [ ] **Metadata** (Should be instant)
  ```bash
  curl https://vera-bot-<id>.onrender.com/v1/metadata
  ```
  Expected: Service info JSON

- [ ] **Context Storage** (Should be <500ms)
  ```bash
  curl -X POST https://vera-bot-<id>.onrender.com/v1/context \
    -H "Content-Type: application/json" \
    -d @sample_context.json
  ```
  Expected: 200 OK

- [ ] **Message Composition** (Should be 2-5s)
  ```bash
  curl -X POST https://vera-bot-<id>.onrender.com/v1/tick \
    -H "Content-Type: application/json" \
    -d @sample_tick.json
  ```
  Expected: Composed message in 2-5 seconds

- [ ] **Reply Handling** (Should be <2s)
  ```bash
  curl -X POST https://vera-bot-<id>.onrender.com/v1/reply \
    -H "Content-Type: application/json" \
    -d @sample_reply.json
  ```
  Expected: 200 OK

### Log Monitoring

- [ ] **Startup logs look good**
  ```bash
  render service logs --name vera-bot | head -20
  ```
  Should show:
  - Python version
  - FastAPI startup
  - Keep-alive thread start
  - Listening on port

- [ ] **No error logs**
  ```bash
  render service logs --name vera-bot | grep -i error
  ```
  Should return nothing (no errors)

- [ ] **Keep-alive working**
  ```bash
  render service logs --name vera-bot | grep "Keep-alive"
  ```
  Should show pings every 10 minutes

### Environment Check

- [ ] **API key is set**
  ```bash
  render env list --service vera-bot | grep GEMINI_API_KEY
  ```
  Should show: `GEMINI_API_KEY [redacted]`

- [ ] **LLM provider configured**
  ```bash
  render env list --service vera-bot | grep LLM
  ```
  Should show:
  - `LLM_PROVIDER` = gemini
  - `LLM_MODEL` = gemini-2.0-flash

- [ ] **Python version correct**
  ```bash
  render env list --service vera-bot | grep PYTHON
  ```
  Should show: `PYTHON_VERSION` = 3.11

---

## Post-Deployment Checklist (Optional)

### Optional: Set Up Monitoring

- [ ] **Enable Render alerts** (in dashboard)
  - Service restarts
  - Memory usage spike
  - High error rate

- [ ] **Set up uptime monitoring** (optional)
  - Use external service like UptimeRobot
  - Monitor `/v1/healthz` endpoint every 5 minutes

### Optional: Scale Up

- [ ] **Monitor request volume**
  - Check Render dashboard metrics
  - Track response times

- [ ] **Upgrade plan if needed**
  - Free tier: 750 hours/month
  - Starter: $7/month, guaranteed uptime
  - Standard: $12/month, auto-scaling

---

## Troubleshooting Quick Reference

| Problem | Solution |
|---------|----------|
| Service stuck in "Building" | Check: `render service logs --name vera-bot` |
| 502 Bad Gateway | Wait 30s, service might be restarting |
| 404 Not Found | Wrong URL format or endpoint path |
| Timeout errors | Normal: 2-5s for LLM calls, 25s max |
| API key error | Verify secret: `render secret set --service vera-bot GEMINI_API_KEY "key"` |
| Service sleeping | Free tier sleeps after 15min; keep-alive should help |
| Out of memory | Free tier has 0.5GB limit; upgrade if needed |

---

## Environment Variables Reference

### Must Set (Secrets)
```
GEMINI_API_KEY=your-key-from-google-ai-studio
```

### Pre-configured (from render.yaml)
```
LLM_PROVIDER=gemini
LLM_MODEL=gemini-2.0-flash
PYTHON_VERSION=3.11
```

### Auto-set by Render
```
PORT=10000  # (varies, typically ~10000)
```

---

## Key Deployment Details

| Item | Value |
|------|-------|
| **Runtime** | Python 3.11 |
| **Framework** | FastAPI + Uvicorn |
| **Plan** | Free ($0/month) |
| **Build Time** | 1-2 minutes |
| **Startup Time** | 15-20 seconds |
| **Memory** | 0.5 GB (shared) |
| **CPU** | Shared |
| **Health Check** | /v1/healthz |
| **Keep-Alive** | Every 10 minutes |
| **URL Pattern** | https://vera-bot-*.onrender.com |

---

## Service URLs After Deployment

Once deployed, your service will be available at:

```
https://vera-bot-<random-id>.onrender.com/
```

Replace `<random-id>` with your actual ID from Render dashboard.

### All Endpoints
```
GET  https://vera-bot-<id>.onrender.com/v1/healthz
GET  https://vera-bot-<id>.onrender.com/v1/metadata
POST https://vera-bot-<id>.onrender.com/v1/context
POST https://vera-bot-<id>.onrender.com/v1/tick
POST https://vera-bot-<id>.onrender.com/v1/reply
```

---

## Support & Documentation

| Document | Purpose |
|----------|---------|
| **RENDER_QUICKSTART.md** | 5-minute deployment guide |
| **DEPLOYMENT_ANALYSIS.md** | 12-section deep dive |
| **ANALYSIS_SUMMARY.md** | Project overview & metrics |
| **ARCHITECTURE_DIAGRAMS.md** | Visual system flows |
| **README.md** | Original project docs |
| **challenge-brief.md** | Challenge specification |

---

## Success Criteria

✅ **Deployment is successful when**:

1. Service status is "Running" in Render dashboard
2. Health check endpoint returns 200 OK
3. Logs show no errors in first 30 seconds
4. GEMINI_API_KEY is set in environment
5. Can successfully call `/v1/tick` endpoint
6. Responses are received in <6 seconds
7. Keep-alive pings appear in logs every 10 minutes
8. Service stays alive beyond 15-minute inactivity window

---

## Next Actions

### Immediate
- [ ] Follow "Deployment Steps" above
- [ ] Wait for service to show "Running"
- [ ] Test health endpoint

### After Successful Deployment
- [ ] Monitor logs for errors
- [ ] Run sample requests through all endpoints
- [ ] Verify API key is working
- [ ] Confirm keep-alive is active

### Optional Later
- [ ] Set up monitoring alerts
- [ ] Upgrade to Starter plan for guaranteed uptime
- [ ] Enable error tracking
- [ ] Set up CI/CD for auto-deployments

---

## Quick Command Reference

```bash
# Authenticate
render login

# Deploy
render deploy --blueprint

# Set secret
render secret set --service vera-bot GEMINI_API_KEY "key"

# View status
render service get --name vera-bot

# View logs (live)
render service logs --name vera-bot --follow

# View last 50 lines
render service logs --name vera-bot --tail 50

# Restart service
render service restart --name vera-bot

# List all services
render service list

# Delete service (careful!)
render service destroy --name vera-bot
```

---

## Estimated Timeline

| Step | Time | Total |
|------|------|-------|
| Install Render CLI | 1 min | 1 min |
| Authenticate | 1 min | 2 min |
| Deploy | 3 min | 5 min |
| Set secret | 1 min | 6 min |
| Verify endpoints | 5 min | 11 min |
| **Total** | — | **~15 min** |

---

## Final Notes

✨ **You're doing great!** This project is:
- ✅ Production-ready
- ✅ Fully tested
- ✅ Well documented
- ✅ Optimized for free tier
- ✅ Easy to deploy

🚀 **Ready to deploy?** Start with "Deployment Steps" above!

---

**Generated**: May 3, 2026  
**Repository**: https://github.com/Gaggs-daggs/vera-bot  
**Dashboard**: https://dashboard.render.com

---

*Good luck with your deployment! 🎉*
