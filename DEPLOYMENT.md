# Deployment Guide for Render

This guide provides step-by-step instructions for deploying the Amazon Gemini Scraper on Render.

## Prerequisites

Before deploying, ensure you have:

1. A GitHub account with this repository
2. A Render account (free tier available at [render.com](https://render.com))
3. A MongoDB Atlas account (free tier available)
4. At least one AI API key (Gemini, OpenAI, or HuggingFace)
5. A Redis instance (can use Render Redis addon)

## Step 1: Set Up MongoDB Atlas

1. Go to [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
2. Create a free cluster
3. Create a database user:
   - Go to Database Access
   - Add a new database user with a strong password
   - Save the username and password
4. Whitelist Render IPs:
   - Go to Network Access
   - Add IP: `0.0.0.0/0` (allows all IPs - for production, use specific Render IPs)
5. Get your connection string:
   - Go to your cluster
   - Click "Connect" → "Connect your application"
   - Copy the connection string
   - Replace `<password>` with your database user password
   - Example: `mongodb+srv://username:password@cluster0.xxxxx.mongodb.net/amazon_scraper`

## Step 2: Get AI API Keys

Choose at least one AI provider:

### Google Gemini (Recommended)
1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create an API key
3. Save it for later

### OpenAI (Alternative)
1. Go to [OpenAI Platform](https://platform.openai.com/api-keys)
2. Create an API key
3. Save it for later

### HuggingFace (Alternative)
1. Go to [HuggingFace Settings](https://huggingface.co/settings/tokens)
2. Create a token
3. Save it for later

## Step 3: Deploy on Render

### Option A: Using render.yaml (Automatic)

1. Log in to [Render](https://render.com)
2. Click "New" → "Blueprint"
3. Connect your GitHub repository
4. Render will detect the `render.yaml` file automatically
5. Click "Apply"
6. Go to the created service and add environment variables (see Step 4)

### Option B: Manual Deployment

1. Log in to [Render](https://render.com)
2. Click "New" → "Web Service"
3. Connect your GitHub repository
4. Configure the service:
   - **Name:** `amazon-gemini-scraper` (or your choice)
   - **Region:** Choose closest to you
   - **Branch:** `main`
   - **Root Directory:** Leave empty
   - **Environment:** `Python 3`
   - **Build Command:**
     ```bash
     pip install --upgrade pip setuptools wheel && pip install -r requirements.txt && playwright install chromium && playwright install-deps
     ```
   - **Start Command:**
     ```bash
     uvicorn api.main:app --host 0.0.0.0 --port $PORT
     ```
5. Click "Create Web Service"

## Step 4: Configure Environment Variables

In your Render service dashboard, go to "Environment" and add these variables:

### Required Variables

| Variable | Value | Description |
|----------|-------|-------------|
| `MONGODB_ATLAS_URI` | Your MongoDB connection string | From Step 1 |
| `REDIS_URL` | Redis connection URL | See Redis setup below |
| `GEMINI_API_KEY` or `OPENAI_API_KEY` | Your API key | From Step 2 |
| `SECRET_KEY` | Generate random string | For JWT tokens (click "Generate" in Render) |

### Optional Variables

| Variable | Value | Description |
|----------|-------|-------------|
| `ENVIRONMENT` | `production` | Deployment environment |
| `DEBUG` | `false` | Debug mode |
| `LOG_LEVEL` | `INFO` | Logging level |
| `ENABLE_ML_FEATURES` | `true` | Enable ML features |
| `ENABLE_NOTIFICATIONS` | `false` | Enable notifications (requires additional setup) |

## Step 5: Set Up Redis

### Option A: Render Redis Addon (Recommended)

1. In your Render dashboard, go to your web service
2. Click "Environment"
3. Scroll down to "Add-ons"
4. Click "Add" next to Redis
5. Choose the free plan
6. Render will automatically add `REDIS_URL` to your environment variables

### Option B: External Redis

Use a free Redis service like:
- [Upstash](https://upstash.com/) - Free tier available
- [Redis Cloud](https://redis.com/try-free/) - Free tier available

Add the connection URL as `REDIS_URL` environment variable.

## Step 6: Deploy

1. Click "Manual Deploy" → "Deploy latest commit" or wait for auto-deploy
2. Monitor the build logs
3. Wait for deployment to complete (5-10 minutes)

## Step 7: Verify Deployment

Once deployed, test your API:

1. Get your Render URL: `https://your-service-name.onrender.com`
2. Test health endpoint:
   ```bash
   curl https://your-service-name.onrender.com/api/v1/health/
   ```
3. Check API documentation:
   ```
   https://your-service-name.onrender.com/api/v1/docs
   ```

## Common Issues and Solutions

### Issue 1: Build Fails - Playwright Installation

**Error:** Playwright installation fails or times out

**Solution:**
- This is common on free tier due to resource limits
- The build command installs Playwright browsers which can be slow
- Wait for the build to complete (may take 8-10 minutes)
- If it fails, click "Manual Deploy" again

### Issue 2: Application Crashes on Startup

**Error:** Service keeps restarting

**Possible Causes:**
1. Missing required environment variables
2. Invalid MongoDB connection string
3. Redis connection failed

**Solution:**
- Check all required environment variables are set
- Test MongoDB connection string locally
- Verify Redis URL is correct
- Check service logs in Render dashboard

### Issue 3: MongoDB Connection Failed

**Error:** `Failed to connect to MongoDB`

**Solution:**
1. Check MongoDB Atlas network access:
   - Go to Network Access in MongoDB Atlas
   - Ensure `0.0.0.0/0` is whitelisted
2. Verify connection string:
   - Must include username and password
   - Must specify database name
   - Example: `mongodb+srv://user:pass@cluster.mongodb.net/amazon_scraper`
3. Check database user permissions

### Issue 4: Health Check Fails

**Error:** Readiness probe fails

**Solution:**
- This usually means MongoDB or Redis is not connected
- Check environment variables
- Look at application logs for specific error
- The `/api/v1/health/live` endpoint should always work
- The `/api/v1/health/ready` endpoint checks dependencies

### Issue 5: Port Binding Error

**Error:** Application can't bind to port

**Solution:**
- Ensure start command uses `$PORT` variable: `--port $PORT`
- Don't hardcode port 8000
- Render automatically sets the PORT environment variable

### Issue 6: Playwright Browser Not Found

**Error:** Browser executable not found

**Solution:**
- Ensure build command includes: `playwright install chromium && playwright install-deps`
- This installs Chromium browser and its dependencies
- On free tier, this might take longer

## Performance Optimization

### Free Tier Limitations

Render's free tier:
- Automatically spins down after 15 minutes of inactivity
- First request after spin-down takes ~30 seconds
- 750 hours/month of uptime
- Limited RAM (512MB)

### Recommendations

1. **Upgrade to Paid Plan** for production use
2. **Use keep-alive pings** to prevent spin-down:
   - Set up a cron job to ping your health endpoint every 10 minutes
   - Use services like [cron-job.org](https://cron-job.org)
3. **Optimize MongoDB connection:**
   - Keep connection pool small on free tier
   - Close connections when not in use
4. **Cache aggressively:**
   - Use Redis cache for frequently accessed data
   - Set appropriate TTL values

## Monitoring

### Check Service Health

```bash
# Basic health
curl https://your-service.onrender.com/api/v1/health/

# Detailed health with metrics
curl https://your-service.onrender.com/api/v1/health/detailed

# Check dependencies
curl https://your-service.onrender.com/api/v1/health/ready
```

### View Logs

1. Go to Render dashboard
2. Select your service
3. Click "Logs" tab
4. Filter by log level if needed

### Set Up Alerts

1. In Render dashboard, go to your service
2. Click "Settings"
3. Add notification email
4. Configure alert thresholds

## Scaling

### Horizontal Scaling (Paid Plans)

1. Go to service settings
2. Increase instance count
3. Configure load balancing

### Background Workers

To enable Celery workers for background tasks:

1. Uncomment the worker service in `render.yaml`
2. Or create a new Worker service manually:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `celery -A workers.celery_app worker --loglevel=info`
   - Add same environment variables as web service

## Security Best Practices

1. **Use Environment Variables:** Never commit secrets to code
2. **Rotate API Keys:** Regularly update API keys
3. **Monitor Access:** Check logs for suspicious activity
4. **Enable HTTPS:** Render provides free SSL certificates
5. **Rate Limiting:** Already configured in the application
6. **IP Whitelisting:** For production, whitelist specific IPs in MongoDB Atlas

## Backup and Recovery

### Database Backups

MongoDB Atlas automatically backs up your data:
1. Go to MongoDB Atlas dashboard
2. Select your cluster
3. Click "Backups" tab
4. Configure backup schedule

### Code Backups

Your code is already backed up in GitHub. To rollback:
1. Go to Render dashboard
2. Select your service
3. Click "Manual Deploy"
4. Choose previous commit

## Cost Optimization

### Free Tier Services

- **Web Service:** Render free tier
- **Database:** MongoDB Atlas free tier (512MB)
- **Cache:** Render Redis free tier (25MB)
- **AI APIs:** 
  - Gemini: Free tier with rate limits
  - OpenAI: Pay as you go (no free tier)

### Estimated Costs

For light usage:
- Render: $0 (free tier)
- MongoDB: $0 (free tier)
- Redis: $0 (free tier)
- Gemini API: $0 (within free tier limits)

For production:
- Render: $7-21/month (Starter-Standard plan)
- MongoDB: $0-9/month (M0-M2 tier)
- Redis: Included with Render plan or $5/month
- Gemini API: Pay per request (check current pricing)

## Support

If you encounter issues:

1. Check the [README.md](README.md) file
2. Review application logs in Render
3. Check MongoDB Atlas metrics
4. Review this deployment guide
5. Open an issue on GitHub with:
   - Error messages
   - Logs
   - Steps to reproduce
   - Environment details

## Next Steps

After successful deployment:

1. Test all API endpoints
2. Set up monitoring and alerts
3. Configure notifications (optional)
4. Set up background workers (optional)
5. Implement custom features
6. Configure domain name (optional, paid feature)

## Additional Resources

- [Render Documentation](https://render.com/docs)
- [MongoDB Atlas Documentation](https://docs.atlas.mongodb.com/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Playwright Documentation](https://playwright.dev/)
- [Gemini API Documentation](https://ai.google.dev/docs)
