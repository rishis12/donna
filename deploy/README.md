# Deployment Configuration

Complete deployment setup for Donna AI Backend.

## 📁 Files Overview

- **Dockerfile** - Multi-stage Docker build for production
- **docker-compose.yml** - Production setup with PostgreSQL
- **docker-compose.local.yml** - Local development override
- **entrypoint.sh** - Startup script with auto-migrations
- **alembic.ini** - Database migration configuration
- **render.yaml** - Render.com infrastructure config
- **railway.json** - Railway.app deployment config
- **fly.toml** - Fly.io deployment config
- **env.example** - Environment variables template
- **DEPLOYMENT.md** - Full deployment guide
- **QUICKSTART.md** - Quick start guide

## 🚀 Quick Deploy

See [QUICKSTART.md](./QUICKSTART.md) for the fastest deployment path.

## 📖 Full Documentation

See [DEPLOYMENT.md](./DEPLOYMENT.md) for complete deployment instructions.

## 🏗️ Architecture

```
┌─────────────────┐
│   Cloud Host    │
│  (Render/Railway│
│     /Fly.io)    │
└────────┬────────┘
         │
    ┌────▼────┐
    │ Backend │
    │ (FastAPI)│
    └────┬────┘
         │
    ┌────▼────┐
    │PostgreSQL│
    └─────────┘
```

## 🔑 Required Environment Variables

See `env.example` for all required variables.

**Minimum for production:**
- `DATABASE_URL` - PostgreSQL connection string
- `SECRET_KEY` - 32+ character secret
- `ENCRYPTION_KEY` - 32-byte Fernet key
- `GROQ_API_KEY` - Groq API key for LLM
- `BASE_URL` - Your production domain
- OAuth credentials (Google, Microsoft, Slack)

## 🐳 Docker Commands

```bash
# Build image
docker build -f deploy/Dockerfile -t donna-backend .

# Run locally
docker-compose -f deploy/docker-compose.yml up

# Run production
docker-compose -f deploy/docker-compose.yml up -d
```

## 🔄 Database Migrations

Migrations run automatically on container startup via `entrypoint.sh`.

Manual migration:
```bash
cd backend
alembic upgrade head
```

## ✅ Health Checks

- `/health` - Application health
- `/webhook/health` - Webhook endpoints health

## 📞 Support

For deployment issues, check:
1. Application logs
2. Health endpoint
3. Database connectivity
4. Environment variables

