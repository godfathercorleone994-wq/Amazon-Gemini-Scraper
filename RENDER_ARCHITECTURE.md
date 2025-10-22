# Render Deployment Architecture

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         RENDER PLATFORM                          │
│                                                                   │
│  ┌────────────────────────────────────────────────────────┐    │
│  │           Web Service (Docker Container)                │    │
│  │                                                          │    │
│  │  ┌──────────────────────────────────────────────────┐  │    │
│  │  │         FastAPI Application                       │  │    │
│  │  │                                                    │  │    │
│  │  │  • API Routes (/api/v1/*)                        │  │    │
│  │  │  • Health Checks (/health)                       │  │    │
│  │  │  • Scraping Logic (Playwright)                   │  │    │
│  │  │  • AI Processing (Gemini/OpenAI)                 │  │    │
│  │  │                                                    │  │    │
│  │  │  Workers: 4                                       │  │    │
│  │  │  Port: $PORT (10000)                             │  │    │
│  │  └──────────────────────────────────────────────────┘  │    │
│  │                                                          │    │
│  │  Environment Variables:                                 │    │
│  │  • MONGODB_ATLAS_URI                                   │    │
│  │  • GEMINI_API_KEY                                      │    │
│  │  • REDIS_URL                                           │    │
│  │  • SECRET_KEY (auto-generated)                         │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                   │
│  ┌────────────────────────────────────────────────────────┐    │
│  │           Redis Database (Optional)                     │    │
│  │                                                          │    │
│  │  • Caching                                              │    │
│  │  • Session Storage                                      │    │
│  │  • Celery Broker/Backend                               │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                   │
│  ┌────────────────────────────────────────────────────────┐    │
│  │      Background Worker (Optional - Celery)              │    │
│  │                                                          │    │
│  │  • Async Task Processing                               │    │
│  │  • Scheduled Jobs                                       │    │
│  │  • Email/Notification Tasks                            │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ HTTPS/SSL
                              │
                              ▼
                    ┌─────────────────┐
                    │   Internet      │
                    │   Users/APIs    │
                    └─────────────────┘

External Services (Connected via Internet):

┌──────────────────────┐     ┌──────────────────────┐
│  MongoDB Atlas       │     │  Google Gemini API   │
│                      │     │                      │
│  • Product Data      │     │  • AI Extraction     │
│  • User Data         │     │  • Data Processing   │
│  • Analytics         │     │  • Content Analysis  │
└──────────────────────┘     └──────────────────────┘

┌──────────────────────┐     ┌──────────────────────┐
│  OpenAI API          │     │  Notification APIs   │
│  (Optional)          │     │  (Optional)          │
│                      │     │                      │
│  • GPT Processing    │     │  • Telegram          │
│  • Alternative AI    │     │  • Discord           │
└──────────────────────┘     │  • SendGrid/Email    │
                              └──────────────────────┘

┌──────────────────────┐     ┌──────────────────────┐
│  Sentry              │     │  Amazon Sites        │
│  (Optional)          │     │  (Scraping Target)   │
│                      │     │                      │
│  • Error Tracking    │     │  • Product Pages     │
│  • Performance       │     │  • Reviews           │
└──────────────────────┘     │  • Pricing Data      │
                              └──────────────────────┘
```

## Data Flow

```
1. Client Request
   ↓
2. Render Load Balancer (HTTPS)
   ↓
3. FastAPI Application
   ↓
4. Process Request:
   ├─→ Check Redis Cache (if available)
   │   ├─→ Cache Hit: Return cached data
   │   └─→ Cache Miss: Continue processing
   │
   ├─→ Scrape Amazon (if needed)
   │   ├─→ Playwright Browser
   │   └─→ BeautifulSoup Parser
   │
   ├─→ AI Processing (Gemini/OpenAI)
   │   ├─→ Extract structured data
   │   └─→ Analyze content
   │
   ├─→ Store in MongoDB
   │   ├─→ Product data
   │   └─→ Analytics
   │
   └─→ Cache in Redis
       └─→ For future requests
   ↓
5. Return Response to Client
```

## Deployment Flow

```
1. Code Push to GitHub
   ↓
2. Render Webhook Triggered (if auto-deploy enabled)
   ↓
3. Build Process:
   ├─→ Clone Repository
   ├─→ Build Docker Image
   │   ├─→ Install System Dependencies
   │   ├─→ Install Python Packages
   │   └─→ Install Playwright Browsers
   ├─→ Run Health Checks
   └─→ Create Container
   ↓
4. Deploy:
   ├─→ Stop Old Container (if exists)
   ├─→ Start New Container
   ├─→ Load Environment Variables
   ├─→ Health Check Verification
   └─→ Route Traffic to New Container
   ↓
5. Monitoring:
   ├─→ Application Logs
   ├─→ Resource Metrics
   └─→ Health Checks
```

## Configuration Files

```
Repository Structure for Render:

amazon-gemini-scraper/
├── render.yaml                 ← Main Render config (IaC)
├── Dockerfile                  ← Container build instructions
├── requirements.txt            ← Python dependencies
├── .renderignore              ← Files to exclude from build
├── build.sh                   ← Optional build script
│
├── RENDER_DEPLOYMENT.md       ← Full deployment guide
├── RENDER_QUICKSTART.md       ← Quick start guide
├── RENDER_CHECKLIST.md        ← Pre-deployment checklist
├── PLATFORM_COMPARISON.md     ← Render vs Railway
│
├── api/
│   ├── main.py                ← FastAPI application entry
│   └── routes/                ← API endpoints
│
├── config/
│   └── settings.py            ← Configuration management
│
└── [other application files]
```

## Resource Allocation

### Free Tier
- **RAM**: 512 MB
- **CPU**: Shared
- **Disk**: Ephemeral (resets on redeploy)
- **Hours**: 750 hours/month
- **Sleep**: After 15 minutes of inactivity

### Starter Plan ($7/month)
- **RAM**: 512 MB
- **CPU**: Shared
- **Disk**: Ephemeral
- **Hours**: Always on (no sleep)
- **Features**: Better for production

### Standard Plan ($25/month)
- **RAM**: 2 GB
- **CPU**: 1 vCPU
- **Disk**: Ephemeral
- **Hours**: Always on
- **Features**: Auto-scaling, more resources

## Health Monitoring

```
Render Health Checks:
├── Path: /api/v1/health
├── Frequency: Every 30 seconds
├── Timeout: 10 seconds
├── Failure Threshold: 3 consecutive failures
└── Action on Failure: Auto-restart container

Application Health Endpoints:
├── /api/v1/health        → General health status
├── /api/v1/health/live   → Liveness probe
└── /api/v1/health/ready  → Readiness probe
```

## Security Layers

```
Security Stack:

1. Network Layer:
   ├── Render's Infrastructure Security
   ├── DDoS Protection
   └── HTTPS/SSL Encryption (automatic)

2. Application Layer:
   ├── CORS Configuration
   ├── Rate Limiting
   ├── API Key Authentication (optional)
   └── JWT Authentication (optional)

3. Data Layer:
   ├── MongoDB Atlas Encryption at Rest
   ├── Encrypted Connections (TLS/SSL)
   └── Redis Encryption (if using Render Redis)

4. Secrets Management:
   └── Environment Variables (encrypted at rest)
```

## Scaling Strategy

```
Horizontal Scaling (Multiple Instances):
├── Standard Plan: 2+ instances
├── Load balancing: Automatic
└── Session sharing: Via Redis

Vertical Scaling (Resources):
├── Starter → Standard (512MB → 2GB RAM)
└── Standard → Pro (Custom resources)

Database Scaling:
├── MongoDB Atlas: M0 → M10 → M20+
└── Redis: Free → Starter → Standard+
```

## Backup and Recovery

```
Backup Strategy:

1. Application Code:
   └── GitHub Repository (version controlled)

2. Database:
   ├── MongoDB Atlas: Automatic backups
   └── Point-in-time recovery available

3. Environment Variables:
   ├── Documented in repository (.env.example)
   └── Backup copy stored securely

4. Rollback:
   ├── Render: Deploy previous version
   └── MongoDB: Restore from backup
```

## Cost Breakdown Example

```
Production Setup:

Web Service (Starter):        $7.00/month
├── Always on
└── 512MB RAM

Redis (Starter):              $5.00/month
├── 256MB
└── Shared

MongoDB Atlas (M10):          $9.00/month
├── 2GB RAM
└── Shared cluster

Total:                        $21.00/month

Optional:
├── Sentry Error Tracking:    $0-26/month
├── SendGrid Email:           $0-15/month
└── Additional workers:       $7/each
```

## Getting Started

1. **Review this architecture**
2. **Check [RENDER_CHECKLIST.md](RENDER_CHECKLIST.md)**
3. **Follow [RENDER_QUICKSTART.md](RENDER_QUICKSTART.md)**
4. **Deploy!**

---

For questions or issues, see [RENDER_DEPLOYMENT.md](RENDER_DEPLOYMENT.md) for troubleshooting.
