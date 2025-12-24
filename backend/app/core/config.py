from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # Server
    secret_key: str = "dev-secret-key-change-in-production"
    database_url: str = "sqlite+aiosqlite:///./agent.db"
    encryption_key: str = "dev-encryption-key-32-bytes-long"
    
    # Groq (for LLM and Whisper)
    groq_api_key: str = ""
    
    # Google OAuth
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/auth/google/callback"
    
    # Microsoft OAuth
    microsoft_client_id: str = ""
    microsoft_client_secret: str = ""
    microsoft_redirect_uri: str = "http://localhost:8000/auth/microsoft/callback"
    
    class Config:
        env_file = ".env"

@lru_cache()
def get_settings() -> Settings:
    return Settings()

