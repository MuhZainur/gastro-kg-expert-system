"""Local static server for frontend/ applying the security headers of frontend/vercel.json.

Run:  python scripts/serve_frontend.py [--port 5500]
"""
from __future__ import annotations

import argparse
import functools
import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"


def load_security_headers() -> list[tuple[str, str]]:
    vercel_cfg = json.loads((FRONTEND / "vercel.json").read_text(encoding="utf-8"))
    headers: list[tuple[str, str]] = []
    for item in vercel_cfg["headers"][0]["headers"]:
        key, value = item["key"], item["value"]
        if key.lower() == "content-security-policy":
            value = value.replace("connect-src 'self'", "connect-src 'self' http://127.0.0.1:8000")
        headers.append((key, value))
    return headers


class SecureFrontendHandler(SimpleHTTPRequestHandler):
    extensions_map = {
        **SimpleHTTPRequestHandler.extensions_map,
        ".js": "application/javascript; charset=utf-8",
        ".mjs": "application/javascript; charset=utf-8",
        ".css": "text/css; charset=utf-8",
        ".json": "application/json; charset=utf-8",
        ".svg": "image/svg+xml",
        ".html": "text/html; charset=utf-8",
    }

    def end_headers(self) -> None:
        for key, value in load_security_headers():
            self.send_header(key, value)
        super().end_headers()

    def log_message(self, format: str, *args) -> None:
        # Keep local logs concise and free of query strings/sensitive info
        pass


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5500)
    args = parser.parse_args()

    handler = functools.partial(SecureFrontendHandler, directory=str(FRONTEND))
    server = ThreadingHTTPServer((args.host, args.port), handler)
    print(f"Serving frontend/ on http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
