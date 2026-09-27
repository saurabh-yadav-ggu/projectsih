import os
import sys
import logging
import asyncio

if sys.platform == "win32":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except Exception:
        pass

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.routers import auth, threads, chat, memory, upload, documents, skills, coding

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

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled server error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"},
    )

frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        frontend_url,
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_origin_regex=r"^https?://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Register Routers
app.include_router(auth.router)
app.include_router(threads.router)
app.include_router(chat.router)
app.include_router(memory.router)
app.include_router(upload.router)
app.include_router(documents.router)
app.include_router(skills.router)
app.include_router(coding.router)

from app.routers.coding import _handle_coding_websocket
from fastapi import WebSocket, Query

@app.websocket("/ws/coding")
async def ws_coding_endpoint(websocket: WebSocket, token: str | None = Query(None)):
    """Direct /ws/coding endpoint for coding agent streaming."""
    await _handle_coding_websocket(websocket, token=token)


@app.get("/")
@app.get("/health")
def health_check():
    return {
        "status": "online",
        "app": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "sandbox_backend": settings.SANDBOX_BACKEND,
    }


@app.get("/health/sandbox")
def sandbox_health():
    from app.sandbox.health import check_sandbox_health
    return check_sandbox_health()
