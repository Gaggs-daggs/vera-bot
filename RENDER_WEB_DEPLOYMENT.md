# 🚀 VERA Bot — Manual Render Deployment Guide

**Status**: Ready to deploy via Render Web Dashboard  
**Date**: May 3, 2026

---

## Quick Deploy via Web Dashboard (Easiest!)

Since Render CLI has installation issues on this machine, use the **Render Web Dashboard** - it's actually faster and easier!

### Step-by-Step Web Dashboard Deployment

#### Step 1: Log In to Render
1. Go to: https://dashboard.render.com
2. Sign up (free) or log in with GitHub
3. Click "New +"
4. Select "Web Service"

#### Step 2: Connect GitHub Repository
1. Click "Connect your GitHub account" (if not already connected)
2. Authorize Render to access your GitHub repos
3. Search for: `vera-bot`
4. Select: `https://github.com/Gaggs-daggs/vera-bot`
5. Click "Connect"

#### Step 3: Configure Service
```
Service Settings:
  Name:                   vera-bot
  Environment:            Python 3
  Region:                 Oregon (or closest)
  Branch:                 main
  Build Command:          pip install -r requirements.txt
  Start Command:          uvicorn bot:app --host 0.0.0.0 --port $PORT
  Instance Type:          Free
```

#### Step 4: Add Environment Variables
Click "Advanced" → Add Environment Variable:

**Required:**
```
GEMINI_API_KEY = [your-api-key]
```

**Optional (already in render.yaml):**
```
LLM_PROVIDER = gemini
LLM_MODEL = gemini-2.0-flash
PYTHON_VERSION = 3.11
```

#### Step 5: Create Service
1. Review all settings
2. Click "Create Web Service"
3. Render starts building automatically

**Build Time**: 2-3 minutes

#### Step 6: Wait for Deployment
Watch the logs:
- ✅ Build starts
- ✅ Dependencies install
- ✅ Server starts
- ✅ Health check passes
- ✅ Service goes LIVE

#### Step 7: Get Your URL
Once live, you'll see:
```
Live URL: https://vera-bot-xxxxx.onrender.com
```

#### Step 8: Test Endpoints
```bash
# Test health check
curl https://vera-bot-xxxxx.onrender.com/v1/healthz

# Expected response:
{"status": "ok"}
```

---

## How to Get Gemini API Key (FREE)

1. Go to: https://aistudio.google.com/apikey
2. Click "Create API key"
3. Select project (or create new)
4. Copy the generated key
5. Paste in Render environment variables

**Free tier limit**: 15 requests per minute (plenty for merchant bot)

---

## Detailed Dashboard Steps with Screenshots

### Create New Service
```
Render Dashboard Home
    ↓
    [New +] button (top right)
    ↓
    Select "Web Service"
    ↓
    Connect GitHub
    ↓
    Select vera-bot repository
    ↓
    Configure & Deploy
```

### Service Configuration
```
┌─────────────────────────────────┐
│ New Web Service                 │
├─────────────────────────────────┤
│ Name: vera-bot                  │
│ Environment: Python 3           │
│ Region: Oregon                  │
│ Repository: vera-bot            │
│ Branch: main                    │
│ Root Directory: [blank]         │
│ Build Command:                  │
│   pip install -r requirements.txt
│ Start Command:                  │
│   uvicorn bot:app --host 0.0.0.0 \
│   --port $PORT                  │
│ Instance Type: Free             │
│ Auto-Deploy: On (GitHub pushes) │
└─────────────────────────────────┘
         ↓
    [Create Web Service]
```

### Environment Variables Setup
```
Render Dashboard > vera-bot Service > Environment
    ↓
    [Add Environment Variable]
    ↓
    Key:   GEMINI_API_KEY
    Value: (paste from Google AI Studio)
    ↓
    [Save]
```

---

## What Happens During Deployment

```
Timeline:
0:00   Service creation starts
0:30   Repository cloned from GitHub
1:00   Build starts
       - Python 3.11+ initialized
       - pip install -r requirements.txt
       - Dependencies installed (~20s)
2:00   Start command runs
       - uvicorn bot:app --host 0.0.0.0 --port $PORT
       - FastAPI initializes
       - Keep-alive thread starts
2:30   Health check runs
       - GET /v1/healthz
       - Success → Service marked "Live"
3:00   ✅ Service is LIVE and ready!
```

---

## Verify Deployment Success

### Check Service Status
1. Go to Render dashboard
2. Click "vera-bot" service
3. Look for: **"Live"** status with green checkmark

### Check Logs
1. In service page, click "Logs"
2. Should see:
```
INFO:     Started server process
INFO:     Waiting for application startup
INFO:     Uvicorn running on 0.0.0.0:10000
INFO:     Keep-alive thread started
```

