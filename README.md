# Amazon Gemini Scraper

Advanced Amazon Product Scraper with AI-powered extraction using Google Gemini, OpenAI, and other AI providers.

## Features

- 🤖 AI-powered product data extraction using Gemini, OpenAI, and HuggingFace
- 🔍 Advanced web scraping with Playwright
- 📊 Price tracking and history
- 🔔 Real-time notifications (Telegram, Email, Discord)
- 💾 MongoDB Atlas for data persistence
- ⚡ Redis caching for performance
- 🎯 Background task processing with Celery
- 📈 Monitoring with Prometheus and Sentry
- 🔒 Secure authentication and rate limiting
- 🐳 Docker support

## Quick Start

### Prerequisites

- Python 3.11+
- MongoDB Atlas account (or local MongoDB)
- Redis instance
- At least one AI API key (Gemini, OpenAI, or HuggingFace)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/godfathercorleone994-wq/Amazon-Gemini-Scraper.git
cd Amazon-Gemini-Scraper
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
playwright install chromium
```

4. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Run the application:
```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

Visit `http://localhost:8000/api/v1/docs` for API documentation.

## Deployment on Render

### Method 1: Using render.yaml (Recommended)

1. Push your code to GitHub
2. Create a new Web Service on Render
3. Connect your GitHub repository
4. Render will automatically detect the `render.yaml` file
5. Configure required environment variables in Render dashboard:
   - `MONGODB_ATLAS_URI` - Your MongoDB Atlas connection string
   - `REDIS_URL` - Redis connection URL (use Render Redis addon)
   - `GEMINI_API_KEY` or `OPENAI_API_KEY` - At least one AI provider API key

### Method 2: Manual Configuration

1. Create a new Web Service on Render
2. Set the following:
   - **Build Command:**
     ```bash
     pip install --upgrade pip setuptools wheel && pip install -r requirements.txt && playwright install chromium && playwright install-deps
     ```
   - **Start Command:**
     ```bash
     uvicorn api.main:app --host 0.0.0.0 --port $PORT
     ```
   - **Environment:** Python 3.11

3. Add environment variables (see `.env.example`)

### Required External Services for Render

1. **MongoDB Atlas** (Free tier available)
   - Create a free cluster at [mongodb.com/atlas](https://www.mongodb.com/atlas)
   - Get your connection string
   - Add to Render as `MONGODB_ATLAS_URI`

2. **Redis** (Required for caching and Celery)
   - Add Render Redis addon (free tier available)
   - Or use external service like Upstash

3. **AI API Keys** (At least one required)
   - Google Gemini: [makersuite.google.com](https://makersuite.google.com/)
   - OpenAI: [platform.openai.com](https://platform.openai.com/)
   - HuggingFace: [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)

## Environment Variables

See `.env.example` for a complete list of environment variables.

### Required Variables

- `MONGODB_ATLAS_URI` - MongoDB connection string
- `REDIS_URL` - Redis connection URL
- `GEMINI_API_KEY` or `OPENAI_API_KEY` - AI provider API key
- `SECRET_KEY` - Secret key for JWT tokens (auto-generated on Render)

### Optional Variables

- AWS credentials for S3 storage
- Notification service credentials (Telegram, SendGrid, Discord)
- Monitoring service credentials (Sentry)

## API Endpoints

### Health Check
- `GET /api/v1/health/` - Basic health check
- `GET /api/v1/health/live` - Liveness probe
- `GET /api/v1/health/ready` - Readiness probe (checks dependencies)
- `GET /api/v1/health/detailed` - Detailed health information

### Scraping
- `POST /api/v1/scraping/extract` - Extract product data from Amazon URL
- `GET /api/v1/scraping/status/{task_id}` - Get extraction task status
- `GET /api/v1/scraping/products` - List scraped products

### Analysis
- `GET /api/v1/analysis/price-history/{asin}` - Get price history
- `GET /api/v1/analysis/analytics` - Get analytics summary

### Notifications
- `POST /api/v1/notifications/send` - Send notification
- `GET /api/v1/notifications/pending` - Get pending notifications

## Docker Deployment

### Using Docker Compose (Local Development)

```bash
docker-compose up -d
```

This starts:
- FastAPI application
- MongoDB
- Redis
- Celery worker
- Flower (Celery monitoring)

### Using Docker alone

```bash
docker build -t amazon-scraper .
docker run -p 8000:8000 -e MONGODB_ATLAS_URI=your-uri -e REDIS_URL=your-redis amazon-scraper
```

## Development

### Running Tests
```bash
make test
```

### Code Formatting
```bash
make format
```

### Linting
```bash
make lint
```

### Start Celery Worker
```bash
make run-celery
```

## Troubleshooting

### Common Issues

1. **Playwright Installation Error**
   - Run: `playwright install chromium && playwright install-deps`

2. **MongoDB Connection Failed**
   - Verify your MongoDB Atlas connection string
   - Check if IP whitelist includes your deployment IP
   - For Render: Add `0.0.0.0/0` to whitelist (or specific Render IPs)

3. **Redis Connection Failed**
   - Ensure Redis URL is correct
   - Check if Redis service is running

4. **Import Errors**
   - Ensure all dependencies are installed: `pip install -r requirements.txt`
   - Check Python version (3.11+ required)

5. **Port Issues on Render**
   - Application automatically uses `$PORT` environment variable
   - No manual configuration needed

## Performance Optimization

- Redis caching reduces API calls and database queries
- MongoDB indexes optimize query performance
- Rate limiting prevents API abuse
- Background tasks with Celery for heavy operations
- Connection pooling for database and Redis

## Security

- JWT-based authentication
- Rate limiting per IP
- CORS configuration
- Environment-based secrets
- Input validation with Pydantic

## Monitoring

- Health check endpoints for Kubernetes/Render
- Prometheus metrics (if enabled)
- Sentry error tracking (if configured)
- Comprehensive logging with Loguru

## License

See LICENSE file for details.

## Support

For issues and questions:
1. Check the [Issues](https://github.com/godfathercorleone994-wq/Amazon-Gemini-Scraper/issues) page
2. Create a new issue with detailed information
3. Include logs and error messages

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Architecture

```
├── api/                  # FastAPI application
│   ├── routes/          # API endpoints
│   ├── middleware/      # Custom middleware
│   └── main.py          # Application entry point
├── config/              # Configuration
├── core/                # Core scraping logic
├── features/            # Additional features
├── models/              # Data models
├── storage/             # Database clients
├── utils/               # Utility functions
└── workers/             # Celery tasks
```

## Tech Stack

- **Web Framework:** FastAPI
- **Scraping:** Playwright, BeautifulSoup4, Cloudscraper
- **AI:** Google Gemini, OpenAI, HuggingFace Transformers
- **Database:** MongoDB (Motor async driver)
- **Cache:** Redis (async)
- **Tasks:** Celery
- **Monitoring:** Prometheus, Sentry
- **Deployment:** Docker, Render
