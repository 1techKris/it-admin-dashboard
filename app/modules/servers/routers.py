from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional, List

from app.core.security import require_login, get_role_for
from app.core.database import SessionLocal

from .models import (
    Server,
    ServerStatusHistory,
    ServerMetrics,
    ServerCredentials,
    ServerGroup,
    ServerGroupMember,
    ServerTag,
    GlobalSettings,
    get_setting,
    set_setting,
)

from .wmi import fetch_wmi
from .scanner import ping_ip_ms

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


# ==========================================================
# DB DEPENDENCY
# ==========================================================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ==========================================================
# STATIC ROUTES (MUST COME FIRST)
# ==========================================================

@router.get("/add-modal", response_class=HTMLResponse)
async def add_server_modal(request: Request, user=Depends(require_login)):
    return templates.TemplateResponse(
        "servers/_add_modal.html",
        {"request": request}
    )


@router.post("/add")
async def add_server(
    hostname: str = Form(None),
    ip_address: str = Form(...),
    db: Session = Depends(get_db),
    user=Depends(require_login),
):
    # Dedup on IP
    existing = db.query(Server).filter(Server.ip_address == ip_address).first()

    if not existing:
        online, ping_ms = ping_ip_ms(ip_address)

        server = Server(
            hostname=hostname or ip_address,
            ip_address=ip_address,
            online=online,
            last_seen=datetime.utcnow() if online else None,
        )
        db.add(server)
        db.commit()

        db.add(ServerStatusHistory(
            server_id=server.id,
            online=online,
            ping_ms=ping_ms
        ))
        db.commit()

    resp = HTMLResponse("", status_code=204)
    resp.headers["HX-Refresh"] = "true"
    return resp


# ==========================================================
# SERVER LIST
# ==========================================================
@router.get("/", response_class=HTMLResponse)
async def server_list(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_login),
):
    role = get_role_for(user)
    servers = db.query(Server).order_by(Server.hostname).all()

    return templates.TemplateResponse(
        "servers/index.html",
        {
            "request": request,
            "servers": servers,
            "user": user,
            "role": role,
            "active": "servers",
            "title": "Servers",
        }
    )

from fastapi.responses import RedirectResponse

@router.get("/admin/settings", response_class=HTMLResponse)
async def admin_settings_redirect():
    # Permanent redirect to centralized settings
    return RedirectResponse(url="/settings/", status_code=307)
# ==========================================================
# ADMIN SETTINGS PAGE (WMI + AD)
# ==========================================================
@router.get("/admin/settings", response_class=HTMLResponse)
async def admin_settings_page(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_login),
):
    role = get_role_for(user)
    if role != "admin":
        return HTMLResponse("<div class='p-4 text-red-400'>Access denied</div>", 403)

    # --- WMI settings ---
    wmi_username = get_setting(db, "wmi_username")
    wmi_password = get_setting(db, "wmi_password")

    # --- AD settings ---
    ad_domain = get_setting(db, "ad_domain")
    ad_dc_host = get_setting(db, "ad_dc_host")
    ad_dc_ip = get_setting(db, "ad_dc_ip")
    ad_base_dn = get_setting(db, "ad_base_dn")
    ad_default_user_ou = get_setting(db, "ad_default_user_ou")
    ad_username = get_setting(db, "ad_username")
    ad_password = get_setting(db, "ad_password")

    return templates.TemplateResponse(
        "admin/settings.html",
        {
            "request": request,
            "title": "Settings",

            # WMI
            "wmi_username": wmi_username,
            "wmi_password": wmi_password,

            # AD
            "ad_domain": ad_domain,
            "ad_dc_host": ad_dc_host,
            "ad_dc_ip": ad_dc_ip,
            "ad_base_dn": ad_base_dn,
            "ad_default_user_ou": ad_default_user_ou,
            "ad_username": ad_username,
            "ad_password": ad_password,
        }
    )


# ==========================================================
# SAVE WMI SETTINGS
# ==========================================================
@router.post("/admin/settings/wmi", response_class=HTMLResponse)
async def save_global_wmi(
    username: str = Form(""),
    password: str = Form(""),
    db: Session = Depends(get_db),
    user=Depends(require_login),
):
    role = get_role_for(user)
    if role != "admin":
        return HTMLResponse("<div class='text-red-400'>Access denied</div>", 403)

    set_setting(db, "wmi_username", username)
    set_setting(db, "wmi_password", password)

    return HTMLResponse("<div class='text-green-400'>Saved.</div>")


