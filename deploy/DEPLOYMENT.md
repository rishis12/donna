# Donna AI Backend - Deployment Guide

Complete deployment guide for Donna AI Backend to cloud platforms.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Development](#local-development)
3. [Docker Deployment](#docker-deployment)
4. [Cloud Deployment](#cloud-deployment)
5. [Database Migrations](#database-migrations)
6. [Environment Variables](#environment-variables)
7. [Health Checks](#health-checks)
8. [Webhooks](#webhooks)
9. [Troubleshooting](#troubleshooting)

## Prerequisites

- Python 3.11+
- Docker & Docker Compose (for containerized deployment)
- PostgreSQL (for production)
- Git
- Cloud platform account (Render/Railway/Fly.io)

## Local Development

### Option 1: Direct Python

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp ../deploy/env.example .env
# Edit .env with your values

# Run migrations
alembic upgrade head

# Start server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Option 2: Docker Compose (Local)

```bash
# Copy environment file
cp deploy/env.example backend/.env
# Edit backend/.env with your values

# Start with SQLite (local dev)
docker-compose -f deploy/docker-compose.yml -f deploy/docker-compose.local.yml up --build

# Or use production Postgres
docker-compose -f deploy/docker-compose.yml up --build
```

## Docker Deployment

### Build Image

```bash
docker build -f deploy/Dockerfile -t donna-backend:latest .
```

### Run Container

```bash
docker run -d \
  --name donna-backend \
  -p 8000:8000 \
  --env-file backend/.env \
  donna-backend:latest
```

### Docker Compose (Production)

```bash
# Set environment variables
export DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname
export SECRET_KEY=your-secret-key
# ... other env vars

# Start services
docker-compose -f deploy/docker-compose.yml up -d

# View logs
docker-compose -f deploy/docker-compose.yml logs -f backend
```

## Cloud Deployment

### Render.com

1. **Create New Web Service**
   - Connect your GitHub repository
   - Select "Docker" as the environment
   - Set Dockerfile path: `deploy/Dockerfile`
   - Set Docker context: `.`

2. **Add Environment Variables**
   - Go to Environment tab
   - Add all variables from `deploy/env.example`
   - Set `DATABASE_URL` to your Render PostgreSQL database URL

3. **Add PostgreSQL Database**
   - Create new PostgreSQL database
   - Copy the internal database URL
   - Use it as `DATABASE_URL` in your web service

4. **Deploy**
   - Render will auto-deploy on push to main branch
   - Or manually deploy from dashboard

**Render Configuration:**
- The `render.yaml` file is provided for infrastructure-as-code
- Deploy command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### Railway.app

1. **Create New Project**
   - Connect your GitHub repository
   - Railway will auto-detect the `railway.json` config

2. **Add PostgreSQL Service**
   - Click "New" → "Database" → "PostgreSQL"
   - Railway will provide `DATABASE_URL` automatically

3. **Configure Environment Variables**
   - Go to Variables tab
   - Add all required variables from `deploy/env.example`
   - `DATABASE_URL` is auto-provided by Railway

4. **Deploy**
   - Railway auto-deploys on push to main
   - Or trigger manual deploy

**Railway Configuration:**
- Uses `deploy/railway.json` for build settings
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### Fly.io

1. **Install Fly CLI**
   ```bash
   curl -L https://fly.io/install.sh | sh
   ```

2. **Login**
   ```bash
   flyctl auth login
   ```

3. **Create App**
   ```bash
   flyctl apps create donna-backend
   ```

4. **Set Secrets**
   ```bash
   flyctl secrets set DATABASE_URL=postgresql://...
   flyctl secrets set SECRET_KEY=...
   # ... set all required secrets
   ```

5. **Deploy**
   ```bash
   flyctl deploy
   ```

**Fly.io Configuration:**
- Uses `deploy/fly.toml` for app configuration
- Health check endpoint: `/health`
- Auto-scales based on traffic

## Database Migrations

### Initialize Alembic (First Time)

```bash
cd backend
alembic init alembic
# Copy the provided alembic/env.py and alembic.ini
```

### Create Migration

```bash
alembic revision --autogenerate -m "Description of changes"
```

### Apply Migrations

```bash
# Upgrade to latest
alembic upgrade head

# Downgrade one version
alembic downgrade -1

# Upgrade to specific revision
alembic upgrade <revision_id>
```

### Auto-Migration on Deploy

The `entrypoint.sh` script automatically runs migrations on container startup:

```bash
alembic upgrade head
```

## Environment Variables

### Required Variables

Copy `deploy/env.example` to `backend/.env` and fill in:

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname

# Security
SECRET_KEY=your-32-char-secret-key
ENCRYPTION_KEY=your-32-byte-encryption-key
JWT_SECRET=your-jwt-secret
JWT_ALGORITHM=HS256

# API Keys
GROQ_API_KEY=your-groq-api-key

# OAuth (Google)
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=https://your-domain.com/auth/google/callback

# OAuth (Microsoft)
MICROSOFT_CLIENT_ID=your-client-id
MICROSOFT_CLIENT_SECRET=your-client-secret
MICROSOFT_REDIRECT_URI=https://your-domain.com/auth/microsoft/callback

# OAuth (Slack)
SLACK_CLIENT_ID=your-client-id
SLACK_CLIENT_SECRET=your-client-secret
SLACK_REDIRECT_URI=https://your-domain.com/auth/slack/callback
SLACK_BOT_TOKEN=xoxb-your-token
SLACK_SIGNING_SECRET=your-signing-secret

# Server
BASE_URL=https://your-domain.com
ENV=production
```

### Generating Secrets

```bash
# Generate SECRET_KEY (32+ chars)
openssl rand -hex 32

# Generate ENCRYPTION_KEY (32 bytes, base64)
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## Health Checks

### Health Endpoint

```bash
GET /health
```

Response:
```json
{
  "status": "healthy",
  "database": "healthy",
  "scheduler": "running",
  "version": "1.0.0"
}
```

### Webhook Health

```bash
GET /webhook/health
```

## Webhooks

### Calendar Webhook

```bash
POST /webhook/calendar
```

Accepts calendar event webhooks from Google Calendar, Outlook, etc.

### Slack Webhook

```bash
POST /webhook/slack
Headers:
  X-Slack-Signature: v0=...
  X-Slack-Request-Timestamp: 1234567890
```

Validates Slack signature and processes events.

**Setup in Slack:**
1. Go to your Slack app settings
2. Navigate to "Event Subscriptions"
3. Set Request URL: `https://your-domain.com/webhook/slack`
4. Subscribe to events you need

## CI/CD with GitHub Actions

The provided `.github/workflows/deploy.yml` automatically:

1. **Runs tests** on every push
2. **Deploys to cloud** on push to main/master

### Setup Secrets

In GitHub repository settings → Secrets:

- `RENDER_SERVICE_ID` - Your Render service ID
- `RENDER_API_KEY` - Your Render API key
- `RAILWAY_TOKEN` - Your Railway token
- `FLY_API_TOKEN` - Your Fly.io API token

## Troubleshooting

### Database Connection Issues

```bash
# Test PostgreSQL connection
psql $DATABASE_URL

# Check if database exists
docker exec -it donna-postgres psql -U donna -d donna_db -c "\dt"
```

### Migration Issues

```bash
# Check current revision
alembic current

# Show migration history
alembic history

# Create new migration if models changed
alembic revision --autogenerate -m "Fix models"
```

### Container Issues

```bash
# View logs
docker logs donna-backend

# Enter container
docker exec -it donna-backend bash

# Restart container
docker restart donna-backend
```

### Rate Limiting

Default rate limits:
- 100 requests per minute per IP
- Adjust in `backend/app/core/middleware.py`

### Scheduler Not Running

Check logs for scheduler errors:
```bash
docker logs donna-backend | grep scheduler
```

## Production Checklist

- [ ] Set all environment variables
- [ ] Use strong SECRET_KEY and ENCRYPTION_KEY
- [ ] Configure CORS for production domains
- [ ] Set up PostgreSQL database
- [ ] Run database migrations
- [ ] Configure OAuth redirect URIs for production domain
- [ ] Set up SSL/HTTPS (handled by platform)
- [ ] Configure webhook endpoints
- [ ] Set up monitoring/logging
- [ ] Test health endpoint
- [ ] Test OAuth flows
- [ ] Test webhook endpoints

## Support

For issues, check:
1. Application logs
2. Health endpoint status
3. Database connectivity
4. Environment variables
5. OAuth configuration

