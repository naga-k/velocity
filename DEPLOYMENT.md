# Velocity Deployment Guide

Quick deployment guide for the hackathon. Choose your preferred platform.

## Prerequisites

- [ ] Anthropic API key
- [ ] Slack Bot Token (optional)
- [ ] Linear API Key (optional)
- [ ] Git repository pushed to GitHub

---

## Option 1: Render (Recommended - You're Familiar!)

### Backend on Render

1. **Create Web Service**
   - Go to https://dashboard.render.com
   - Click "New +" → "Web Service"
   - Connect your GitHub repo
   - Configure:
     - **Name**: `velocity-backend`
     - **Root Directory**: `backend`
     - **Runtime**: Docker
     - **Instance Type**: Free or Starter

2. **Add Disk for Persistent Storage**
   - In service settings → "Disks"
   - Click "Add Disk"
   - **Mount Path**: `/app/data` (for SQLite)
   - **Size**: 1 GB (free tier)
   - Add another disk:
     - **Mount Path**: `/app/memory` (for agent memory files)
     - **Size**: 1 GB

3. **Environment Variables**
   ```
   ANTHROPIC_API_KEY=<your-key>
   SLACK_BOT_TOKEN=<your-token>
   LINEAR_API_KEY=<your-key>
   REDIS_URL=<upstash-redis-url>
   DATABASE_URL=sqlite:////app/data/app.db
   FRONTEND_URL=<will-add-after-vercel-deploy>
   ```

4. **Deploy**
   - Click "Create Web Service"
   - Wait for build (~3-5 min)
   - Note your backend URL: `https://velocity-backend.onrender.com`

### Redis on Upstash (Free Tier)

1. Go to https://upstash.com
2. Create account → Create Database
3. Select "Global" → Free tier
4. Copy the `REDIS_URL` (looks like `rediss://...@...upstash.io:6379`)
5. Add to Render environment variables

### Frontend on Vercel

1. Go to https://vercel.com/new
2. Import your GitHub repo
3. Configure:
   - **Framework Preset**: Next.js
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build` (auto-detected)
   - **Output Directory**: `.next` (auto-detected)

4. **Environment Variable**
   ```
   NEXT_PUBLIC_API_URL=https://velocity-backend.onrender.com
   ```

5. Click "Deploy"
6. Copy your Vercel URL and update Render's `FRONTEND_URL` env var

---

## Option 2: Railway

### Backend on Railway

1. **Install Railway CLI** (optional)
   ```bash
   npm install -g @railway/cli
   railway login
   ```

2. **Create Project**
   - Go to https://railway.app/new
   - Connect GitHub repo
   - Select `backend/` as root
   - Railway auto-detects Dockerfile

3. **Add Volume**
   - Go to service settings → "Volumes"
   - Add volume:
     - **Mount Path**: `/app/data`
     - **Size**: 1 GB
   - Add another:
     - **Mount Path**: `/app/memory`
     - **Size**: 1 GB

4. **Environment Variables** (same as Render above)

5. **Add Redis**
   - In project → "New" → "Database" → "Redis"
   - Railway auto-generates `REDIS_URL` environment variable
   - No Upstash needed!

6. Deploy automatically triggers

### Frontend (same Vercel steps as above)

---

## Option 3: Fly.io

### Backend on Fly.io

1. **Install Fly CLI**
   ```bash
   curl -L https://fly.io/install.sh | sh
   fly auth login
   ```

2. **Create fly.toml** (in project root)
   ```toml
   app = "velocity-backend"

   [build]
     dockerfile = "backend/Dockerfile"

   [env]
     PORT = "8000"

   [[services]]
     internal_port = 8000
     protocol = "tcp"

     [[services.ports]]
       port = 80
       handlers = ["http"]

     [[services.ports]]
       port = 443
       handlers = ["tls", "http"]

     [services.http_checks]
       interval = 10000
       timeout = 2000
       grace_period = "5s"
       method = "GET"
       path = "/api/health"

   [mounts]
     source = "velocity_data"
     destination = "/app/data"

     source = "velocity_memory"
     destination = "/app/memory"
   ```

3. **Create Volumes**
   ```bash
   fly volumes create velocity_data --size 1
   fly volumes create velocity_memory --size 1
   ```

4. **Set Secrets**
   ```bash
   fly secrets set ANTHROPIC_API_KEY=<key>
   fly secrets set SLACK_BOT_TOKEN=<token>
   fly secrets set LINEAR_API_KEY=<key>
   fly secrets set REDIS_URL=<upstash-url>
   ```

5. **Deploy**
   ```bash
   fly deploy
   ```

### Frontend (same Vercel steps)

---

## Testing Deployment

Once both are deployed:

1. **Backend Health Check**
   ```bash
   curl https://your-backend-url.com/api/health
   ```
   Should return: `{"status":"ok","version":"...","anthropic_configured":true}`

2. **Frontend**
   - Visit your Vercel URL
   - Try sending a message
   - Check browser console for errors

3. **Verify Persistence**
   - Create a session
   - Restart backend service
   - Session should still exist

---

## Environment Variables Summary

### Backend
| Variable | Required | Example | Notes |
|----------|----------|---------|-------|
| `ANTHROPIC_API_KEY` | Yes | `sk-ant-...` | Claude API key |
| `SLACK_BOT_TOKEN` | No | `xoxb-...` | For Slack MCP |
| `LINEAR_API_KEY` | No | `lin_api_...` | For Linear tools |
| `REDIS_URL` | Recommended | `rediss://...` | Upstash or Railway Redis |
| `DATABASE_URL` | No | `sqlite:////app/data/app.db` | Default is fine |
| `FRONTEND_URL` | Yes | `https://...vercel.app` | For CORS |