# ==========================================================
# SAVE ACTIVE DIRECTORY SETTINGS
# ==========================================================
@router.post("/admin/settings/ad", response_class=HTMLResponse)
async def save_ad_settings(
    ad_domain: str = Form(...),
    ad_dc_host: str = Form(...),
    ad_dc_ip: str = Form(""),
    ad_base_dn: str = Form(...),
    ad_default_user_ou: str = Form(...),
    ad_username: str = Form(...),
    ad_password: str = Form(...),
    db: Session = Depends(get_db),
    user=Depends(require_login),
):
    role = get_role_for(user)
    if role != "admin":
        return HTMLResponse("<div class='text-red-400'>Access denied</div>", 403)

    set_setting(db, "ad_domain", ad_domain)
    set_setting(db, "ad_dc_host", ad_dc_host)
    set_setting(db, "ad_dc_ip", ad_dc_ip)
    set_setting(db, "ad_base_dn", ad_base_dn)
    set_setting(db, "ad_default_user_ou", ad_default_user_ou)
    set_setting(db, "ad_username", ad_username)
    set_setting(db, "ad_password", ad_password)

    return HTMLResponse("<div class='text-green-400'>AD settings saved.</div>")


# ==========================================================
# TEST ACTIVE DIRECTORY CONNECTION
# ==========================================================
@router.post("/admin/settings/ad/test", response_class=JSONResponse)
async def test_ad_settings(
    db: Session = Depends(get_db),
    user=Depends(require_login),
):
    role = get_role_for(user)
    if role != "admin":
        return JSONResponse({"error": "Access denied"}, status_code=403)

    try:
        from app.modules.active_directory.ad_client import ADClient
        ad = ADClient()
        ad.connect()
        return JSONResponse({"ok": True, "message": "AD connection successful!"})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
# ==========================================================
# SERVER DETAIL MODAL
# ==========================================================
@router.get("/{server_id}/modal", response_class=HTMLResponse)
async def server_detail_modal(
    server_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_login),
):
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        return HTMLResponse("<div class='text-red-400 p-4'>Not found</div>", 404)

    return templates.TemplateResponse(
        "servers/_detail_modal.html",
        {"request": request, "server": server}
    )


# ==========================================================
# DETAIL CARDS (AUTO-REFRESH)
# ==========================================================
@router.get("/{server_id}/cards", response_class=HTMLResponse)
async def server_detail_cards(
    server_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_login),
):
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        return HTMLResponse("<div class='text-red-400 p-4'>Not found</div>", 404)

    history = (
        db.query(ServerStatusHistory)
        .filter(ServerStatusHistory.server_id == server_id)
        .order_by(ServerStatusHistory.ts.desc())
        .limit(20)
        .all()
    )

    lookback = datetime.utcnow() - timedelta(hours=1)
    recent = (
        db.query(ServerStatusHistory)
        .filter(
            ServerStatusHistory.server_id == server_id,
            ServerStatusHistory.ts >= lookback,
        )
        .all()
    )
    uptime_pct = (
        round(100 * sum(1 for r in recent if r.online) / len(recent), 1)
        if recent
        else None
    )

    latest_ping = history[0].ping_ms if history else None

    return templates.TemplateResponse(
        "servers/_cards.html",
        {
            "request": request,
            "server": server,
            "history": list(reversed(history)),
            "uptime_pct": uptime_pct,
            "latest_ping": latest_ping,
        }
    )


# ==========================================================
# WMI SUMMARY (PARTIAL)
# ==========================================================
import json

@router.get("/{server_id}/wmi/summary", response_class=HTMLResponse)
async def wmi_summary(
    server_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_login),
):
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        return HTMLResponse("<div class='text-red-400'>Server not found</div>", 404)

    parsed = None
    if server.wmi_json:
        try:
            parsed = json.loads(server.wmi_json)
        except:
            parsed = None

    return templates.TemplateResponse(
        "servers/_wmi_summary.html",
        {"request": request, "server": server, "wmi": parsed}
    )


# ==========================================================
# WMI REFRESH (SAFE + OS AUTODETECT + FRIENDLY ERRORS)
# ==========================================================
import json

@router.post("/{server_id}/wmi/refresh", response_class=HTMLResponse)
async def wmi_refresh(
    server_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_login),
):
    from .wmi_utils import is_windows_host
    from .wmi import fetch_wmi

    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        return HTMLResponse("<div class='text-red-400'>Server not found</div>", 404)

    if not is_windows_host(server.ip_address):
        return HTMLResponse(
            "<div class='text-gray-500 text-xs p-2'>WMI skipped — WinRM not detected.</div>",
            200
        )

    # Resolve credentials
    creds = db.query(ServerCredentials).filter(ServerCredentials.server_id == server_id).first()
    username = creds.username if creds else get_setting(db, "wmi_username")
    password = creds.password if creds else get_setting(db, "wmi_password")

    if not username or not password:
        return HTMLResponse(
            "<div class='text-yellow-400 text-xs p-2'>No WMI credentials configured.</div>",
            200
        )

    # Fetch RAW JSON WMI
    try:
        result = fetch_wmi(server.ip_address, username, password)
    except Exception as e:
        return HTMLResponse(
            f"<div class='text-red-400 text-xs p-2'>WMI error: {e}</div>",
            200
        )

    # Store as RAW JSON
    server.wmi_json = json.dumps(result, indent=2)
    server.last_wmi_at = datetime.utcnow()
    db.commit()

    return templates.TemplateResponse(
        "servers/_wmi_summary.html",
        {"request": request, "server": server}
    )


