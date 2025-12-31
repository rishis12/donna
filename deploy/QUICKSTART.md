# Quick Start Deployment Guide

## 🚀 Fastest Way to Deploy

### Option 1: Render.com (Recommended - Easiest)

1. **Fork/Clone Repository**
   ```bash
   git clone <your-repo-url>
   cd donna
   ```

2. **Create Render Account**
   - Go to [render.com](https://render.com)
   - Sign up with GitHub

3. **Create PostgreSQL Database**
   - New → PostgreSQL
   - Name: `donna-postgres`
   - Copy the Internal Database URL

4. **Create Web Service**
   - New → Web Service
   - Connect your GitHub repo
   - Name: `donna-backend`
   - Environment: **Docker**
   - Dockerfile Path: `deploy/Dockerfile`
   - Docker Context: `.`
   - Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

5. **Add Environment Variables**
   - Click on your service → Environment
   - Add all variables from `deploy/env.example`
   - Set `DATABASE_URL` to your PostgreSQL Internal Database URL
   - Set `BASE_URL` to your Render service URL (e.g., `https://donna-backend.onrender.com`)

6. **Deploy**
   - Click "Create Web Service"
   - Render will build and deploy automatically
   - Wait 5-10 minutes for first deploy

7. **Update OAuth Redirect URIs**
   - Google: `https://your-service.onrender.com/auth/google/callback`
   - Microsoft: `https://your-service.onrender.com/auth/microsoft/callback`
   - Slack: `https://your-service.onrender.com/auth/slack/callback`

### Option 2: Railway.app

1. **Install Railway CLI** (optional)
   ```bash
   npm i -g @railway/cli
   railway login
   ```

2. **Create Project**
   - Go to [railway.app](https://railway.app)
   - New Project → Deploy from GitHub
   - Select your repository

3. **Add PostgreSQL**
   - Click "+ New" → Database → PostgreSQL
   - Railway auto-provides `DATABASE_URL`

4. **Configure Variables**
   - Go to Variables tab
   - Add all variables from `deploy/env.example`
   - `DATABASE_URL` is auto-set by Railway

5. **Deploy**
   - Railway auto-deploys on push
   - Or click "Deploy" in dashboard

### Option 3: Fly.io

1. **Install Fly CLI**
   ```bash
   curl -L https://fly.io/install.sh | sh
   flyctl auth login
   ```

2. **Create App**
   ```bash
   flyctl apps create donna-backend
   ```

3. **Set Secrets**
   ```bash
   flyctl secrets set DATABASE_URL=postgresql://...
   flyctl secrets set SECRET_KEY=$(openssl rand -hex 32)
   flyctl secrets set ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
   # ... set all other secrets
   ```

4. **Deploy**
   ```bash
   flyctl deploy
   ```

## 📋 Pre-Deployment Checklist

- [ ] All environment variables set
- [ ] PostgreSQL database created
- [ ] OAuth apps configured (Google, Microsoft, Slack)
- [ ] OAuth redirect URIs updated to production domain
- [ ] `BASE_URL` set to production domain
- [ ] `ENV=production` set
- [ ] Strong `SECRET_KEY` and `ENCRYPTION_KEY` generated

## 🔧 Local Testing Before Deploy

```bash
# Test with Docker
docker-compose -f deploy/docker-compose.yml up --build

# Test health endpoint
curl http://localhost:8000/health

# Test webhook endpoint
curl http://localhost:8000/webhook/health
```

## ✅ Post-Deployment Verification

1. **Health Check**
   ```bash
   curl https://your-domain.com/health
   ```

2. **Test OAuth**
   - Visit `https://your-domain.com/auth/google`
   - Should redirect to Google OAuth

3. **Test API**
   ```bash
   curl https://your-domain.com/
   ```

## 🐛 Common Issues

### Database Connection Failed
- Check `DATABASE_URL` format
- Ensure database is accessible
- For Render: Use Internal Database URL

### OAuth Redirect Mismatch
- Ensure redirect URIs match exactly (including https://)
- Check for trailing slashes

### Build Fails
- Check Dockerfile path in platform settings
- Ensure all dependencies in `requirements.txt`

### Migrations Not Running
- Check `entrypoint.sh` has execute permissions
- Verify `alembic.ini` exists

## 📚 Next Steps

- Read full deployment guide: `deploy/DEPLOYMENT.md`
- Configure webhooks: See webhook section in deployment guide
- Set up monitoring: Add logging service
- Configure custom domain: Update DNS and BASE_URL

