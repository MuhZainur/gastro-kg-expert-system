"""Health endpoint."""
from __future__ import annotations

from fastapi import APIRouter

from backend.app.config import VERSION
from backend.app.store import get_store

router = APIRouter()


@router.get("/api/health")
def health() -> dict:
    store = get_store()
    return {"status": "ok", "version": VERSION, "rules": len(store.rules)}
