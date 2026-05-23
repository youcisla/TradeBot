"""FastAPI HTTP server — serves the trading bot's REST API."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup and shutdown hooks."""
    # Startup: nothing needed yet; adapter connections are lazy
    logger.info("API server starting")
    yield
    # Shutdown: flush event logs, close MT5 connection if open
    logger.info("API server shutting down")


def create_app() -> FastAPI:
    """Factory — returns a configured FastAPI instance."""
    app = FastAPI(
        title="PulseTrade Bot API",
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS — allow dashboard (Next.js) to call the API
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",   # local dev
            "https://*.vercel.app",    # Vercel preview/prod
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount auth routes
    from api.routes import auth as auth_module
    app.include_router(auth_module.router, prefix="/api/auth", tags=["auth"])

    return app


app = create_app()