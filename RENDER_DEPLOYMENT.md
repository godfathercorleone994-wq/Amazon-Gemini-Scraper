# Render Deployment Guide

This guide provides step-by-step instructions for deploying the Amazon Gemini Scraper to Render.

## Prerequisites

Before deploying to Render, ensure you have:

- ✅ A [Render account](https://render.com) (free tier available)
- ✅ A MongoDB Atlas account and cluster (free tier available)
- ✅ Google Gemini API key (required)
- ✅ Optional: OpenAI API key, SendGrid API key, Telegram bot token, etc.

## Deployment Options

### Option 1: Using render.yaml (Infrastructure as Code) - Recommended

This option uses the `render.yaml` file to automatically configure all services.

1. **Fork/Clone this repository** to your GitHub account

2. **Go to Render Dashboard**
   - Visit [Render Dashboard](https://dashboard.render.com)
   - Click "New +" → "Blueprint"

3. **Connect Repository**
   - Connect your GitHub account if not already connected
   - Select this repository
   - Render will automatically detect the `render.yaml` file

4. **Configure Environment Variables**
   
   Render will prompt you to set the following environment variables:
   
   **Required:**
   - `MONGODB_ATLAS_URI` - Your MongoDB Atlas connection string
     - Format: `mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority`
   - `GEMINI_API_KEY` - Your Google Gemini API key
   
   **Recommended:**
   - `REDIS_URL` - Redis connection URL (or use Render's Redis add-on)
     - If using Render Redis: Will be auto-configured
     - If using external Redis: `redis://default:password@host:port/0`
   
   **Optional (for full features):**
   - `OPENAI_API_KEY` - OpenAI API key for alternative AI processing
   - `HUGGINGFACE_API_KEY` - HuggingFace API key for ML features
   - `TELEGRAM_BOT_TOKEN` - For Telegram notifications
   - `SENDGRID_API_KEY` - For email notifications
   - `DISCORD_WEBHOOK_URL` - For Discord notifications
   - `SENTRY_DSN` - For error tracking
   - `AWS_ACCESS_KEY_ID` - For AWS S3 storage (optional)
   - `AWS_SECRET_ACCESS_KEY` - For AWS S3 storage (optional)
   - `S3_BUCKET_NAME` - S3 bucket name (optional)
   - `CELERY_BROKER_URL` - Celery broker URL (uses Redis by default)
   - `CELERY_RESULT_BACKEND` - Celery result backend (uses Redis by default)
   
   **Auto-configured (do not set manually):**
   - `PORT` - Automatically set by Render to 10000
   - `SECRET_KEY` - Auto-generated secure key
   - `ENVIRONMENT` - Set to "production"
   - `DEBUG` - Set to "false"

5. **Deploy**
   - Click "Apply" to create the services
   - Render will:
     - Build the Docker image (this may take 5-10 minutes on first build)
     - Install Playwright browsers
     - Start the application
     - Provision Redis database (if included in blueprint)

6. **Verify Deployment**
   - Once deployed, Render will provide a URL like: `https://your-service-name.onrender.com`
   - Test the health endpoint: `https://your-service-name.onrender.com/api/v1/health`
   - Access API documentation: `https://your-service-name.onrender.com/api/v1/docs`

### Option 2: Manual Deployment (Web Service Only)

If you prefer to manually configure the service:

1. **Create New Web Service**
   - Go to Render Dashboard → "New +" → "Web Service"
   - Connect your repository

2. **Configure Service**
   - **Name**: `amazon-gemini-scraper` (or your choice)
   - **Runtime**: Docker
   - **Region**: Choose closest to your users
   - **Branch**: `main` (or your deployment branch)
   - **Dockerfile Path**: `./Dockerfile`
   - **Docker Context**: `.`

3. **Configure Build & Deploy**
   - **Docker Command**: (leave empty, uses Dockerfile CMD)
   - Or specify: `uvicorn api.main:app --host 0.0.0.0 --port $PORT --workers 4`

4. **Set Environment Variables**
   - Add all required and optional environment variables (see Option 1 list above)

5. **Advanced Settings**
   - **Health Check Path**: `/api/v1/health`
   - **Auto-Deploy**: Yes (enable for automatic deployments on git push)

6. **Create Web Service**
   - Click "Create Web Service"
   - Wait for the build to complete (5-10 minutes)

## Setting Up MongoDB Atlas

1. **Create a Free Cluster**
   - Go to [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
   - Create a free M0 cluster

2. **Configure Network Access**
   - In Atlas Dashboard → Network Access
   - Click "Add IP Address"
   - Click "Allow Access from Anywhere" (for Render)
   - Or add specific Render IP addresses if using static IPs

3. **Create Database User**
   - In Atlas Dashboard → Database Access
   - Click "Add New Database User"
   - Create user with password authentication
   - Grant "Read and write to any database" role

4. **Get Connection String**
   - In Atlas Dashboard → Database → Connect
   - Choose "Connect your application"
   - Copy the connection string
   - Replace `<password>` with your database user password
   - Set this as `MONGODB_ATLAS_URI` in Render

## Setting Up Redis

### Option A: Using Render Redis (Recommended)

1. If using `render.yaml`, Redis is automatically provisioned
2. The `REDIS_URL` environment variable is auto-configured
3. No manual setup required

### Option B: Using External Redis

1. **Redis Cloud** (Free tier available)
   - Go to [Redis Cloud](https://redis.com/try-free/)
   - Create a free database
   - Copy the connection URL
   - Set as `REDIS_URL` in Render

2. **Upstash Redis** (Free tier available)
   - Go to [Upstash](https://upstash.com/)
   - Create a Redis database
   - Copy the Redis URL
   - Set as `REDIS_URL` in Render

## Celery Workers (Optional)

For background task processing with Celery:

1. **Add Background Worker Service**
   - In Render Dashboard → "New +" → "Background Worker"
   - Connect same repository
   - **Start Command**: `celery -A workers.celery_app worker --loglevel=info`
   - Add all same environment variables as the web service

2. **Configure Celery URLs**
   - Set `CELERY_BROKER_URL` to your Redis URL
   - Set `CELERY_RESULT_BACKEND` to your Redis URL
   - Or use different Redis database numbers: `/1` and `/2`

## Post-Deployment Configuration

### 1. MongoDB Database Initialization

The application will automatically:
- Create collections on first use
- Set up indexes for performance
- No manual initialization required

### 2. Test the Deployment

```bash
# Health check
curl https://your-service-name.onrender.com/api/v1/health

# Get API info
curl https://your-service-name.onrender.com/api/v1/info

# Test scraping (requires authentication if enabled)
curl -X POST https://your-service-name.onrender.com/api/v1/scraping/scrape \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.amazon.com/dp/PRODUCT_ID"}'
```

### 3. Monitor Your Application

- **Logs**: View real-time logs in Render Dashboard
- **Metrics**: Monitor CPU, Memory, and Request metrics
- **Alerts**: Set up alerts for service health
- **Sentry**: If configured, view errors in Sentry dashboard

## Performance Optimization

### 1. Scaling

- **Starter Plan**: Single instance, suitable for testing
- **Standard Plan**: Multiple instances with auto-scaling
- Increase workers: Modify `--workers 4` in start command

### 2. Build Time Optimization

First build may take 5-10 minutes due to:
- Playwright browser installation (~800MB)
- Python dependencies compilation
- System dependencies installation

Subsequent builds are faster due to layer caching.

### 3. Cold Start Mitigation

Render free tier services may spin down after inactivity:
- Use paid plans for always-on services
- Implement keep-alive pings if needed
- Consider background workers for critical tasks

## Important Notes

### Playwright Browsers

- Chromium browser is installed during Docker build
- Takes ~3-5 minutes and ~800MB disk space
- Required for web scraping functionality

### Environment Variables Security

- Never commit `.env` file or secrets to git
- Use Render's environment variable dashboard
- Consider using Render's Secret Files for sensitive data

### Network & Firewall

- Ensure MongoDB Atlas allows connections from 0.0.0.0/0
- Or use Render's static IPs and whitelist those in Atlas
- Check that external APIs (Gemini, OpenAI) are accessible

### Resource Limits

- Free tier: 512MB RAM, shared CPU
- Monitor resource usage in Render dashboard
- Upgrade plan if needed for production workloads

## Troubleshooting

### Build Failures

**Issue**: Docker build fails
- Check Dockerfile syntax
- Verify all dependencies in requirements.txt
- Check build logs for specific errors

**Issue**: Playwright installation fails
- Increase build timeout
- Check system dependencies in Dockerfile
- Verify `install_playwright.sh` script

### Runtime Errors

**Issue**: Application won't start
- Check `PORT` environment variable is set
- Verify all required environment variables
- Check application logs in Render dashboard

**Issue**: Database connection fails
- Verify MongoDB Atlas connection string
- Check network access in MongoDB Atlas
- Ensure credentials are correct

**Issue**: Redis connection fails
- Verify Redis URL format
- Check Redis service is running
- Test connection separately

### Performance Issues

**Issue**: Slow responses
- Check resource usage (CPU/Memory)
- Verify database indexes
- Consider Redis caching
- Increase worker count

**Issue**: Timeouts
- Increase timeout settings
- Check external API latency
- Monitor Playwright scraping time

## Monitoring and Maintenance

### Health Checks

Render automatically monitors:
- `/api/v1/health` - General health status
- HTTP response codes
- Service uptime

### Logging

- View logs in Render dashboard
- Logs retained for 7 days (free tier)
- Consider external log aggregation for production

### Updates and Deployments

- **Auto-deploy**: Enabled by default with `render.yaml`
- Push to main branch triggers automatic deployment
- Manual deploy: Click "Deploy" button in Render dashboard
- Rollback: Use Render dashboard to rollback to previous version

## Cost Estimation

### Free Tier Limits

- 750 hours/month of free services
- Shared CPU, 512MB RAM
- Services spin down after 15 minutes of inactivity
- Multiple free services allowed

### Paid Plans

- **Starter**: $7/month - Always on, 512MB RAM
- **Standard**: $25/month - 2GB RAM, auto-scaling
- **Pro**: Custom pricing for production workloads

### Additional Costs

- **Redis**: Free tier available, paid plans start at $5/month
- **MongoDB Atlas**: Free M0 tier, paid plans start at $9/month
- **External Services**: Gemini API, OpenAI, etc. have their own pricing

## Best Practices

1. **Environment Variables**
   - Use Render's environment groups for multiple services
   - Keep production secrets separate from development

2. **Database**
   - Use MongoDB Atlas free tier for development
   - Upgrade to paid tier for production
   - Enable backups in Atlas

3. **Monitoring**
   - Set up Sentry for error tracking
   - Use Prometheus metrics if needed
   - Monitor costs and resource usage

4. **Security**
   - Enable CORS properly
   - Use strong SECRET_KEY
   - Implement rate limiting
   - Keep dependencies updated

5. **Deployment**
   - Test in preview environments first
   - Use feature flags for gradual rollouts
   - Monitor logs during deployments
   - Have rollback plan ready

## Support and Resources

- 📖 [Render Documentation](https://render.com/docs)
- 💬 [Render Community](https://community.render.com)
- 🐛 [Report Issues](https://github.com/godfathercorleone994-wq/Amazon-Gemini-Scraper/issues)
- 📧 [Render Support](https://render.com/support)

## Next Steps

After successful deployment:

1. ✅ Test all API endpoints
2. ✅ Verify database connections
3. ✅ Test scraping functionality
4. ✅ Configure notifications (if needed)
5. ✅ Set up monitoring and alerts
6. ✅ Review and optimize performance
7. ✅ Document any customizations

---

**Need Help?** Open an issue on GitHub or consult the Render documentation.
