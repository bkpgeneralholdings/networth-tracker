import sqlite3
import json
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data.db")


def _get_conn():
    return sqlite3.connect(DB_PATH)


def init_db():
    """Create the snapshots table if it doesn't exist."""
    conn = _get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT UNIQUE NOT NULL,
            total_value REAL NOT NULL,
            breakdown TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def save_snapshot(date: str, total_value: float, breakdown: dict):
    """Upsert a snapshot for the given date."""
    conn = _get_conn()
    conn.execute("""
        INSERT INTO snapshots (date, total_value, breakdown)
        VALUES (?, ?, ?)
        ON CONFLICT(date) DO UPDATE SET
            total_value = excluded.total_value,
            breakdown = excluded.breakdown
    """, (date, total_value, json.dumps(breakdown)))
    conn.commit()
    conn.close()


def get_all_snapshots() -> list[dict]:
    """Return all snapshots ordered by date."""
    conn = _get_conn()
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM snapshots ORDER BY date ASC").fetchall()
    conn.close()
    results = []
    for row in rows:
        results.append({
            "date": row["date"],
            "total_value": row["total_value"],
            "breakdown": json.loads(row["breakdown"]),
        })
    return results


def get_latest_snapshot() -> dict | None:
    """Return the most recent snapshot, or None."""
    conn = _get_conn()
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM snapshots ORDER BY date DESC LIMIT 1").fetchone()
    conn.close()
    if row is None:
        return None
    return {
        "date": row["date"],
        "total_value": row["total_value"],
        "breakdown": json.loads(row["breakdown"]),
    }