### Frontend
| Variable | Required | Example | Notes |
|----------|----------|---------|-------|
| `NEXT_PUBLIC_API_URL` | Yes | `https://...onrender.com` | Backend URL |

---

## Troubleshooting

### Backend won't start
- Check logs for missing env vars
- Verify Dockerfile builds locally: `docker build -t velocity-backend backend/`
- Check health endpoint: `/api/health`

### Frontend can't reach backend
- Verify `NEXT_PUBLIC_API_URL` is set correctly
- Check CORS settings in `backend/app/main.py`
- Ensure backend `FRONTEND_URL` matches Vercel URL

### Sessions not persisting
- Verify volume is mounted at `/app/data`
- Check SQLite file exists: `ls /app/data/app.db` (via SSH/logs)
- Ensure `DATABASE_URL` points to mounted volume

### Redis not working
- App should work without Redis (graceful fallback)
- Check `REDIS_URL` format: `rediss://` (with TLS)
- Verify Upstash database is active

---

## Cost Estimates (Free Tiers)

- **Render**: Free web service + 2 x 1GB disks (free)
- **Railway**: $5 credit/month (should cover hackathon)
- **Fly.io**: Free tier (3 shared-cpu-1x VMs)
- **Vercel**: Free (hobby tier)
- **Upstash Redis**: Free tier (10,000 commands/day)

**Total hackathon cost**: $0-5 depending on platform choice

---

## Quick Start (Render + Vercel)

1. **Deploy Backend to Render** (10 min)
   - New Web Service → GitHub repo → Root: `backend` → Docker
   - Add 2 disks: `/app/data` and `/app/memory`
   - Add env vars (see table above)
   - Deploy

2. **Set up Upstash Redis** (2 min)
   - Create free database
   - Copy `REDIS_URL` to Render env vars

3. **Deploy Frontend to Vercel** (5 min)
   - Import repo → Root: `frontend`
   - Add `NEXT_PUBLIC_API_URL` env var
   - Deploy

4. **Update CORS** (1 min)
   - Copy Vercel URL
   - Update Render's `FRONTEND_URL` env var
   - Trigger redeploy (or it auto-restarts)

**Total time: ~20 minutes**

Done! 🚀
