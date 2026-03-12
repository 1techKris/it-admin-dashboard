import asyncio
from datetime import datetime
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.modules.servers.models import Server, ServerStatusHistory
from app.modules.servers.scanner import ping_ip_ms

_MONITOR_TASK = None
_INTERVAL_SECONDS = 30  # tweak later or make configurable from Settings/Admin

async def _monitor_loop():
    while True:
        try:
            db: Session = SessionLocal()
            servers = db.query(Server).all()
            for s in servers:
                online, ping_ms = ping_ip_ms(s.ip_address)
                s.online = online
                if online:
                    s.last_seen = datetime.utcnow()
                # append history row
                hist = ServerStatusHistory(server_id=s.id, online=online, ping_ms=ping_ms)
                db.add(hist)
            db.commit()
            db.close()
        except Exception:
            # Avoid crashing the loop on transient errors
            try:
                db.rollback()
                db.close()
            except Exception:
                pass
        await asyncio.sleep(_INTERVAL_SECONDS)

def start_server_monitor():
    """
    Call this once at app startup (in main.py) to launch the background loop.
    """
    global _MONITOR_TASK
    if _MONITOR_TASK is None:
        _MONITOR_TASK = asyncio.create_task(_monitor_loop())