# Desktop AI Agent

A cross-platform desktop AI assistant that sits in your system tray and helps you manage reminders, calendar events, and emails via text or voice.

## Features

- 🎯 **System Tray** - Always accessible, toggle with `Ctrl+Shift+Space`
- 💬 **Natural Language** - Chat with your assistant naturally
- 🎤 **Voice Input** - Push-to-talk microphone support
- ⏰ **Reminders** - "Remind me at 3pm to email Sarah"
- 📅 **Calendar** - "Move my 2pm meeting to Friday at 10" (with confirmation before creating)
- ✉️ **Email** - "Draft an email to my professor asking for an extension"
- 🔐 **OAuth** - Google Calendar, Gmail, Microsoft 365, and Slack support
- 📊 **Daily Digest** - Morning briefing with emails, calendar, and messages from all platforms
- 🔔 **Native Notifications** - Desktop alerts for due reminders
- 🚀 **Auto-Launch** - Optional startup with your system

## Tech Stack

- **Desktop**: Tauri (Rust + TypeScript/React)
- **Backend**: FastAPI (Python)
- **Database**: SQLite (local) / PostgreSQL (cloud)
- **LLM**: Groq (Llama 3.3 70B with fallback to Llama 3.1 8B)
- **STT**: Groq Whisper Large v3
- **UI**: TailwindCSS + Zustand

## Quick Start

### Prerequisites

- Node.js 18+
- Python 3.10+
- Rust (for Tauri) - Install from [rustup.rs](https://rustup.rs)
- Groq API Key

### 1. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate it
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment
# Create .env file with:
# SECRET_KEY=your-secret-key
# GROQ_API_KEY=your-groq-api-key
# GOOGLE_CLIENT_ID=your-google-client-id
# GOOGLE_CLIENT_SECRET=your-google-secret

# Run the backend
uvicorn app.main:app --reload
```

### 2. Desktop Setup

```bash
cd desktop

# Install dependencies
npm install

# Generate tray icons (required for system tray)
# Place icon.png (512x512) in src-tauri/icons/
# Then generate all sizes with:
npm run tauri icon src-tauri/icons/icon.png

# Run in development
npm run tauri dev
```

### 3. Usage

1. **Sign in** with Google or Microsoft (one-click, no separate registration needed!)
   - Your calendar and email access is connected automatically
2. Click the tray icon or press `Ctrl+Shift+Space` to toggle the window
3. Type or speak your request:
   - "Remind me at 5pm to call mom"
   - "Schedule a meeting with John tomorrow at 2pm"
   - "Draft an email to professor asking for extension"
4. Confirm actions when prompted
5. Optionally connect additional services from Settings (gear icon)

## OAuth Configuration

### Google

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project
3. Enable **Google Calendar API** and **Gmail API**
4. Go to Credentials → Create OAuth 2.0 Client ID
5. Add `http://localhost:8000/auth/google/callback` as redirect URI
6. Copy Client ID and Secret to your `.env`

### Microsoft 365

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to Azure Active Directory → App registrations
3. Register a new application
4. Add `http://localhost:8000/auth/microsoft/callback` as redirect URI
5. Create a client secret
6. Copy Application ID and Secret to your `.env`

### Slack

1. Go to [Slack API](https://api.slack.com/apps)
2. Create a new app
3. Add OAuth scopes: `channels:history`, `channels:read`, `users:read`
4. Add `http://localhost:8000/auth/slack/callback` as redirect URI
5. Copy Client ID and Secret to your `.env`

See `SETUP_SLACK.md` for detailed instructions.

## API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/auth/register` | POST | Create account |
| `/auth/login` | POST | Login |
| `/auth/me` | GET | Get current user |
| `/auth/google` | GET | Start Google OAuth |
| `/auth/microsoft` | GET | Start Microsoft OAuth |
| `/auth/slack` | GET | Start Slack OAuth |
| `/digest/summary` | GET | Get daily digest with emails, calendar, messages |
| `/utterance/process` | POST | Process text command |
| `/utterance/voice` | POST | Process voice command |
| `/action/confirm` | POST | Confirm/cancel pending action |
| `/reminders/create` | POST | Create reminder |
| `/reminders/list` | GET | List reminders |
| `/reminders/due` | GET | Get due reminders |
| `/calendar/events` | GET | List calendar events |
| `/calendar/create` | POST | Create event |
| `/calendar/update/{id}` | PATCH | Update event |
| `/email/draft` | POST | Draft email |
| `/email/send` | POST | Send email |

## Architecture

```
desktop-ai-agent/
├── backend/                    # FastAPI backend
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes/        # API endpoints
│   │   │   │   ├── auth.py    # Authentication
│   │   │   │   ├── utterance.py # LLM processing
│   │   │   │   ├── action.py  # Action confirmation
│   │   │   │   ├── reminders.py
│   │   │   │   ├── calendar.py
│   │   │   │   └── email.py
│   │   │   ├── deps.py        # Dependencies
│   │   │   └── schemas.py     # Pydantic models
│   │   ├── core/
│   │   │   ├── config.py      # Settings
│   │   │   ├── database.py    # SQLAlchemy setup
│   │   │   └── security.py    # JWT + encryption
│   │   ├── models/            # SQLAlchemy models
│   │   ├── services/
│   │   │   ├── llm_service.py # Groq/Llama integration
│   │   │   └── reminder_service.py
│   │   └── integrations/
│   │       ├── google_integration.py
│   │       ├── microsoft_integration.py
│   │       └── slack_integration.py
│   └── requirements.txt
├── desktop/                    # Tauri app
│   ├── src/
│   │   ├── components/
│   │   │   ├── CommandWindow.tsx
│   │   │   ├── LoginForm.tsx
│   │   │   └── SettingsPanel.tsx
│   │   ├── stores/
│   │   │   └── appStore.ts    # Zustand state
│   │   ├── lib/
│   │   │   └── api.ts         # HTTP client
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   └── index.css
│   └── src-tauri/
│       ├── src/
│       │   └── main.rs        # Rust backend
│       ├── Cargo.toml
│       └── tauri.conf.json
└── README.md
```

## Example Commands

**Reminders:**
- "Remind me at 3pm to take a break"
- "Remind me tomorrow morning to check emails"
- "Set a reminder for Friday at noon"

**Calendar:**
- "What's on my schedule today?"
- "Schedule a 30 minute call with Sarah at 2pm"
- "Move my 3pm meeting to 4pm"

**Email:**
- "Draft an email to john@example.com about the project update"
- "Send an email to my manager saying I'll be late"

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+Shift+Space` | Toggle window visibility |
| Click tray icon | Show window |

## Troubleshooting

**Backend won't start:**
- Ensure Python 3.10+ is installed
- Check `.env` file exists with required keys
- Verify `pip install -r requirements.txt` completed

**Tauri won't build:**
- Install Rust from rustup.rs
- On Windows, install Visual Studio Build Tools
- Run `npm run tauri icon` to generate icons

**Voice input not working:**
- Allow microphone access when prompted
- Ensure backend is running and Groq API key is valid

**OAuth not working:**
- Verify redirect URIs match exactly
- Check client ID/secret are correct
- Ensure APIs are enabled in Google/Azure console

## License

MIT

