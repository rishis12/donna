import os
from dotenv import load_dotenv
from functools import lru_cache
from pathlib import Path

# Load .env file
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

class Settings:
    """Simple settings class that loads from environment variables."""
    
    def __init__(self):
        # Server
        self.env: str = os.getenv("ENV", "development")
        self.secret_key: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
        self.database_url: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./agent.db")
        self.encryption_key: str = os.getenv("ENCRYPTION_KEY", "dev-encryption-key-32-bytes-long")
        
        # Gemini (for LLM)
        self.gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")

        # Groq (for Whisper audio transcription - fallback)
        self.groq_api_key: str = os.getenv("GROQ_API_KEY", "")
        
        # Base URL for OAuth redirects (environment-based)
        base_url = os.getenv("BASE_URL", "http://localhost:8000")
        
        # Google OAuth
        self.google_client_id: str = os.getenv("GOOGLE_CLIENT_ID", "")
        self.google_client_secret: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
        self.google_redirect_uri: str = os.getenv("GOOGLE_REDIRECT_URI", f"{base_url}/auth/google/callback")
        
        # Microsoft OAuth
        self.microsoft_client_id: str = os.getenv("MICROSOFT_CLIENT_ID", "")
        self.microsoft_client_secret: str = os.getenv("MICROSOFT_CLIENT_SECRET", "")
        self.microsoft_redirect_uri: str = os.getenv("MICROSOFT_REDIRECT_URI", f"{base_url}/auth/microsoft/callback")
        
        # Slack OAuth (for scalable deployment - replaces manual webhook setup)
        self.slack_client_id: str = os.getenv("SLACK_CLIENT_ID", "")
        self.slack_client_secret: str = os.getenv("SLACK_CLIENT_SECRET", "")
        self.slack_redirect_uri: str = os.getenv("SLACK_REDIRECT_URI", f"{base_url}/auth/slack/callback")

        # Messaging Platform Bots/Webhooks
        self.discord_bot_token: str = os.getenv("DISCORD_BOT_TOKEN", "")
        self.slack_bot_token: str = os.getenv("SLACK_BOT_TOKEN", "")
        self.slack_signing_secret: str = os.getenv("SLACK_SIGNING_SECRET", "")

        # Webhook URLs (these can be set via API)
        self.discord_webhook_base_url: str = os.getenv("DISCORD_WEBHOOK_BASE_URL", "https://your-domain.com")
        self.slack_webhook_base_url: str = os.getenv("SLACK_WEBHOOK_BASE_URL", "https://your-domain.com")

@lru_cache()
def get_settings() -> Settings:
    return Settings()