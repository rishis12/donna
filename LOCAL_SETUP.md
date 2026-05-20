# Local Development Setup

This guide helps you set up Donna for local development or connect to a production backend.

---

## Option A: Connect to Production Backend (Recommended for Testing)

If you have a backend deployed on Render, you can connect the desktop app directly to it without running a local server.

### Step 1: Get Your Render API URL

1. Go to your [Render Dashboard](https://dashboard.render.com)
2. Click on your backend service
3. Copy the URL (e.g., `https://donna-backend-xxxx.onrender.com`)

### Step 2: Configure Desktop App

```bash
cd desktop

# Create .env file
echo "VITE_API_URL=https://your-app-name.onrender.com" > .env

# Install dependencies
npm install

# Run the app
npm install -D @tauri-apps/cli
npx tauri dev
```

The desktop app will now connect to your production backend.

---

## Option B: Full Local Development

Run both the backend and desktop app locally for development.

### Step 1: Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate it
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
```

Edit `backend/.env`:
```env
SECRET_KEY=your-secret-key-32-chars-minimum
ENCRYPTION_KEY=your-encryption-key-32-bytes
GEMINI_API_KEY=your-gemini-api-key
DATABASE_URL=sqlite+aiosqlite:///./agent.db
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback
```

Start the backend:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Step 2: Desktop App Setup

```bash
cd desktop

# Create .env for local backend
echo "VITE_API_URL=http://localhost:8000" > .env

# Install dependencies
npm install
npm install -D @tauri-apps/cli

# Run the app
npx tauri dev
```

---

## Switching Between Local and Production

Update `desktop/.env`:

**Use Production (Render):**
```env
VITE_API_URL=https://your-app-name.onrender.com
```

**Use Local Backend:**
```env
VITE_API_URL=http://localhost:8000
```

Then restart the desktop app.

---

## Benefits of Each Approach

### Production Backend (Render)
- No local server needed
- Works from anywhere
- Always available (24/7)
- HTTPS secure connections
- PostgreSQL database

### Local Development
- Faster iteration
- Debug backend code
- Test database changes
- No internet required
- Full control

---

## Troubleshooting

**Desktop app can't connect:**
- Check the backend URL is correct in `desktop/.env`
- Verify the backend is running (local) or deployed (Render)
- Check browser console for errors

**OAuth not working:**
- Ensure redirect URIs match exactly in Google/Azure console
- For local: `http://localhost:8000/auth/google/callback`
- For Render: `https://your-app.onrender.com/auth/google/callback`

**Gemini API errors:**
- Verify `GEMINI_API_KEY` is set correctly
- Check API key has access to Gemini 2.5 Flash
- View [Google AI Studio](https://makersuite.google.com) for status
