"""HTTP security middleware, error formatting, and safe request logging."""
from __future__ import annotations

import json
import logging
import time
from uuid import uuid4

from fastapi import Request
from fastapi.responses import JSONResponse

from backend.app.config import MAX_BODY_BYTES

logger = logging.getLogger("gastrokg.api")

SECURITY_HEADERS: list[tuple[bytes, bytes]] = [
    (b"x-content-type-options", b"nosniff"),
    (b"referrer-policy", b"no-referrer"),
    (b"content-security-policy", b"default-src 'none'; frame-ancestors 'none'"),
]


def error_payload(code: str, message: str, request_id: str, field: str | None = None) -> dict:
    item: dict[str, str | None] = {"code": code, "message": message}
    if field is not None:
        item["field"] = field
    return {"errors": [item], "requestId": request_id}


def request_id_of(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")


class SecurityMiddleware:
    """Enforce body size cap, JSON content type, security headers, and safe logging."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = uuid4().hex[:16]
        state = scope.setdefault("state", {})
        state["request_id"] = request_id

        method = scope.get("method", "GET")
        path = scope.get("path", "")
        raw_headers = {k.lower(): v for k, v in scope.get("headers", [])}
        started = time.perf_counter()
        status_code = 500

        async def send_with_headers(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                headers = list(message.get("headers", []))
                existing = {k.lower() for k, _ in headers}
                for key, val in SECURITY_HEADERS:
                    if key not in existing:
                        headers.append((key, val))
                if path.startswith("/api/consultations") and b"cache-control" not in existing:
                    headers.append((b"cache-control", b"no-store"))
                message = {**message, "headers": headers}
            await send(message)

        async def send_json_error(status: int, code: str, message: str):
            body = json.dumps(error_payload(code, message, request_id)).encode("utf-8")
            await send_with_headers({
                "type": "http.response.start",
                "status": status,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode("ascii")),
                ],
            })
            await send({"type": "http.response.body", "body": body})

        try:
            if method == "POST" and path == "/api/consultations":
                content_type = raw_headers.get(b"content-type", b"").decode("latin-1")
                media_type = content_type.split(";", 1)[0].strip().lower()
                if media_type != "application/json":
                    await send_json_error(
                        415, "unsupported_media_type", "Content-Type must be application/json."
                    )
                    return

            if method in ("POST", "PUT", "PATCH"):
                cl_raw = raw_headers.get(b"content-length")
                if cl_raw is not None:
                    try:
                        cl = int(cl_raw.decode("ascii"))
                    except ValueError:
                        await send_json_error(413, "too_large", "Invalid Content-Length.")
                        return
                    if cl < 0 or cl > MAX_BODY_BYTES:
                        await send_json_error(413, "too_large", "Request body exceeds 64 KB.")
                        return

                chunks: list[bytes] = []
                total = 0
                while True:
                    event = await receive()
                    if event["type"] != "http.request":
                        break
                    chunk = event.get("body", b"")
                    total += len(chunk)
                    if total > MAX_BODY_BYTES:
                        await send_json_error(413, "too_large", "Request body exceeds 64 KB.")
                        return
                    if chunk:
                        chunks.append(chunk)
                    if not event.get("more_body", False):
                        break

                body_bytes = b"".join(chunks)
                sent_body = False

                async def replay_receive():
                    nonlocal sent_body
                    if not sent_body:
                        sent_body = True
                        return {"type": "http.request", "body": body_bytes, "more_body": False}
                    return await receive()

                await self.app(scope, replay_receive, send_with_headers)
            else:
                await self.app(scope, receive, send_with_headers)
        finally:
            duration_ms = (time.perf_counter() - started) * 1000.0
            logger.info("%s %s -> %d (%.1fms) requestId=%s", method, path, status_code, duration_ms, request_id)


def error_response(status: int, code: str, message: str, request_id: str, field: str | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content=error_payload(code, message, request_id, field=field),
    )
