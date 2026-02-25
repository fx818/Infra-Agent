"""
Request/Response Logger Middleware.

Logs every API request and response to a daily-rotating CSV file at
backend/logs/api_requests_YYYY-MM-DD.csv with full timestamp, method,
path, status code, duration, and body snippets.
"""

import csv
import io
import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)

# Directory where CSV logs are written (relative to project root, or absolute)
LOGS_DIR = Path(__file__).resolve().parent.parent.parent / "logs"

CSV_HEADERS = [
    "timestamp",
    "method",
    "path",
    "query_params",
    "status_code",
    "duration_ms",
    "user_agent",
    "request_body",
    "response_body",
    "error",
]


def _get_csv_path() -> Path:
    """Return today's log file path."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return LOGS_DIR / f"api_requests_{date_str}.csv"


def _ensure_csv_header(path: Path) -> None:
    """Write CSV header if the file is new/empty."""
    if not path.exists() or path.stat().st_size == 0:
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(CSV_HEADERS)


def _truncate(value: str, max_len: int = 500) -> str:
    """Truncate long strings for CSV readability."""
    if len(value) > max_len:
        return value[:max_len] + "...[truncated]"
    return value


def _safe_json_full(body_bytes: bytes) -> str:
    """Convert raw bytes to a safe full string for CSV (no truncation)."""
    if not body_bytes:
        return ""
    try:
        decoded = body_bytes.decode("utf-8", errors="replace")
        parsed = json.loads(decoded)
        # Remove sensitive fields
        if isinstance(parsed, dict):
            for key in ("password", "secret", "api_key", "token", "access_key"):
                if key in parsed:
                    parsed[key] = "***"
        return json.dumps(parsed, ensure_ascii=False)
    except Exception:
        return body_bytes.decode("utf-8", errors="replace")


def _write_log_row(row: dict) -> None:
    """Append a single row to the daily CSV log file."""
    try:
        path = _get_csv_path()
        _ensure_csv_header(path)
        with open(path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
            writer.writerow(row)
    except Exception as e:
        logger.warning("Failed to write request log: %s", e)


class RequestLoggerMiddleware(BaseHTTPMiddleware):
    """
    Middleware that logs every HTTP request and response to a CSV file.

    Skips logging for: /docs, /openapi.json, /redoc, and static files.
    """

    SKIP_PATHS = {"/docs", "/openapi.json", "/redoc", "/favicon.ico", "/"}

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip logging for health/docs endpoints
        if request.url.path in self.SKIP_PATHS:
            return await call_next(request)

        start_time = time.perf_counter()
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        # Read request body (must be done before forwarding)
        request_body_bytes = await request.body()
        request_body_snippet = _safe_json_full(request_body_bytes)

        # Rebuild the receive channel so the body is still available to the handler
        async def receive():
            return {"type": "http.request", "body": request_body_bytes, "more_body": False}

        request = Request(request.scope, receive)

        # Call the actual handler
        error_detail = ""
        response_body_snippet = ""
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code

            # Capture response body
            response_body_chunks = []
            async for chunk in response.body_iterator:
                response_body_chunks.append(chunk)
            response_body_bytes = b"".join(response_body_chunks)
            response_body_snippet = _safe_json_full(response_body_bytes)

            # Extract error detail from non-2xx responses
            if status_code >= 400:
                try:
                    parsed = json.loads(response_body_bytes)
                    error_detail = str(parsed.get("detail", ""))
                except Exception:
                    error_detail = response_body_bytes.decode("utf-8", errors="replace")

            # Rebuild response with the already-consumed body
            response = Response(
                content=response_body_bytes,
                status_code=status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
            )

        except Exception as exc:
            error_detail = str(exc)
            logger.exception("Unhandled exception in request: %s %s", request.method, request.url.path)
            response = Response(
                content=json.dumps({"detail": "Internal server error"}).encode(),
                status_code=500,
                media_type="application/json",
            )

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        _write_log_row({
            "timestamp": timestamp,
            "method": request.method,
            "path": request.url.path,
            "query_params": str(request.query_params) if request.query_params else "",
            "status_code": status_code,
            "duration_ms": duration_ms,
            "user_agent": request.headers.get("user-agent", "")[:100],
            "request_body": request_body_snippet,
            "response_body": response_body_snippet,
            "error": error_detail,
        })

        # Log to Python logger as well (visible in terminal)
        log_fn = logger.warning if status_code >= 400 else logger.info
        log_fn(
            "%s %s → %d  (%.1fms)",
            request.method,
            request.url.path,
            status_code,
            duration_ms,
        )

        return response
