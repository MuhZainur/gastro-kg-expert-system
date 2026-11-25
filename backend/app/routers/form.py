"""Form options endpoint."""
from __future__ import annotations

from fastapi import APIRouter

from backend.app.store import get_store

router = APIRouter()


@router.get("/api/form")
def get_form() -> dict:
    return get_store().vocabulary.form_payload
