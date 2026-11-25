"""Rules listing endpoint."""
from __future__ import annotations

from fastapi import APIRouter

from backend.app.store import get_store

router = APIRouter()


@router.get("/api/rules")
def get_rules() -> dict:
    return get_store().rules_payload
