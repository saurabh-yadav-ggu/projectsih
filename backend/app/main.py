import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.routers import auth, threads, chat, memory, upload

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app.main")

# Initialize SQLite database tables on startup
init_db()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Shield AI - Persistent Conversation Memory & RAG Agent API"
)

frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        frontend_url,
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Routers
app.include_router(auth.router)
app.include_router(threads.router)
app.include_router(chat.router)
app.include_router(memory.router)
app.include_router(upload.router)


@app.get("/")
@app.get("/health")
def health_check():
    return {
        "status": "online",
        "app": settings.PROJECT_NAME,
        "version": settings.VERSION
    }
