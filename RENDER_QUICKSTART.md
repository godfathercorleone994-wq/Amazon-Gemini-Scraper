# Render Quick Start Guide

## Deploy to Render in 5 Minutes

### Prerequisites
- GitHub account with this repository
- Render account (free tier available at https://render.com)
- MongoDB Atlas account (free tier at https://www.mongodb.com/cloud/atlas)
- Google Gemini API key (get it at https://makersuite.google.com/app/apikey)

### Step 1: Prepare MongoDB Atlas

1. Create a free cluster at MongoDB Atlas
2. Set network access to `0.0.0.0/0` (allow all IPs)
3. Create database user with password
4. Get connection string (looks like: `mongodb+srv://username:password@cluster.mongodb.net/...`)

### Step 2: Deploy to Render

**Option A: One-Click Blueprint Deploy (Easiest)**

1. Go to https://dashboard.render.com
2. Click **"New"** → **"Blueprint"**
3. Connect your GitHub repository
4. Render will detect `render.yaml`
5. Fill in required environment variables:
   - `MONGODB_ATLAS_URI`: Your MongoDB connection string
   - `GEMINI_API_KEY`: Your Gemini API key
6. Click **"Apply"**
7. Wait 5-10 minutes for deployment

**Option B: Manual Deploy**

1. Go to https://dashboard.render.com
2. Click **"New"** → **"Web Service"**
3. Connect your repository
4. Configure:
   - Name: `amazon-gemini-scraper`
   - Runtime: **Docker**
   - Branch: `main`
5. Add environment variables (see below)
6. Click **"Create Web Service"**

### Step 3: Verify Deployment

Once deployed, test these endpoints:

```bash
# Health check
https://your-service-name.onrender.com/api/v1/health

# API docs
https://your-service-name.onrender.com/api/v1/docs
```

## Required Environment Variables

Set these in Render dashboard:

| Variable | Required | Example/Description |
|----------|----------|---------------------|
| `MONGODB_ATLAS_URI` | ✅ Yes | `mongodb+srv://user:pass@cluster.mongodb.net/` |
| `GEMINI_API_KEY` | ✅ Yes | Your Google Gemini API key |
| `REDIS_URL` | ⚠️ Recommended | Auto-set if using Render Redis, or external Redis URL |

## Optional Environment Variables

| Variable | Purpose |
|----------|---------|
| `OPENAI_API_KEY` | For OpenAI integration |
| `TELEGRAM_BOT_TOKEN` | For Telegram notifications |
| `SENDGRID_API_KEY` | For email notifications |
| `DISCORD_WEBHOOK_URL` | For Discord notifications |
| `SENTRY_DSN` | For error tracking |

**Note**: `PORT`, `SECRET_KEY`, `ENVIRONMENT`, and `DEBUG` are auto-configured by Render.

## Common Issues

### Build fails
- Check build logs in Render dashboard
- Verify Dockerfile is valid
- Ensure all dependencies in requirements.txt are available

### App won't start
- Check environment variables are set correctly
- Verify MongoDB connection string
- Check logs for specific errors

### Can't connect to MongoDB
- Verify MongoDB Atlas network access allows 0.0.0.0/0
- Check username/password in connection string
- Ensure MongoDB Atlas cluster is running

## Cost

- **Render Free Tier**: 750 hours/month (sufficient for testing)
- **Render Starter**: $7/month (always on, no sleep)
- **MongoDB Atlas**: Free M0 tier available
- **Redis**: Free tier available with Render

## Next Steps

After deployment:
1. ✅ Test API endpoints
2. ✅ Configure notifications (optional)
3. ✅ Set up monitoring
4. ✅ Review logs for any issues

## Need Help?

- 📖 Full guide: [RENDER_DEPLOYMENT.md](RENDER_DEPLOYMENT.md)
- 🐛 Issues: https://github.com/godfathercorleone994-wq/Amazon-Gemini-Scraper/issues
- 💬 Render Community: https://community.render.com

---

**Deployment Time**: ~5-10 minutes  
**Difficulty**: Easy  
**Cost**: Free tier available
