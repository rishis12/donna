from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from .core.database import init_db
from .api.routes import auth, utterance, reminders, calendar, email, action

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(
    title="Desktop AI Agent API",
    description="Backend API for the Desktop AI Assistant",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(utterance.router)
app.include_router(reminders.router)
app.include_router(calendar.router)
app.include_router(email.router)
app.include_router(action.router)

@app.get("/")
async def root():
    return {"message": "Desktop AI Agent API", "version": "1.0.0"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

