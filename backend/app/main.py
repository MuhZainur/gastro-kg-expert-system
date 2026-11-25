"""FastAPI application factory, middleware, error handlers, and router wiring."""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.app.config import VERSION, docs_enabled, get_allowed_origins
from backend.app.routers import consultations, form, health, ontology, rules
from backend.app.security import SecurityMiddleware, error_response, request_id_of
from backend.app.services.consultation import RequestValidationProblem
from backend.app.store import get_store

logger = logging.getLogger("gastrokg.api")


def _format_loc(loc: tuple) -> str | None:
    parts = [str(part) for part in loc if part != "body"]
    return ".".join(parts) if parts else None


def create_app() -> FastAPI:
    allow_docs = docs_enabled()
    application = FastAPI(
        title="GastroKG API",
        version=VERSION,
        docs_url="/docs" if allow_docs else None,
        redoc_url="/redoc" if allow_docs else None,
        openapi_url="/openapi.json" if allow_docs else None,
    )

    # Warm up the read-only knowledge store and set SPARQL_LOAD_GRAPHS = False
    get_store()

    application.include_router(health.router)
    application.include_router(form.router)
    application.include_router(rules.router)
    application.include_router(ontology.router)
    application.include_router(consultations.router)

    @application.exception_handler(RequestValidationProblem)
    async def handle_domain_validation(request: Request, exc: RequestValidationProblem):
        return error_response(422, exc.code, exc.message, request_id_of(request), field=exc.field)

    @application.exception_handler(RequestValidationError)
    async def handle_pydantic_validation(request: Request, exc: RequestValidationError):
        rid = request_id_of(request)
        errors = []
        for err in exc.errors():
            field = _format_loc(err.get("loc", ()))
            err_type = err.get("type", "")
            msg = "Malformed JSON request body." if err_type == "json_invalid" else str(err.get("msg", "Invalid input."))
            entry = {"code": "validation", "message": msg}
            if field:
                entry["field"] = field
            errors.append(entry)
        return JSONResponse(status_code=422, content={"errors": errors, "requestId": rid})

    @application.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request: Request, exc: StarletteHTTPException):
        code = "not_found" if exc.status_code == 404 else "http_error"
        message = "Resource not found." if exc.status_code == 404 else "Request could not be processed."
        return error_response(exc.status_code, code, message, request_id_of(request))

    @application.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception):
        rid = request_id_of(request)
        logger.error("Unhandled %s requestId=%s", type(exc).__name__, rid)
        return error_response(500, "internal", "An internal error occurred.", rid)

    application.add_middleware(GZipMiddleware, minimum_size=1024)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=get_allowed_origins(),
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
        allow_credentials=False,
    )
    application.add_middleware(SecurityMiddleware)
    return application


app = create_app()
