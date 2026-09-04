"""FastAPI entrypoint. Phase 0: health, provider status, budget counter."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from services.llm import budget, cache, router

STORAGE = Path("storage")
STORAGE.mkdir(exist_ok=True)

app = FastAPI(title="AI Teacher", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ponytail: open CORS, demo app with no user data to protect
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/storage", StaticFiles(directory=str(STORAGE)), name="storage")


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "providers": router.available(),
        "cache": cache.stats(),
        "budget": budget.today(),
    }


@app.get("/budget")
def budget_today() -> dict:
    """Feeds the trace panel's request counter."""
    return budget.today()
