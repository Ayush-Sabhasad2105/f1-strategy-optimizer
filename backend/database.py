# backend/database.py
"""
Lightweight SQLAlchemy connection pool for the FastAPI backend.

Uses a module-level engine (created once at import time) so the connection
pool is shared across all requests rather than reconnecting on every call.
"""
import os
import sys

# Ensure the project root is on sys.path so .env resolves correctly
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

_db_url = os.getenv("DATABASE_URL")
if not _db_url:
    raise RuntimeError("DATABASE_URL is not set. Add it to your .env file.")

# pool_pre_ping keeps stale connections from surfacing after a DB restart
engine = create_engine(_db_url, pool_pre_ping=True)


def get_all_track_profiles() -> list[dict]:
    """Return every row from track_profiles as a list of dicts."""
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT
                circuit_name,
                total_laps,
                base_lap_time_ms,
                pit_loss_ms,
                tire_deg_ms_per_lap,
                cluster,
                cluster_label,
                data_points,
                last_updated
            FROM track_profiles
            ORDER BY cluster, circuit_name;
        """)).mappings().all()
    return [dict(r) for r in rows]


def get_track_profile(circuit_name: str) -> dict | None:
    """Return a single track profile by (case-insensitive) circuit name, or None."""
    with engine.connect() as conn:
        row = conn.execute(text("""
            SELECT
                circuit_name,
                total_laps,
                base_lap_time_ms,
                pit_loss_ms,
                tire_deg_ms_per_lap,
                cluster,
                cluster_label,
                data_points,
                last_updated
            FROM track_profiles
            WHERE LOWER(circuit_name) LIKE LOWER(:name)
            LIMIT 1;
        """), {"name": f"%{circuit_name}%"}).mappings().one_or_none()
    return dict(row) if row else None
