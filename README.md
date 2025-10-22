# Amazon Gemini Scraper

Advanced Amazon Product Scraper with AI-powered extraction using Google Gemini, OpenAI, and other AI providers.

## Features

- 🤖 AI-powered product data extraction using Gemini, OpenAI, and HuggingFace
- 🌐 Advanced web scraping with Playwright (anti-detection)
- 📊 Price tracking and analysis
- 🔔 Multi-channel notifications (Telegram, Discord, Email)
- 📈 Real-time monitoring with Prometheus
- ⚡ Async task processing with Celery
- 🗄️ MongoDB for data persistence
- 🚀 Redis caching for performance
- 🎨 Streamlit dashboard for visualization
- 🔄 Automated CI/CD with GitHub Actions

## Tech Stack

- **Backend**: FastAPI
- **AI/ML**: Google Gemini, OpenAI, HuggingFace Transformers
- **Scraping**: Playwright, BeautifulSoup, Cloudscraper
- **Database**: MongoDB (Atlas), Redis
- **Task Queue**: Celery
- **Monitoring**: Prometheus, Sentry
- **Deployment**: Docker, Railway, Render
- **CI/CD**: GitHub Actions

## Quick Start

### Prerequisites

- Python 3.11+
- MongoDB Atlas account (or local MongoDB)
- Redis (or Redis Cloud)
- Google Gemini API key (required)
- OpenAI API key (optional)

### Environment Variables

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Required variables:
- `MONGODB_ATLAS_URI` - Your MongoDB connection string
- `REDIS_URL` - Your Redis connection URL
- `GEMINI_API_KEY` - Google Gemini API key

Optional variables:
- `OPENAI_API_KEY` - OpenAI API key
- `TELEGRAM_BOT_TOKEN` - For Telegram notifications
- `SENDGRID_API_KEY` - For email notifications
- `DISCORD_WEBHOOK_URL` - For Discord notifications
- `SENTRY_DSN` - For error tracking

### Local Development

1. Install dependencies:
```bash
pip install -r requirements.txt
playwright install chromium
```

2. Run the application:
```bash
uvicorn api.main:app --reload
```

3. Access the API documentation:
- Swagger UI: http://localhost:8000/api/v1/docs
- ReDoc: http://localhost:8000/api/v1/redoc

### Using Make commands

```bash
make install      # Install dependencies
make run          # Run the application
make test         # Run tests
make docker-up    # Start with Docker Compose
make docker-down  # Stop Docker containers
```

## Railway Deployment 🚂

### Option 1: Deploy with Dockerfile (Recommended)

