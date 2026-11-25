"""Application settings, limits, and static ontology file map."""
from __future__ import annotations

import os
from pathlib import Path

from backend.app import engine

VERSION = "1.0.0"

MAX_BODY_BYTES = 64 * 1024
MAX_EXTRA_BYTES = 4096
MAX_EXTRA_TRIPLES = 40
MAX_LITERAL_LEN = 200

DEFAULT_ORIGINS = "http://127.0.0.1:5500,http://localhost:5500"

DISCLAIMER = (
    "Educational prototype, not a medical device. "
    "Certainty weights are illustrative and have not been clinically validated."
)

ONTOLOGY_FILES: dict[str, tuple[Path, str]] = {
    "tbox": (engine.TBOX, "gastrokg-tbox.ttl"),
    "knowledge": (engine.KNOWLEDGE, "gastrokg-knowledge.ttl"),
    "cases": (engine.CASES, "gastrokg-cases.ttl"),
    "shapes": (engine.SHAPES, "gastrokg-shapes.ttl"),
}


def get_allowed_origins() -> list[str]:
    raw = os.environ.get("FRONTEND_ORIGINS", DEFAULT_ORIGINS)
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def docs_enabled() -> bool:
    return os.environ.get("ENABLE_DOCS", "false").strip().lower() == "true"
