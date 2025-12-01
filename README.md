# Desktop AI Agent

A cross-platform desktop AI assistant that sits in your system tray and helps you manage reminders, calendar events, and emails via text or voice.

## Features

- 🎯 **System Tray** - Always accessible, toggle with `Ctrl+Shift+Space`
- 💬 **Natural Language** - Chat with your assistant naturally
- 🎤 **Voice Input** - Push-to-talk microphone support
- ⏰ **Reminders** - "Remind me at 3pm to email Sarah"
- 📅 **Calendar** - "Move my 2pm meeting to Friday at 10"
- ✉️ **Email** - "Draft an email to my professor asking for an extension"
- 🔐 **OAuth** - Google Calendar, Gmail, and Microsoft 365 support

## Tech Stack

- **Desktop**: Tauri (Rust + TypeScript/React)
- **Backend**: FastAPI (Python)
- **Database**: PostgreSQL (cloud) / SQLite (local)
- **LLM**: OpenAI GPT-4o
- **STT**: OpenAI Whisper

## Setup

### Prerequisites

- Node.js 18+
- Python 3.10+
- Rust (for Tauri)
- PostgreSQL (optional, SQLite works for local dev)

### Backend Setup

```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # macOS/Linux

pip install -r requirements.txt
cp .env.example .env
# Edit .env with your API keys

uvicorn app.main:app --reload
```

### Desktop Setup

```bash
cd desktop
npm install
npm run tauri dev
```

## OAuth Configuration

### Google

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a project and enable Calendar API + Gmail API
3. Create OAuth 2.0 credentials
4. Add `http://localhost:8000/auth/google/callback` as redirect URI
5. Copy Client ID and Secret to `.env`

### Microsoft (Optional)

1. Go to [Azure Portal](https://portal.azure.com)
2. Register an application in Azure AD
3. Add `http://localhost:8000/auth/microsoft/callback` as redirect URI
4. Copy Application ID and Secret to `.env`

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/auth/register` | POST | Create account |
| `/auth/login` | POST | Login |
| `/utterance/process` | POST | Process text command |
| `/utterance/voice` | POST | Process voice command |
| `/reminders/create` | POST | Create reminder |
| `/reminders/list` | GET | List reminders |
| `/calendar/events` | GET | List calendar events |
| `/calendar/create` | POST | Create event |
| `/email/draft` | POST | Draft email |
| `/email/send` | POST | Send email |

## Architecture

```
desktop-ai-agent/
├── backend/           # FastAPI backend
│   ├── app/
│   │   ├── api/       # Routes
│   │   ├── core/      # Config, security, database
│   │   ├── models/    # SQLAlchemy models
│   │   ├── services/  # Business logic
│   │   └── integrations/  # Google, Microsoft APIs
│   └── requirements.txt
├── desktop/           # Tauri app
│   ├── src/           # React frontend
│   └── src-tauri/     # Rust backend
└── README.md
```

## License

MIT

