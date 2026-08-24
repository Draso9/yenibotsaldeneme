"""Application factory for the future mobile/web IZFIN backend."""

from __future__ import annotations

from fastapi import FastAPI

from .routers import api_router


def create_app() -> FastAPI:
    """Create an API instance without importing or initializing Streamlit."""
    app = FastAPI(title="IZFIN API", version="0.1.0")
    app.include_router(api_router)
    return app


app = create_app()
