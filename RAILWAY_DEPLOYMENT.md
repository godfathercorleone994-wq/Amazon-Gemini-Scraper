# Railway Deployment Guide 🚂

Complete guide to deploy Amazon Gemini Scraper on Railway.

## Prerequisites

Before deploying, ensure you have:

1. ✅ A Railway account ([railway.app](https://railway.app))
2. ✅ MongoDB Atlas account with a database created
3. ✅ Google Gemini API key ([ai.google.dev](https://ai.google.dev))
4. ✅ This repository forked or accessible to your GitHub account

## Step-by-Step Deployment

### 1. Prepare MongoDB Atlas

1. Go to [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
2. Create a cluster (Free tier works)
3. Create a database user with password
4. **Important**: In Network Access, add `0.0.0.0/0` to allow Railway connections
5. Get your connection string (looks like: `mongodb+srv://username:password@cluster.mongodb.net/`)

### 2. Get Your Gemini API Key

1. Visit [Google AI Studio](https://ai.google.dev)
2. Create a new API key
3. Save it securely

### 3. Deploy to Railway

#### Option A: Deploy from GitHub (Recommended)

1. **Login to Railway**
   - Go to [railway.app](https://railway.app)
   - Sign in with GitHub

2. **Create New Project**
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your forked repository

3. **Add Redis Service**
   - In your project, click "+ New"
   - Select "Database" → "Add Redis"
   - Railway will automatically provision Redis and set the `REDIS_URL` variable

4. **Configure Environment Variables**
   
   In your main app service, add these variables:
   
   ```env
   # Required Variables
   MONGODB_ATLAS_URI=mongodb+srv://username:password@cluster.mongodb.net/amazon_scraper?retryWrites=true&w=majority
   GEMINI_API_KEY=your-gemini-api-key-here
   SECRET_KEY=your-super-secret-random-key-here
   ENVIRONMENT=production
   DEBUG=False
   
   # Redis (automatically set by Railway Redis plugin)
   REDIS_URL=redis://default:password@redis-host:port
   CELERY_BROKER_URL=${REDIS_URL}/1
   CELERY_RESULT_BACKEND=${REDIS_URL}/2
   
   # Optional: Additional AI Providers
   OPENAI_API_KEY=your-openai-key (optional)
   HUGGINGFACE_API_KEY=your-hf-key (optional)
   
   # Optional: Notifications
   TELEGRAM_BOT_TOKEN=your-bot-token (optional)
   SENDGRID_API_KEY=your-sendgrid-key (optional)
   DISCORD_WEBHOOK_URL=your-webhook-url (optional)
   
   # Optional: Monitoring
   SENTRY_DSN=your-sentry-dsn (optional)
   ```

5. **Deploy**
   - Railway will automatically detect the `Dockerfile`
   - Click "Deploy" or wait for automatic deployment
   - Build takes 3-5 minutes (Playwright browser installation)

#### Option B: Deploy with Railway CLI

1. **Install Railway CLI**
   ```bash
   npm i -g @railway/cli
   ```

2. **Login**
   ```bash
   railway login
   ```

3. **Initialize Project**
   ```bash
   cd Amazon-Gemini-Scraper
   railway init
   ```

4. **Add Redis**
   ```bash
   railway add -d redis
   ```

5. **Set Environment Variables**
   ```bash
   railway variables set MONGODB_ATLAS_URI="your-mongodb-uri"
   railway variables set GEMINI_API_KEY="your-api-key"
   railway variables set SECRET_KEY="your-secret-key"
   railway variables set ENVIRONMENT="production"
   railway variables set DEBUG="False"
   ```

6. **Deploy**
   ```bash
   railway up
   ```

### 4. Verify Deployment

Once deployed, Railway will provide a URL (e.g., `your-app.railway.app`).

Test the deployment:

1. **Health Check**
   ```bash
   curl https://your-app.railway.app/api/v1/health
   ```
   
   Should return:
   ```json
   {
     "status": "healthy",
     "timestamp": "...",
     "services": {
       "mongodb": "connected",
       "redis": "connected"
     }
   }
   ```

2. **API Documentation**
   - Visit: `https://your-app.railway.app/api/v1/docs`
   - You should see the Swagger UI with all endpoints

3. **Test Scraping**
   ```bash
   curl -X POST "https://your-app.railway.app/api/v1/scraping/scrape" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://www.amazon.com/dp/B08N5WRWNW"}'
   ```

## Configuration Details

### Railway-Specific Settings

Railway automatically provides:
- ✅ `PORT` environment variable (app listens on this)
- ✅ HTTPS enabled by default
- ✅ Auto-restart on failure
- ✅ Log aggregation

### Resource Requirements

**Recommended:**
- Memory: 2GB+ (for Playwright)
- CPU: 1 vCPU+
- Storage: 2GB+ (for browser binaries)

**Free Tier Limits:**
- $5/month in usage credits
- Should be enough for testing
- Monitor usage in Railway dashboard

### Scaling Considerations

1. **Horizontal Scaling** (Multiple Instances)
   - Not recommended for free tier
   - Enable in Railway settings for production
   - Ensure sticky sessions if using authentication

2. **Worker Processes**
   - The app uses 4 workers by default
   - Adjust in `railway.json` or Dockerfile if needed

3. **Database Connections**
   - MongoDB Atlas free tier: 500 connections
   - App uses connection pooling (max 100)
   - Should be sufficient for single instance

## Troubleshooting

### Issue: Build Fails During Playwright Installation

**Solution:**
- This is normal and expected
- The `install_playwright.sh` script handles progress bar errors
- If build truly fails, check Railway logs for specific error

### Issue: "Module Not Found" Errors

**Solution:**
- Ensure `requirements.txt` is up to date
- Clear Railway build cache and redeploy

### Issue: MongoDB Connection Timeout

**Solutions:**
1. Check MongoDB Atlas Network Access allows `0.0.0.0/0`
2. Verify connection string format
3. Ensure username/password are correct
4. Check if cluster is paused (Atlas auto-pauses after inactivity)

### Issue: Redis Connection Failed

**Solutions:**
1. Ensure Redis service is running in Railway
2. Check if `REDIS_URL` variable is set correctly
3. Redis format should be: `redis://default:password@host:port`

### Issue: High Memory Usage

**Solutions:**
1. Reduce number of workers in `Dockerfile` CMD
2. Disable dashboard features if not needed
3. Set `scraper_headless=True` in environment
4. Consider upgrading Railway plan

### Issue: API Responds Slowly

**Possible Causes:**
1. Cold start (first request after inactivity)
2. Playwright browser initialization
3. AI API (Gemini) rate limits

**Solutions:**
1. Keep app warm with uptime monitor (e.g., UptimeRobot)
2. Cache frequently requested data with Redis
3. Consider upgrading AI API tier

## Monitoring & Logs

### View Logs

**Railway Dashboard:**
- Click on your service
- Go to "Deployments" tab
- Click on active deployment
- View real-time logs

**Railway CLI:**
```bash
railway logs
```

### Monitoring Endpoints

- **Health**: `/api/v1/health`
- **Metrics**: `/metrics` (if Prometheus enabled)
- **Info**: `/api/v1/info`

### Set Up Alerts

Use Railway webhooks to notify you:
1. Go to Settings → Webhooks
2. Add webhook URL for:
   - Deployment success/failure
   - Service crashes
   - Resource limits

## Cost Optimization

### Tips to Stay Within Free Tier

1. **Use External Services**
   - MongoDB Atlas Free Tier (M0)
   - Redis Cloud Free Tier
   - This reduces Railway usage

2. **Disable Unused Features**
   ```env
   ENABLE_DASHBOARD=False
   ENABLE_WEBHOOKS=False
   ENABLE_ML_FEATURES=False  # If not using ML
   ```

3. **Optimize Docker Image**
   - The `.dockerignore` file helps reduce image size
   - Consider multi-stage builds for further optimization

4. **Monitor Usage**
   - Check Railway dashboard regularly
   - Set up alerts for usage thresholds

## Production Checklist

Before going to production:

- [ ] Set strong `SECRET_KEY` (64+ random characters)
- [ ] Set `DEBUG=False`
- [ ] Set `ENVIRONMENT=production`
- [ ] Enable `SENTRY_DSN` for error tracking
- [ ] Configure all required environment variables
- [ ] Set up MongoDB backups in Atlas
- [ ] Test all API endpoints
- [ ] Set up uptime monitoring (UptimeRobot, Pingdom)
- [ ] Configure custom domain (optional)
- [ ] Set up rate limiting appropriately
- [ ] Review CORS settings
- [ ] Enable SSL/HTTPS (automatic in Railway)
- [ ] Set up logging and monitoring
- [ ] Document API for your users

## Custom Domain

To use a custom domain:

1. Go to your service settings in Railway
2. Click "Networking"
3. Add custom domain
4. Add CNAME record to your DNS:
   ```
   CNAME your-domain.com -> your-app.railway.app
   ```
5. Wait for DNS propagation (up to 48 hours)

## Updating Your Deployment

Railway automatically redeploys when you push to your GitHub repository:

1. Make changes locally
2. Commit and push to GitHub
3. Railway detects changes and redeploys
4. Monitor deployment in Railway dashboard

**Manual Redeploy:**
- In Railway dashboard, click "Redeploy"
- Or use CLI: `railway up`

## Support & Resources

- **Railway Documentation**: [docs.railway.app](https://docs.railway.app)
- **Railway Discord**: [discord.gg/railway](https://discord.gg/railway)
- **Project Issues**: [GitHub Issues](https://github.com/godfathercorleone994-wq/Amazon-Gemini-Scraper/issues)
- **API Documentation**: Your deployed app's `/api/v1/docs`

## Security Best Practices

1. **Never commit secrets**
   - Use Railway environment variables
   - Don't hardcode API keys

2. **Rotate credentials regularly**
   - Change API keys periodically
   - Update SECRET_KEY

3. **Use strong passwords**
   - MongoDB Atlas users
   - Redis passwords

4. **Monitor access**
   - Check Railway logs regularly
   - Set up alerts for suspicious activity

5. **Keep dependencies updated**
   - Regularly update `requirements.txt`
   - Monitor for security advisories

## Next Steps

After successful deployment:

1. ✅ Test all API endpoints
2. ✅ Monitor logs for errors
3. ✅ Set up notifications (Telegram, Discord, Email)
4. ✅ Create API documentation for your users
5. ✅ Implement authentication for production
6. ✅ Set up backups for MongoDB
7. ✅ Configure monitoring and alerts

---

**Happy Deploying! 🚀**

For questions or issues, please open an issue on GitHub.