# ==========================================================
# DELETE SERVER
# ==========================================================
@router.delete("/{server_id}/delete")
async def delete_server(
    server_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_login),
):
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        return HTMLResponse("<div>Not found</div>", 404)

    db.query(ServerStatusHistory).filter(ServerStatusHistory.server_id == server_id).delete()
    db.delete(server)
    db.commit()

    resp = HTMLResponse("", 204)
    resp.headers["HX-Refresh"] = "true"
    return resp


# ==========================================================
# EDIT SERVER MODAL
# ==========================================================
@router.get("/{server_id}/edit-modal", response_class=HTMLResponse)
async def edit_server_modal(
    server_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_login),
):
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        return HTMLResponse("<div>Not found</div>", 404)

    creds = db.query(ServerCredentials).filter(ServerCredentials.server_id == server_id).first()
    groups = db.query(ServerGroup).order_by(ServerGroup.name).all()
    member_ids = {
        m.group_id
        for m in db.query(ServerGroupMember).filter(ServerGroupMember.server_id == server_id).all()
    }
    tags = [t.tag for t in db.query(ServerTag).filter(ServerTag.server_id == server_id).all()]

    return templates.TemplateResponse(
        "servers/_edit_modal.html",
        {
            "request": request,
            "server": server,
            "creds": creds,
            "groups": groups,
            "member_ids": member_ids,
            "tags_csv": ", ".join(tags),
        }
    )


# ==========================================================
# SAVE EDITED SERVER
# ==========================================================
@router.post("/{server_id}/edit")
async def edit_server(
    server_id: int,
    hostname: Optional[str] = Form(None),
    ip_address: Optional[str] = Form(None),
    os_type: Optional[str] = Form(None),
    username: Optional[str] = Form(None),
    password: Optional[str] = Form(None),
    port: Optional[int] = Form(None),
    groups: Optional[List[int]] = Form(None),
    tags_csv: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    user=Depends(require_login),
):
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        return HTMLResponse("Not found", 404)

    if hostname:
        server.hostname = hostname.strip()
    if ip_address:
        server.ip_address = ip_address.strip()
    db.commit()

    # Credentials
    if any([os_type, username, password, port]):
        creds = db.query(ServerCredentials).filter(ServerCredentials.server_id == server_id).first()
        if not creds:
            creds = ServerCredentials(server_id=server_id)
            db.add(creds)

        if os_type:
            creds.os_type = os_type
        if username is not None:
            creds.username = username
        if password is not None:
            creds.password = password
        if port:
            creds.port = port

        db.commit()

    # Groups
    if groups is not None:
        db.query(ServerGroupMember).filter(ServerGroupMember.server_id == server_id).delete()
        for gid in groups:
            if gid:
                db.add(ServerGroupMember(server_id=server_id, group_id=int(gid)))
        db.commit()

    # Tags
    if tags_csv is not None:
        db.query(ServerTag).filter(ServerTag.server_id == server_id).delete()
        tags = [t.strip() for t in tags_csv.split(",") if t.strip()]
        for t in tags:
            db.add(ServerTag(server_id=server_id, tag=t))
        db.commit()

    resp = HTMLResponse("", 204)
    resp.headers["HX-Refresh"] = "true"
    return resp


# ==========================================================
# METRICS JSON FOR CHARTS
# ==========================================================
@router.get("/{server_id}/metrics.json")
async def metrics_json(
    server_id: int,
    limit: int = 50,
    db: Session = Depends(get_db),
    user=Depends(require_login),
):
    ms = (
        db.query(ServerMetrics)
        .filter(ServerMetrics.server_id == server_id)
        .order_by(ServerMetrics.ts.desc())
        .limit(limit)
        .all()
    )
    ms = list(reversed(ms))

    return {
        "ts": [m.ts.isoformat() for m in ms],
        "cpu": [m.cpu_percent for m in ms],
        "ram": [m.ram_percent for m in ms],
        "disk": [m.disk_percent for m in ms],

    }
