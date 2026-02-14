"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.agent import cleanup_all_sessions
from app.config import settings
from app.routes import chat, health, sessions


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await cleanup_all_sessions()


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
