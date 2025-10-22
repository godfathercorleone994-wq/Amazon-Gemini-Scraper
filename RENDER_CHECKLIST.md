# Pre-Deployment Checklist for Render

Use this checklist before deploying to Render to ensure everything is ready.

## ✅ Prerequisites

### Accounts
- [ ] Render account created (https://render.com)
- [ ] GitHub account with repository access
- [ ] MongoDB Atlas account (https://www.mongodb.com/cloud/atlas)
- [ ] Google Cloud account for Gemini API

### API Keys
- [ ] Google Gemini API key obtained
- [ ] (Optional) OpenAI API key
- [ ] (Optional) Telegram bot token
- [ ] (Optional) SendGrid API key
- [ ] (Optional) Discord webhook URL
- [ ] (Optional) Sentry DSN

## ✅ MongoDB Atlas Setup

- [ ] Free M0 cluster created
- [ ] Database user created with strong password
- [ ] Network access set to `0.0.0.0/0` (allow all)
- [ ] Connection string copied and saved securely
- [ ] Connection string format verified: `mongodb+srv://username:password@cluster.mongodb.net/...`

## ✅ Repository Configuration

- [ ] Repository forked/cloned to your GitHub
- [ ] `render.yaml` file present in root
- [ ] `Dockerfile` present and valid
- [ ] `.renderignore` present (optional but recommended)
- [ ] `requirements.txt` up to date

## ✅ Environment Variables Prepared

### Required
- [ ] `MONGODB_ATLAS_URI` - MongoDB connection string
- [ ] `GEMINI_API_KEY` - Google Gemini API key

### Recommended
- [ ] `REDIS_URL` - Will be auto-configured if using Render Redis

### Optional
- [ ] `OPENAI_API_KEY`
- [ ] `HUGGINGFACE_API_KEY`
- [ ] `TELEGRAM_BOT_TOKEN`
- [ ] `SENDGRID_API_KEY`
- [ ] `DISCORD_WEBHOOK_URL`
- [ ] `SENTRY_DSN`
- [ ] `AWS_ACCESS_KEY_ID`
- [ ] `AWS_SECRET_ACCESS_KEY`
- [ ] `S3_BUCKET_NAME`

### Auto-Configured (Do NOT set manually)
- [ ] `PORT` - Auto-set by Render to 10000
- [ ] `SECRET_KEY` - Auto-generated
- [ ] `ENVIRONMENT` - Set to "production"
- [ ] `DEBUG` - Set to "false"

## ✅ Documentation Review

- [ ] Read `RENDER_QUICKSTART.md` for quick start
- [ ] Review `RENDER_DEPLOYMENT.md` for full guide
- [ ] Check `PLATFORM_COMPARISON.md` if unsure about Render vs Railway

## ✅ Deployment Steps

### Using Blueprint (Recommended)
1. [ ] Go to https://dashboard.render.com
2. [ ] Click "New +" → "Blueprint"
3. [ ] Connect GitHub repository
4. [ ] Verify `render.yaml` detected
5. [ ] Fill in required environment variables
6. [ ] Click "Apply"
7. [ ] Wait for build (5-10 minutes first time)

### Using Manual Deploy
1. [ ] Go to https://dashboard.render.com
2. [ ] Click "New +" → "Web Service"
3. [ ] Connect GitHub repository
4. [ ] Select Docker runtime
5. [ ] Configure settings
6. [ ] Add environment variables
7. [ ] Create service
8. [ ] Wait for build

## ✅ Post-Deployment Verification

- [ ] Build completed successfully (check Render logs)
- [ ] Service is running (green status in dashboard)
- [ ] Health endpoint responding: `/api/v1/health`
- [ ] API docs accessible: `/api/v1/docs`
- [ ] MongoDB connection working (check logs)
- [ ] Redis connection working (check logs)
- [ ] Test scraping functionality

## ✅ Testing

Run these tests after deployment:

```bash
# 1. Health check
curl https://your-service.onrender.com/api/v1/health

# Expected response:
# {"status": "healthy", ...}

# 2. API info
curl https://your-service.onrender.com/api/v1/info

# Expected response:
# {"name": "Amazon-Gemini-Scraper", ...}

# 3. Live probe
curl https://your-service.onrender.com/api/v1/health/live

# 4. Ready probe
curl https://your-service.onrender.com/api/v1/health/ready
```

## ✅ Optional Services

### Add Redis
- [ ] In Render dashboard, click "New +" → "Redis"
- [ ] Select plan (free tier available)
- [ ] Connect to web service
- [ ] `REDIS_URL` will be auto-configured

### Add Background Worker (Celery)
- [ ] Create new "Background Worker" service
- [ ] Connect same repository
- [ ] Set start command: `celery -A workers.celery_app worker --loglevel=info`
- [ ] Add same environment variables
- [ ] Set `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND`

## ✅ Monitoring Setup

- [ ] Review logs in Render dashboard
- [ ] Set up log alerts (optional)
- [ ] Configure Sentry for error tracking (optional)
- [ ] Monitor resource usage (CPU/Memory)
- [ ] Set up uptime monitoring (optional)

## ✅ Security

- [ ] All secrets stored in Render environment variables (not in code)
- [ ] `.env` file NOT committed to git
- [ ] MongoDB Atlas network access configured correctly
- [ ] Strong passwords used for all services
- [ ] CORS configured properly for your domain
- [ ] Rate limiting enabled (already in code)

## ✅ Cost Management

- [ ] Understand free tier limitations (750 hours/month, sleeps after 15 min)
- [ ] Consider upgrading to Starter plan ($7/month) for production
- [ ] Monitor usage in Render dashboard
- [ ] Set up billing alerts

## ✅ Backup Plan

- [ ] MongoDB Atlas backups enabled
- [ ] Environment variables documented
- [ ] Repository backed up
- [ ] Know how to rollback deployment in Render

## Common Issues Checklist

If deployment fails, check:

- [ ] All required environment variables are set
- [ ] MongoDB connection string is correct
- [ ] MongoDB Atlas allows connections from 0.0.0.0/0
- [ ] Gemini API key is valid
- [ ] Dockerfile builds successfully locally
- [ ] Build logs for specific errors
- [ ] Port configuration (should be $PORT)

## Need Help?

- 📖 [RENDER_QUICKSTART.md](RENDER_QUICKSTART.md) - Quick start guide
- 📖 [RENDER_DEPLOYMENT.md](RENDER_DEPLOYMENT.md) - Full deployment guide
- 📖 [PLATFORM_COMPARISON.md](PLATFORM_COMPARISON.md) - Render vs Railway
- 🐛 [GitHub Issues](https://github.com/godfathercorleone994-wq/Amazon-Gemini-Scraper/issues)
- 💬 [Render Community](https://community.render.com)

## Ready to Deploy?

Once all checkboxes above are complete:

1. ✅ Go to https://dashboard.render.com
2. ✅ Follow deployment steps above
3. ✅ Monitor build progress
4. ✅ Test deployment
5. ✅ Celebrate! 🎉

---

**Estimated Time**: 5-10 minutes for deployment + 5-10 minutes for build  
**Difficulty**: Easy  
**Cost**: Free tier available
