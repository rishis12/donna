# Donna - AI Executive Assistant

A cross-platform desktop AI assistant inspired by Donna Paulsen from Suits. Donna sits in your system tray and helps you manage your calendar, emails, reminders, and communications via natural language or voice.

## Features

- **System Tray Integration** - Always accessible, toggle with `Ctrl+Shift+Space`
- **Natural Language Processing** - Chat naturally with your AI assistant
- **Voice Input** - Push-to-talk microphone support with Whisper transcription
- **Reminders** - "Remind me at 3pm to email Sarah"
- **Calendar Management** - "Schedule a meeting with John tomorrow at 2pm"
- **Email Integration** - "Send an email to boss@company.com wishing them a good day"
- **Multi-Platform OAuth** - Google Calendar, Gmail, Microsoft 365, Outlook, and Slack
- **Daily Digest** - Morning briefing with emails, calendar, and messages
- **Native Notifications** - Desktop alerts for due reminders
- **Auto-Launch** - Optional startup with your system
- **Personality Customization** - Adjust Donna's tone from professional to playful

## Tech Stack

| Component | Technology |
|-----------|------------|
| **Desktop App** | Tauri (Rust + TypeScript/React) |
| **Backend API** | FastAPI (Python 3.10+) |
| **Database** | SQLite (local) / PostgreSQL (production) |
| **LLM** | Google Gemini 2.5 Flash |
| **Speech-to-Text** | Gemini multimodal / Groq Whisper (fallback) |
| **UI Framework** | TailwindCSS + Zustand |
| **Deployment** | Render (backend) / Local build (desktop) |

## Quick Start

### Prerequisites

