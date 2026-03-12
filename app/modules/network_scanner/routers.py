from fastapi import APIRouter, Request, Depends, Query, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
import ipaddress

from app.core.security import require_login, get_role_for, require_role
from app.core.database import SessionLocal
from app.modules.network_scanner.scanner import scan_subnet, detect_local_cidr
from app.modules.network_scanner.models import ScannedHost, SubnetProfile

# IMPORTANT: these must match your actual model class names
from app.modules.servers.models import Server
from app.modules.printers.models import Printer

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


# -----------------------------
# DB session dependency
# -----------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# -----------------------------
# MAIN SCANNER PAGE (UI)
# -----------------------------
@router.get("/scan", response_class=HTMLResponse)
async def scan_page(request: Request, db: Session = Depends(get_db), user=Depends(require_login)):
    role = get_role_for(user)
    profiles = db.query(SubnetProfile).order_by(SubnetProfile.name).all()
    suggested = detect_local_cidr()

    return templates.TemplateResponse(
        "network/scan.html",
        {
            "request": request,
            "user": user,
            "role": role,
            "active": "network",
            "title": "Network Scanner",
            "profiles": profiles,
            "suggested": suggested
        }
    )


# -----------------------------
# RUN SCAN (HTMX partial)
# -----------------------------
@router.get("/scan/run", response_class=HTMLResponse)
async def run_scan(
    request: Request,
    range: Optional[str] = Query(None),
    profile_id: Optional[str] = Query(None),  # may be ""
    community: str = Query("public"),
    db: Session = Depends(get_db),
    user=Depends(require_login)
):
    # Determine CIDR: profile -> range -> auto-detect
    cidr = None

    if profile_id and profile_id.isdigit():
        prof = db.query(SubnetProfile).filter(SubnetProfile.id == int(profile_id)).first()
        if prof:
            cidr = prof.cidr
            prof.last_used = datetime.utcnow()
            db.commit()

    if not cidr and range:
        cidr = range.strip()

    if not cidr:
        cidr = detect_local_cidr()

    # Validate CIDR
    try:
        network = ipaddress.ip_network(cidr, strict=False)
    except Exception:
        return HTMLResponse(
            "<div class='text-red-400 p-4 bg-red-900/20 rounded'>Invalid subnet. Example: 192.168.125.0/24</div>"
        )

    subnet_ips = [str(ip) for ip in network.hosts()]

    # Run scan (from scanner.py; may include SNMP/vendor/OS guess)
    results = scan_subnet(subnet_ips, snmp_community=community)

    # Persist results
    for r in results:
        host = db.query(ScannedHost).filter(ScannedHost.ip == r["ip"]).first()
        if not host:
            host = ScannedHost(ip=r["ip"])
            db.add(host)

        host.hostname = r["hostname"]
        host.open_ports = ",".join(map(str, r["ports"]))
        host.vendor = r.get("vendor")
        host.os_guess = r.get("os_guess")
        host.host_type = r.get("host_type") or "unknown"
        host.last_seen = datetime.utcnow()
        db.commit()

    hosts = (
        db.query(ScannedHost)
        .filter(ScannedHost.ip.in_(subnet_ips))
        .order_by(ScannedHost.ip)
        .all()
    )

    return templates.TemplateResponse(
        "network/_host_cards.html",
        {"request": request, "hosts": hosts}
    )


# -----------------------------
# SAVE PROFILE (Admin only)
# -----------------------------
@router.post("/scan/profile/save")
async def save_profile(
    name: str = Form(...),
    cidr: str = Form(...),
    notes: str = Form(None),
    db: Session = Depends(get_db),
    user=Depends(require_role("admin"))
):
    try:
        ipaddress.ip_network(cidr, strict=False)
    except Exception:
        return JSONResponse({"ok": False, "error": "Invalid CIDR"}, status_code=400)

    existing = db.query(SubnetProfile).filter(SubnetProfile.name == name).first()
    if existing:
        existing.cidr = cidr
        existing.notes = notes
        existing.last_used = datetime.utcnow()
    else:
        db.add(SubnetProfile(name=name, cidr=cidr, notes=notes, last_used=datetime.utcnow()))
    db.commit()
    return {"ok": True}


# -----------------------------
# OPTIONAL: ADD MODAL (choose type & name)
# -----------------------------
@router.get("/scan/add-modal", response_class=HTMLResponse)
async def add_modal(request: Request, ip: str, db: Session = Depends(get_db), user=Depends(require_login)):
    host = db.query(ScannedHost).filter(ScannedHost.ip == ip).first()
    return templates.TemplateResponse(
        "network/_add_modal.html",
        {"request": request, "host": host}
    )


# -----------------------------
# ADD HOST TO MONITORING
# Accepts Form OR JSON (works with hx-vals)
# Returns small HTML snippet so HTMX can swap button -> "Monitoring Enabled"
# -----------------------------
@router.post("/scan/add")
async def add_host(
    request: Request,
    ip: Optional[str] = Form(None),
    host_type: Optional[str] = Form(None),   # server | printer | unknown
    hostname: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    user=Depends(require_login)
):
    # If not provided as Form, try JSON body (hx-vals often sends JSON)
    if not ip or not host_type:
        try:
            data = await request.json()
            ip = ip or data.get("ip")
            host_type = host_type or data.get("host_type")
            hostname = hostname or data.get("hostname")
        except Exception:
            pass

    if not ip or not host_type:
        return HTMLResponse(
            "<span class='text-red-400 text-sm'>Missing ip/host_type</span>", status_code=422
        )

    # Ensure scanned host exists and set monitored=1
    host = db.query(ScannedHost).filter(ScannedHost.ip == ip).first()
    if not host:
        host = ScannedHost(ip=ip)
        db.add(host)
        db.commit()
        db.refresh(host)

    host.monitored = True
    host.host_type = host_type
    if hostname:
        host.hostname = hostname
    db.commit()

    # Insert into Servers/Printers tables
    if host_type == "server":
        exists = db.query(Server).filter(Server.ip_address == ip).first()
        if not exists:
            db.add(Server(
                hostname=hostname or host.hostname or ip,
                ip_address=ip,
                online=True,
                last_seen=datetime.utcnow()
            ))
            db.commit()

    elif host_type == "printer":
        exists = db.query(Printer).filter(Printer.ip_address == ip).first()
        if not exists:
            db.add(Printer(
                name=hostname or host.hostname or ip,
                ip_address=ip,
                model="Unknown",
                status=True
            ))
            db.commit()

    # Return a small HTML snippet to swap the button
    return HTMLResponse("<span class='text-green-400 text-sm'>Monitoring Enabled</span>")