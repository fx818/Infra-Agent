"""
GET /logs           — list available log dates (from filenames in logs/)
GET /logs/{date}    — return all rows for a given date as JSON
"""

import csv
import io
import os
from datetime import datetime, date
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/logs", tags=["logs"])

# backend/app/api/logs.py  → .parent = api  → .parent = app  → .parent = backend
LOGS_DIR = Path(__file__).resolve().parent.parent.parent / "logs"



def _logs_dir() -> Path:
    """Return the logs directory, creating it if missing."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    return LOGS_DIR


def _parse_csv_file(path: Path) -> list[dict[str, Any]]:
    rows = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
        reader = csv.DictReader(io.StringIO(text))
        for i, row in enumerate(reader):
            row["_id"] = i  # stable row index for frontend keying
            rows.append(dict(row))
    except Exception:
        pass
    return rows


@router.get("/dates")
def list_log_dates():
    """Return sorted list of dates that have log files, most-recent first."""
    d = _logs_dir()
    dates = []
    for f in sorted(d.glob("api_requests_*.csv"), reverse=True):
        stem = f.stem  # api_requests_YYYY-MM-DD
        date_str = stem.replace("api_requests_", "")
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            dates.append({"date": date_str, "filename": f.name, "size_bytes": f.stat().st_size})
        except ValueError:
            pass
    return dates


@router.get("/{log_date}")
def get_logs(
    log_date: str,
    method: str | None = Query(None),
    status: str | None = Query(None),
    path_filter: str | None = Query(None, alias="path"),
    limit: int = Query(500, le=2000),
    offset: int = Query(0, ge=0),
):
    """
    Fetch log rows for a specific date (format: YYYY-MM-DD).
    Supports optional filters: method, status (2xx/4xx/5xx or exact code), path substring.
    """
    try:
        datetime.strptime(log_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(400, "Invalid date format. Use YYYY-MM-DD.")

    log_file = _logs_dir() / f"api_requests_{log_date}.csv"
    if not log_file.exists():
        raise HTTPException(404, f"No log file found for {log_date}")

    rows = _parse_csv_file(log_file)

    # Apply filters
    filtered = []
    for row in rows:
        sc = row.get("status_code", "")
        m = row.get("method", "")
        p = row.get("path", "")

        if method and m.upper() != method.upper():
            continue

        if status:
            if status.endswith("xx"):
                prefix = status[0]
                if not str(sc).startswith(prefix):
                    continue
            elif sc != status:
                continue

        if path_filter and path_filter.lower() not in p.lower():
            continue

        filtered.append(row)

    total = len(filtered)
    page = filtered[offset: offset + limit]

    return {
        "date": log_date,
        "total": total,
        "offset": offset,
        "limit": limit,
        "rows": page,
    }
