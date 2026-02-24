from __future__ import annotations
import json
import base64
import requests
import streamlit as st

GITHUB_REPO = "bkpgeneralholdings/networth-tracker"
SNAPSHOTS_FILE = "snapshots.json"
GITHUB_API = "https://api.github.com"


def _get_token() -> str:
    return st.secrets["GITHUB_TOKEN"]


def _get_headers() -> dict:
    return {
        "Authorization": f"token {_get_token()}",
        "Accept": "application/vnd.github.v3+json",
    }


def _fetch_file() -> tuple[list, str | None]:
    """Fetch snapshots.json from GitHub. Returns (snapshots_list, sha)."""
    url = f"{GITHUB_API}/repos/{GITHUB_REPO}/contents/{SNAPSHOTS_FILE}"
    resp = requests.get(url, headers=_get_headers())
    if resp.status_code == 404:
        return [], None
    resp.raise_for_status()
    data = resp.json()
    content = base64.b64decode(data["content"]).decode("utf-8")
    return json.loads(content), data["sha"]


def _write_file(snapshots: list, sha: str | None):
    """Write snapshots list to GitHub."""
    url = f"{GITHUB_API}/repos/{GITHUB_REPO}/contents/{SNAPSHOTS_FILE}"
    content = base64.b64encode(json.dumps(snapshots, indent=2).encode()).decode()
    payload = {
        "message": f"Update snapshots",
        "content": content,
    }
    if sha:
        payload["sha"] = sha
    resp = requests.put(url, headers=_get_headers(), json=payload)
    resp.raise_for_status()


def init_db():
    """No-op — GitHub is the storage backend."""
    pass


def save_snapshot(date: str, total_value: float, breakdown: dict):
    """Upsert a snapshot for the given date into GitHub."""
    snapshots, sha = _fetch_file()
    # Remove existing entry for this date if present
    snapshots = [s for s in snapshots if s["date"] != date]
    snapshots.append({
        "date": date,
        "total_value": total_value,
        "breakdown": breakdown,
    })
    snapshots.sort(key=lambda s: s["date"])
    _write_file(snapshots, sha)


def get_all_snapshots() -> list[dict]:
    """Return all snapshots ordered by date."""
    snapshots, _ = _fetch_file()
    return sorted(snapshots, key=lambda s: s["date"])


def get_latest_snapshot() -> dict | None:
    """Return the most recent snapshot, or None."""
    snapshots, _ = _fetch_file()
    if not snapshots:
        return None
    return sorted(snapshots, key=lambda s: s["date"])[-1]