- **Node.js** 18+ ([nodejs.org](https://nodejs.org))
- **Python** 3.10+ ([python.org](https://python.org))
- **Rust** (for Tauri) - Install from [rustup.rs](https://rustup.rs)
- **Gemini API Key** - Get from [Google AI Studio](https://makersuite.google.com/app/apikey)

---

## Local Development Setup

### 1. Clone the Repository

```bash
git clone https://github.com/rishis12/donna.git
cd donna
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create environment file
cp .env.example .env
```

Edit `backend/.env` with your credentials:

```env
# Required
SECRET_KEY=your-secret-key-min-32-chars
ENCRYPTION_KEY=your-encryption-key-32-bytes
GEMINI_API_KEY=your-gemini-api-key

# Database (SQLite for local dev)
DATABASE_URL=sqlite+aiosqlite:///./agent.db

# Google OAuth (for Calendar/Gmail)
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback

# Optional: Microsoft OAuth (for Outlook/Teams)
MICROSOFT_CLIENT_ID=your-microsoft-client-id
MICROSOFT_CLIENT_SECRET=your-microsoft-client-secret
MICROSOFT_REDIRECT_URI=http://localhost:8000/auth/microsoft/callback

# Optional: Slack
SLACK_CLIENT_ID=your-slack-client-id
SLACK_CLIENT_SECRET=your-slack-client-secret
SLACK_REDIRECT_URI=http://localhost:8000/auth/slack/callback

# Optional: Groq (for Whisper audio fallback)
GROQ_API_KEY=your-groq-api-key
```

Start the backend:

```bash
# From backend/ directory
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`. View docs at `http://localhost:8000/docs`.

### 3. Desktop App Setup

```bash
cd desktop

# Install dependencies
npm install

# Install Tauri CLI
npm install -D @tauri-apps/cli

# Create environment file for API URL
echo "VITE_API_URL=http://localhost:8000" > .env

# Run in development mode
npx tauri dev
```

The first build will take a few minutes as Rust compiles dependencies.

---

## Production Deployment

### Backend on Render

1. **Create a Render account** at [render.com](https://render.com)

2. **Create a new Web Service** connected to your GitHub repo

3. **Configure settings:**
   - **Root Directory:** `backend`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

4. **Add environment variables** in Render dashboard:
   ```
   SECRET_KEY=<generate-secure-key>
   ENCRYPTION_KEY=<generate-32-byte-key>
   GEMINI_API_KEY=<your-gemini-key>
   DATABASE_URL=<your-postgres-url>
   GOOGLE_CLIENT_ID=<your-client-id>
   GOOGLE_CLIENT_SECRET=<your-client-secret>
   GOOGLE_REDIRECT_URI=https://your-app.onrender.com/auth/google/callback
   ```

5. **Update Google OAuth** redirect URIs in [Google Cloud Console](https://console.cloud.google.com) to include your Render URL

### Desktop App for Production

1. **Update `.env`** in `desktop/` to point to your Render backend:
   ```
   VITE_API_URL=https://your-app.onrender.com
   ```

2. **Build the app:**
   ```bash
   cd desktop
   npx tauri build
   ```

3. The installer will be in `desktop/src-tauri/target/release/bundle/`

---

## OAuth Configuration

### Google (Calendar & Gmail)

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project or select existing
3. Enable **Google Calendar API** and **Gmail API**
4. Go to **APIs & Services > Credentials**
5. Create **OAuth 2.0 Client ID** (Web application)
6. Add redirect URIs:
   - `http://localhost:8000/auth/google/callback` (development)
   - `https://your-app.onrender.com/auth/google/callback` (production)
7. Go to **OAuth consent screen**:
   - Add your email as a test user (for testing mode)
   - Or publish the app for production use
8. Copy Client ID and Secret to your `.env`

### Microsoft 365 (Outlook & Teams)

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to **Azure Active Directory > App registrations**
3. Register a new application
4. Add redirect URIs (Web platform):
   - `http://localhost:8000/auth/microsoft/callback`
   - `https://your-app.onrender.com/auth/microsoft/callback`
5. Create a client secret under **Certificates & secrets**
6. Copy Application (client) ID and Secret to your `.env`

### Slack

1. Go to [Slack API](https://api.slack.com/apps)
2. Create a new app from scratch
3. Add OAuth scopes: `channels:history`, `channels:read`, `chat:write`, `users:read`
4. Add redirect URLs:
   - `http://localhost:8000/auth/slack/callback`
   - `https://your-app.onrender.com/auth/slack/callback`
5. Install to your workspace
6. Copy Client ID and Secret to your `.env`

---

## Usage

### Getting Started

1. **Launch the app** - Click the system tray icon or press `Ctrl+Shift+Space`
2. **Sign in** - Connect with Google or Microsoft (one-click OAuth)
3. **Start chatting** - Type or speak your requests naturally

### Example Commands

**Reminders:**
- "Remind me at 3pm to take a break"
- "Remind me tomorrow morning to check emails"
- "Set a reminder for Friday at noon to submit report"

**Calendar:**
- "What's on my schedule today?"
- "Schedule a meeting with Sarah tomorrow at 2pm"
- "Move my 3pm meeting to 4pm"
- "Cancel my meeting with John"

**Email:**
- "Send an email to john@example.com wishing him a good day"
- "Draft an email to my professor asking for an extension"
- "Mark all emails as read"

**Communication Summary:**
- "Summarize my communications"
- "What emails do I have?"
- "Give me my daily digest"

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+Shift+Space` | Toggle window visibility |
| Click tray icon | Show window |

---

## API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/auth/register` | POST | Create account |
| `/auth/login` | POST | Login |
| `/auth/me` | GET | Get current user |
| `/auth/google` | GET | Start Google OAuth |
| `/auth/google/callback` | GET | Google OAuth callback |
| `/auth/microsoft` | GET | Start Microsoft OAuth |
| `/auth/slack` | GET | Start Slack OAuth |
| `/utterance/process` | POST | Process text command |
| `/utterance/voice` | POST | Process voice command |
| `/action/confirm` | POST | Confirm pending action |
| `/reminders/create` | POST | Create reminder |
| `/reminders/list` | GET | List reminders |
| `/calendar/events` | GET | List calendar events |
| `/calendar/create` | POST | Create event |
| `/email/draft` | POST | Draft email |
| `/email/send` | POST | Send email |
| `/digest/daily` | GET | Get daily digest |
| `/summary/communications` | GET | Summarize communications |

---

## Project Structure

```
donna/
├── backend/                    # FastAPI backend
│   ├── app/
│   │   ├── api/routes/        # API endpoints
│   │   ├── core/              # Config, security, middleware
│   │   ├── models/            # SQLAlchemy models
│   │   ├── services/          # LLM service, reminders
│   │   ├── integrations/      # Google, Microsoft, Slack
│   │   └── crud/              # Database operations
│   ├── alembic/               # Database migrations
│   ├── requirements.txt
│   └── .env.example
├── desktop/                    # Tauri desktop app
│   ├── src/
│   │   ├── components/        # React components
│   │   ├── stores/            # Zustand state
│   │   └── lib/               # API client
│   ├── src-tauri/             # Rust backend
│   └── package.json
├── deploy/                     # Deployment configs
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── env.example
└── README.md
```

---

## Troubleshooting

### Backend Issues

**"Module not found" errors:**
```bash
pip install -r requirements.txt
```

**Database errors:**
```bash
# Reset the database
rm backend/agent.db
# Restart the backend - tables will be recreated
```

**Gemini API errors:**
- Verify your `GEMINI_API_KEY` is correct
- Check [Google AI Studio](https://makersuite.google.com) for API status
- Ensure the API key has access to Gemini 2.5 Flash

### Desktop App Issues

**"tauri not found":**
```bash
npm install -D @tauri-apps/cli
npx tauri dev
```

**Rust build errors:**
- Install Visual Studio Build Tools (Windows)
- Run `rustup update`

**Can't connect to backend:**
- Check backend is running on port 8000
- Verify `VITE_API_URL` in `desktop/.env`

### OAuth Issues

**"Access blocked" error:**
- Add your email as a test user in Google Cloud Console
- Or publish the OAuth consent screen

**Redirect URI mismatch:**
- Ensure redirect URIs match exactly in Google/Azure console
- Check for trailing slashes

---

## Environment Variables Reference

### Backend (`backend/.env`)

| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | Yes | JWT signing key (min 32 chars) |
| `ENCRYPTION_KEY` | Yes | Token encryption key (32 bytes) |
| `GEMINI_API_KEY` | Yes | Google Gemini API key |
| `DATABASE_URL` | Yes | Database connection string |
| `GOOGLE_CLIENT_ID` | For Google | OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | For Google | OAuth client secret |
| `GOOGLE_REDIRECT_URI` | For Google | OAuth callback URL |
| `MICROSOFT_CLIENT_ID` | For Microsoft | Azure app client ID |
| `MICROSOFT_CLIENT_SECRET` | For Microsoft | Azure client secret |
| `SLACK_CLIENT_ID` | For Slack | Slack app client ID |
| `SLACK_CLIENT_SECRET` | For Slack | Slack client secret |
| `GROQ_API_KEY` | Optional | For Whisper audio fallback |

### Desktop (`desktop/.env`)

| Variable | Required | Description |
|----------|----------|-------------|
| `VITE_API_URL` | Yes | Backend API URL |

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

## Acknowledgments

- Inspired by Donna Paulsen from *Suits*
- Built with [Tauri](https://tauri.app), [FastAPI](https://fastapi.tiangolo.com), and [Google Gemini](https://ai.google.dev)
