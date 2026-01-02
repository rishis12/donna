from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import logging
from pathlib import Path
from .core.database import init_db
from .core.middleware import LoggingMiddleware, setup_rate_limiting, limiter
from .core.scheduler import start_scheduler, shutdown_scheduler
from .api.routes import auth, utterance, reminders, calendar, email, action, digest, messages, summary
from .api.routes import messaging_accounts, webhook, onboarding, history
from .core.config import get_settings
from sqlalchemy import select

settings = get_settings()
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Donna AI Backend...")
    await init_db()
    start_scheduler()
    logger.info("Backend started successfully")
    yield
    # Shutdown
    logger.info("Shutting down Donna AI Backend...")
    shutdown_scheduler()
    logger.info("Backend shut down")

app = FastAPI(
    title="Desktop AI Agent API",
    description="Backend API for the Desktop AI Assistant",
    version="1.0.0",
    lifespan=lifespan
)

# Setup rate limiting
app = setup_rate_limiting(app)

# Add middleware
app.add_middleware(LoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (can restrict later if needed)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(utterance.router)
app.include_router(reminders.router)
app.include_router(calendar.router)
app.include_router(email.router)
app.include_router(action.router)
app.include_router(digest.router)
app.include_router(messages.router)
app.include_router(summary.router)
app.include_router(messaging_accounts.router)
app.include_router(webhook.router)
app.include_router(onboarding.router)
app.include_router(history.router)

# Serve landing page
# Try multiple paths to find landing.html (works in both local and deployed environments)
_landing_paths = [
    Path(__file__).parent / "landing.html",  # In app/ directory (deployed - copied by Dockerfile)
    Path(__file__).parent.parent / "landing.html",  # In backend/ directory
    Path(__file__).parent.parent.parent / "landing.html",  # Project root (local dev)
]

landing_page_path = None
for path in _landing_paths:
    if path.exists():
        landing_page_path = path
        logger.info(f"Found landing page at: {path}")
        break

if not landing_page_path:
    logger.warning("Landing page not found. API info will be served at root.")

@app.get("/")
async def root():
    """Serve landing page if available, otherwise return API info."""
    if landing_page_path and landing_page_path.exists():
        return FileResponse(landing_page_path, media_type="text/html")
    return {
        "message": "Desktop AI Agent API",
        "version": "1.0.0",
        "status": "running",
        "landing_page": "/landing"
    }

@app.get("/landing")
async def landing():
    """Serve the landing page."""
    if landing_page_path and landing_page_path.exists():
        return FileResponse(landing_page_path, media_type="text/html")
    return {"error": "Landing page not found"}

@app.get("/health")
async def health():
    """Enhanced health check endpoint."""
    from .core.scheduler import scheduler
    from .core.database import engine
    
    try:
        # Check database connection
        from sqlalchemy import text
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        db_status = "unhealthy"
    
    # Check scheduler
    scheduler_status = "running" if scheduler.running else "stopped"
    
    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "database": db_status,
        "scheduler": scheduler_status,
        "version": "1.0.0"
    }