1. **Create a new Railway project** from the [Railway Dashboard](https://railway.app)

2. **Connect your GitHub repository**

3. **Add environment variables** in Railway dashboard:
   - `MONGODB_ATLAS_URI` - Your MongoDB Atlas connection string
   - `REDIS_URL` - Railway Redis or external Redis URL
   - `GEMINI_API_KEY` - Your Gemini API key
   - `SECRET_KEY` - Generate a strong random key
   - `ENVIRONMENT=production`
   - `DEBUG=False`

4. **Deploy**:
   - Railway will automatically detect the `Dockerfile`
   - The `railway.json` configures the build and deployment
   - Railway will inject the `PORT` environment variable automatically

### Option 2: Deploy with Procfile

If you prefer not to use Docker:

1. Railway will use the `Procfile` instead
2. Set the same environment variables as above
3. Railway will use Python buildpack automatically

### Railway Services Setup

For a complete setup, you'll need:

1. **Main App Service** (this repository)
   - Automatically uses the Dockerfile
   - PORT is set by Railway

2. **MongoDB** 
   - Use MongoDB Atlas (recommended)
   - Or add Railway's MongoDB plugin

3. **Redis**
   - Add Railway's Redis plugin
   - Set `REDIS_URL` to the Railway Redis URL

### Important Notes for Railway:

- ✅ Railway automatically provides the `PORT` environment variable
- ✅ The app is configured to use `$PORT` from the environment
- ✅ Health check endpoint available at `/api/v1/health`
- ⚠️ Playwright browsers are installed during Docker build (may take 3-5 minutes)
- ⚠️ Ensure your MongoDB Atlas allows connections from Railway IPs (set to 0.0.0.0/0 or use Railway's static IPs)

### Monitoring Deployment

After deployment:
- Check logs in Railway dashboard
- Test health endpoint: `https://your-app.railway.app/api/v1/health`
- Access API docs: `https://your-app.railway.app/api/v1/docs`

## Render Deployment 🚀

**Quick Start**: See [RENDER_QUICKSTART.md](RENDER_QUICKSTART.md) for 5-minute deployment guide.  
**Full Guide**: See [RENDER_DEPLOYMENT.md](RENDER_DEPLOYMENT.md) for detailed instructions.

### Quick Start with Render

1. **Deploy with Blueprint (Recommended)**:
   - Go to [Render Dashboard](https://dashboard.render.com)
   - Click "New +" → "Blueprint"
   - Connect your GitHub repository
   - Render will detect `render.yaml` automatically
   - Set required environment variables:
     - `MONGODB_ATLAS_URI`
     - `GEMINI_API_KEY`
   - Click "Apply" to deploy

2. **Manual Deployment**:
   - Create a new Web Service
   - Select Docker runtime
   - Connect repository and configure environment variables
   - Deploy!

### What Render Provides

- ✅ Automatic HTTPS/SSL certificates
- ✅ Auto-scaling capabilities
- ✅ Free tier available (with limitations)
- ✅ Integrated Redis database option
- ✅ Simple environment variable management
- ✅ Built-in health checks
- ✅ Automatic deployments on git push

### Key Configuration Files

- `render.yaml` - Infrastructure as Code configuration
- `Dockerfile` - Docker build configuration
- `RENDER_DEPLOYMENT.md` - Complete deployment guide
- `RENDER_QUICKSTART.md` - 5-minute quick start guide

**Important**: See [RENDER_DEPLOYMENT.md](RENDER_DEPLOYMENT.md) for complete instructions, troubleshooting, and best practices.

## API Endpoints

### Health Check
- `GET /api/v1/health` - Health status
- `GET /api/v1/health/live` - Liveness probe
- `GET /api/v1/health/ready` - Readiness probe

### Scraping
- `POST /api/v1/scraping/scrape` - Scrape a single product
- `POST /api/v1/scraping/bulk` - Bulk scraping
- `GET /api/v1/scraping/search` - Search products
- `GET /api/v1/scraping/task/{task_id}` - Get scraping task status

### Analysis
- `POST /api/v1/analysis/sentiment` - Sentiment analysis of reviews
- `POST /api/v1/analysis/compare` - Compare products
- `GET /api/v1/analysis/trends` - Price trends

### Notifications
- `POST /api/v1/notifications/subscribe` - Subscribe to price alerts
- `GET /api/v1/notifications/list` - List notifications
- `POST /api/v1/notifications/test` - Test notification

## Docker Deployment

### Using Docker Compose (Local Development)

```bash
docker-compose up -d
```

This starts:
- FastAPI application (port 8000)
- MongoDB (port 27017)
- Redis (port 6379)
- Celery worker
- Flower (Celery monitoring, port 5555)
- Streamlit dashboard (port 8501)

### Building Docker Image

```bash
docker build -t amazon-scraper .
docker run -p 8000:8000 --env-file .env amazon-scraper
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_scraper.py -v
```

## Project Structure

```
.
├── api/                    # FastAPI application
│   ├── routes/            # API routes
│   └── middleware/        # Middleware (rate limiting, auth)
├── core/                  # Core scraping logic
│   ├── scraper_agent.py   # Playwright scraper
│   ├── gemini_extractor.py # AI extraction
│   └── fallback_extractors.py
├── models/                # Pydantic models
├── storage/               # Database clients
│   ├── mongodb_client.py
│   ├── redis_cache.py
│   └── s3_storage.py
├── workers/               # Celery workers
├── features/              # Additional features
│   ├── analysis/
│   ├── dashboard/
│   └── notifications/
├── utils/                 # Utilities
├── config/                # Configuration
├── scripts/               # Utility scripts
├── tests/                 # Tests
├── Dockerfile             # Docker configuration
├── docker-compose.yml     # Docker Compose
├── railway.json           # Railway configuration
├── Procfile               # Process file for Railway
├── requirements.txt       # Python dependencies
└── .env.example          # Environment variables template
```

## Security

- 🔐 JWT authentication support
- 🛡️ API key authentication
- ⚡ Rate limiting per endpoint
- 🔒 CORS configuration
- 📊 Request logging and monitoring

## Performance

- ⚡ Redis caching for frequent requests
- 🔄 Async/await for I/O operations
- 🎯 Connection pooling for databases
- 📦 Gzip compression for responses
- 🚀 Multiple workers in production

## Troubleshooting

### Playwright Installation Issues

If Playwright browsers fail to install:
```bash
playwright install chromium --with-deps
```

### MongoDB Connection Issues

Ensure:
- MongoDB Atlas allows connections from your IP
- Connection string includes credentials
- Network access is configured in Atlas

### Redis Connection Issues

Check:
- Redis URL format: `redis://user:password@host:port/db`
- Redis service is running
- Firewall allows connection

## CI/CD and Testing

This project includes comprehensive GitHub Actions workflows for automated testing and deployment validation.

### Available Workflows

- **Deployment Testing**: Validates Docker builds, application health, and deployment readiness
- **Railway Preview**: Provides preview deployment information
- **Health Check**: Monitors production deployment health

For detailed information, see:
- 📖 [Quick Start Guide](.github/QUICKSTART.md)
- 📖 [Complete Workflows Documentation](.github/WORKFLOWS.md)

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

**Note**: GitHub Actions will automatically test your changes!

## License

MIT License - see LICENSE file for details

## Support

For issues and questions:
- Open an issue on GitHub
- Check the API documentation at `/api/v1/docs`
- Review logs for error details

## Acknowledgments

- Google Gemini AI for data extraction
- Playwright for web scraping
- FastAPI for the web framework
- MongoDB and Redis for data storage
