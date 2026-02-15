"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.agents import disconnect_all_clients
from app.config import settings
from app.database import init_db
from app.redis_client import connect_redis, disconnect_redis
from app.routes import chat, health, sessions


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: init DB + Redis. Shutdown: disconnect clients + Redis."""
    await init_db()
    await connect_redis()
    yield
    await disconnect_all_clients()
    await disconnect_redis()


app = FastAPI(
    title="Velocity",
    description="AI PM Agent — Backend API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(sessions.router)
app.include_router(chat.router)
