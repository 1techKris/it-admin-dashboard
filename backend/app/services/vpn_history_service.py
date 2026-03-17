# backend/app/services/vpn_history_service.py

from datetime import datetime, timezone
import json
from sqlalchemy.exc import SQLAlchemyError
from app.db.vpn_history_db import SessionLocal, engine
from app.models.vpn_history import VPNHistory


def init_history_db():
    """Creates the vpn_history table on startup."""
    from app.models.vpn_history import Base
    Base.metadata.create_all(bind=engine)


def _safe_str(value):
    """Convert list/dict/anything into a string suitable for DB storage."""
    if value is None:
        return None
    if isinstance(value, list):
        if len(value) == 0:
            return None
        return str(value[0])
    if isinstance(value, dict):
        return json.dumps(value)
    return str(value)


def _parse_iso(value):
    """Parse ISO timestamps safely."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def _duration_seconds(dur):
    """
    Normalize duration from:
     - {"Hours": x, "Minutes": y, "Seconds": z}
     - integer seconds
     - weird formats
    """
    if dur is None:
        return None

    if isinstance(dur, int):
        return dur

    if isinstance(dur, dict):
        h = int(dur.get("Hours", 0) or 0)
        m = int(dur.get("Minutes", 0) or 0)
        s = int(dur.get("Seconds", 0) or 0)
        return h * 3600 + m * 60 + s

    return None


def record_vpn_sessions(session_list: list):
    db = SessionLocal()
    try:
        for s in session_list:
            username = _safe_str(s.get("Username"))
            ipv4 = _safe_str(s.get("ClientIPv4Address"))
            from_ip = _safe_str(s.get("ConnectedFrom"))

            geo = s.get("Geo") or {}
            geo_country = geo.get("country")
            geo_city = geo.get("city")
            geo_isp = geo.get("isp")
            geo_org = geo.get("org")

            start = _parse_iso(s.get("ConnectionStartTime"))
            duration = _duration_seconds(s.get("ConnectionDuration"))

            rec = VPNHistory(
                username=username,
                ipv4=ipv4,
                connected_from=from_ip,
                geo_country=geo_country,
                geo_city=geo_city,
                geo_isp=geo_isp,
                geo_org=geo_org,
                start_time=start,
                duration_seconds=duration,
                timestamp_logged=datetime.utcnow(),
                raw_json=json.dumps(s),
            )

            db.add(rec)

        db.commit()
    except SQLAlchemyError:
        db.rollback()
    finally:
        db.close()