import re
import requests
from datetime import datetime, timezone

from app.core.config import settings

HEADERS = {
    "X-API-Key": settings.BC_AGENT_API_KEY
}

DATE_RE = re.compile(r"/Date\((\d+)\)/")


def _parse_ps_date(value: str | None):
    """
    Convert PowerShell /Date(x)/ timestamps to ISO-8601.
    """
    if not value:
        return None

    match = DATE_RE.match(value)
    if not match:
        return value

    ms = int(match.group(1))
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat()


def get_bc_sessions():
    """
    Fetch and normalize Business Central sessions from the BC agent.
    """
    url = f"{settings.BC_AGENT_URL}/sessions"
    resp = requests.get(url, headers=HEADERS, timeout=10)
    resp.raise_for_status()

    raw = resp.json()
    sessions = raw if isinstance(raw, list) else [raw]

    normalized = []
    for s in sessions:
        normalized.append({
            "sessionId": s.get("SessionID"),
            "user": s.get("UserID") or "(service / system)",
            "clientType": s.get("ClientType"),

            "loginTime": _parse_ps_date(s.get("LoginDatetime")),
            "lastActive": _parse_ps_date(s.get("LastActiveTime")),

            "idleTime": str(s.get("IdleTime"))
            if s.get("IdleTime") is not None
            else "—",
        })

    return normalized


def kill_bc_session(session_id: int):
    """
    Kill a specific Business Central session.
    """
    url = f"{settings.BC_AGENT_URL}/kill"
    payload = {"sessionId": session_id}

    resp = requests.post(url, json=payload, headers=HEADERS, timeout=10)
    resp.raise_for_status()

    return resp.json()