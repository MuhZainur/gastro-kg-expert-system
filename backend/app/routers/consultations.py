"""Consultation reasoning endpoint."""
from __future__ import annotations

from fastapi import APIRouter

from backend.app.schemas import ConsultationRequest
from backend.app.services.consultation import run_consultation
from backend.app.store import get_store

router = APIRouter()


@router.post("/api/consultations")
def create_consultation(body: ConsultationRequest) -> dict:
    return run_consultation(get_store(), body)