### Test Endpoints
```bash
# Health check (instant)
curl https://vera-bot-xxxxx.onrender.com/v1/healthz
# Response: {"status": "ok"}

# Metadata (instant)
curl https://vera-bot-xxxxx.onrender.com/v1/metadata
# Response: Service info JSON

# Compose message (2-5 seconds)
curl -X POST https://vera-bot-xxxxx.onrender.com/v1/tick \
  -H "Content-Type: application/json" \
  -d @sample_request.json
```

---

## Troubleshooting

### Issue: Build Fails
**Solution**: Check logs for errors
- Missing requirements? Run `pip freeze` locally
- Python version? Should be 3.11+
- Syntax errors? Test locally first

### Issue: "Failed to start"
**Solution**: Check startup logs
- Uvicorn command correct?
- Port binding to $PORT?
- Dependencies installed?

### Issue: GEMINI_API_KEY not found
**Solution**: Verify environment variable
1. Click service → Environment
2. Confirm GEMINI_API_KEY is set
3. If missing, add it
4. Service will auto-restart

### Issue: Service keeps sleeping
**Solution**: Free tier sleeps after 15 min inactivity
- Keep-alive thread should help
- Or upgrade to Starter plan ($7/month)

### Issue: Timeout errors
**Solution**: 
- LLM calls take 2-5 seconds (normal)
- Render timeout is 30 seconds (fine)
- If longer, check LLM API status

---

## Auto-Deploy on GitHub Push

Since you connected GitHub:

1. **Any push to `main` branch** → Auto-deploy
2. **You see build progress** in Render dashboard
3. **Live updates** happen automatically
4. **Zero downtime** (Render handles it)

Example workflow:
```bash
# Make changes locally
git add .
git commit -m "Fix something"
git push origin main

# Render automatically:
# 1. Detects the push
# 2. Clones new code
# 3. Rebuilds
# 4. Restarts service
# 5. All within 2-3 minutes
```

---

## Post-Deployment Tasks

- [ ] ✅ Service is live
- [ ] ✅ Health check returns 200
- [ ] ✅ GEMINI_API_KEY is set
- [ ] ✅ Logs show no errors
- [ ] ✅ Test `/v1/tick` endpoint
- [ ] ✅ Monitor first 5 minutes
- [ ] ⏳ Celebrate! 🎉

---

## Important Links

| Item | URL |
|------|-----|
| **Render Dashboard** | https://dashboard.render.com |
| **Your Service** | https://vera-bot-xxxxx.onrender.com |
| **Gemini API Key** | https://aistudio.google.com/apikey |
| **GitHub Repo** | https://github.com/Gaggs-daggs/vera-bot |
| **Render Docs** | https://render.com/docs |

---

## Monitoring & Maintenance

### Daily Monitoring
- Check Render dashboard for service status
- Review logs for errors
- Monitor response times

### Weekly Review
- Check uptime metrics
- Review error rates
- Monitor memory usage

### Monthly Review
- Upgrade plan if needed (>1000 req/day)
- Review cost ($0 for free tier)
- Plan scaling strategy

---

## Cost Breakdown

| Item | Cost |
|------|------|
| Render Free Tier | $0/month |
| Gemini API (15 req/min) | FREE |
| **Total** | **$0/month** |

### Upgrade Path (when needed)
- **Starter Plan**: $7/month (guaranteed uptime)
- **Standard Plan**: $12/month (auto-scaling)
- **Pro Plan**: $50+/month (full enterprise)

---

## Next Steps

1. ✅ Go to https://dashboard.render.com
2. ⏳ Click "New +" → "Web Service"
3. ⏳ Connect GitHub & select vera-bot
4. ⏳ Configure (build + start commands)
5. ⏳ Add GEMINI_API_KEY environment variable
6. ⏳ Create service
7. ⏳ Wait 2-3 minutes
8. ✨ Service is LIVE!

---

## FAQ

**Q: Do I need Render CLI?**  
A: No! Dashboard is easier and faster.

**Q: How long does deployment take?**  
A: 2-3 minutes from clicking "Create"

**Q: Will it auto-update?**  
A: Yes! Any push to main branch triggers auto-deploy

**Q: What if I make a mistake?**  
A: You can delete and recreate in seconds

**Q: Can I test locally first?**  
A: Yes! Run `python bot.py` before deploying

**Q: What's the URL format?**  
A: `https://vera-bot-<random-id>.onrender.com`

**Q: Can I use a custom domain?**  
A: Yes! Available on paid plans

---

## Success Indicators

✅ **You'll know it's working when:**
1. Status shows "Live" (green checkmark)
2. Health check returns 200 OK
3. Logs show "Listening on 0.0.0.0:10000"
4. Keep-alive pings appear every 10 min
5. Service doesn't sleep after 15 min

---

**Ready? Go to https://dashboard.render.com and click "New +"!** 🚀

---

*Guide created: 2026-05-03*  
*All files committed and pushed to GitHub*  
*You're ready to deploy now!*
