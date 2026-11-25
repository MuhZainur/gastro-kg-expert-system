"""Ontology Turtle download endpoint using a fixed file map."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from backend.app.config import ONTOLOGY_FILES

router = APIRouter()


@router.get("/api/ontology/{name}")
def get_ontology(name: str) -> Response:
    entry = ONTOLOGY_FILES.get(name)
    if entry is None:
        raise HTTPException(status_code=404, detail="Ontology file not found.")
    path, filename = entry
    content = path.read_bytes()
    return Response(
        content=content,
        media_type="text/turtle; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
