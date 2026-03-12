from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from collections import Counter

from app.core.security import require_login, get_role_for
from app.core.database import SessionLocal

# Models
from app.modules.servers.models import Server, ServerStatusHistory, ServerGroup
from app.modules.printers.models import Printer
from app.modules.network_scanner.models import ScannedHost

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


# -----------------------------
# DB dependency
# -----------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# -----------------------------
# DASHBOARD HOME (container page)
# -----------------------------
@router.get("/", response_class=HTMLResponse)
async def dashboard_home(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_login)
):
    role = get_role_for(user)

    return templates.TemplateResponse(
        "dashboard/index.html",
        {
            "request": request,
            "user": user,
            "role": role,
            "active": "dashboard",
            "title": "Dashboard",
        }
    )


# -----------------------------
# PARTIAL: Top tiles
# -----------------------------
@router.get("/tiles", response_class=HTMLResponse)
async def dash_tiles(request: Request, db: Session = Depends(get_db), user=Depends(require_login)):
    servers = db.query(Server).all()
    total_servers = len(servers)
    online_servers = sum(1 for s in servers if s.online)
    offline_servers = total_servers - online_servers

    printers = db.query(Printer).count()
    scanned = db.query(ScannedHost).all()
    scanned_count = len(scanned)
    monitored_count = sum(1 for h in scanned if getattr(h, "monitored", False))

    return templates.TemplateResponse(
        "dashboard/_tiles.html",
        {
            "request": request,
            "total_servers": total_servers,
            "online_servers": online_servers,
            "offline_servers": offline_servers,
            "printer_count": printers,
            "scanned_hosts": scanned_count,
            "monitored_hosts": monitored_count,
        }
    )


# -----------------------------
# PARTIAL: Recent server events (last hour)
# -----------------------------
@router.get("/events", response_class=HTMLResponse)
async def dash_events(request: Request, db: Session = Depends(get_db), user=Depends(require_login)):
    lookback = datetime.utcnow() - timedelta(hours=1)
    events = (
        db.query(ServerStatusHistory)
        .filter(ServerStatusHistory.ts >= lookback)
        .order_by(ServerStatusHistory.ts.desc())
        .limit(30)
        .all()
    )
    return templates.TemplateResponse(
        "dashboard/_events.html",
        {
            "request": request,
            "events": events,
        }
    )


# -----------------------------
# PARTIAL: Groups summary
# -----------------------------
@router.get("/groups", response_class=HTMLResponse)
async def dash_groups(request: Request, db: Session = Depends(get_db), user=Depends(require_login)):
    groups = db.query(ServerGroup).all()
    group_counts = {g.name: len(g.members) for g in groups}
    return templates.TemplateResponse(
        "dashboard/_groups.html",
        {
            "request": request,
            "group_counts": group_counts
        }
    )


# -----------------------------
# PARTIAL: Printers summary
# -----------------------------
@router.get("/printers", response_class=HTMLResponse)
async def dash_printers(request: Request, db: Session = Depends(get_db), user=Depends(require_login)):
    count = db.query(Printer).count()
    return templates.TemplateResponse(
        "dashboard/_printers.html",
        {
            "request": request,
            "printer_count": count
        }
    )


# -----------------------------
# PARTIAL: Scanner summary (by host_type)
# -----------------------------
@router.get("/scanner", response_class=HTMLResponse)
async def dash_scanner(request: Request, db: Session = Depends(get_db), user=Depends(require_login)):
    hosts = db.query(ScannedHost).all()
    by_type = Counter([getattr(h, "host_type", "unknown") or "unknown" for h in hosts])
    monitored = sum(1 for h in hosts if getattr(h, "monitored", False))
    return templates.TemplateResponse(
        "dashboard/_scanner.html",
        {
            "request": request,
            "tot": len(hosts),
            "monitored": monitored,
            "by_type": dict(by_type)
        }
    )