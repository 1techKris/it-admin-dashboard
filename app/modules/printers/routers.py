from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime
import subprocess
import re

from app.core.security import require_login, get_role_for
from app.core.database import SessionLocal
from .models import Printer, PrinterSupplies

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------
# SNMP HELPERS
# ---------------------------------------------------------

def snmp_raw(ip: str, oid: str) -> str | None:
    """Return raw snmpget output or None."""
    try:
        out = subprocess.check_output(
            ["snmpget", "-v1", "-c", "public", ip, oid],
            stderr=subprocess.STDOUT,
            timeout=2
        ).decode()
        return out
    except Exception as e:
        print(f"[SNMP RAW ERROR] {ip} {oid}: {e}")
        return None


def snmp_int(ip: str, oid: str) -> int | None:
    """Extract integer after INTEGER:/Gauge32: only (prevents 'iso.3' -> 3 bug)."""
    out = snmp_raw(ip, oid)
    if not out:
        return None

    out = out.strip()

    if "INTEGER:" in out:
        try:
            return int(out.split("INTEGER:", 1)[1].strip())
        except:
            return None

    if "Gauge32:" in out:
        try:
            return int(out.split("Gauge32:", 1)[1].strip())
        except:
            return None

    return None


def decode_description(raw: str | None) -> str | None:
    """Decode SNMP STRING or Hex-STRING safely."""
    if not raw:
        return None

    s = raw.strip()

    # STRING: "..."
    if "STRING:" in s:
        return s.split("STRING:", 1)[1].strip().strip('"')

    # Hex-STRING: AA BB CC
    if "Hex-STRING" in s:
        bytestr = re.findall(r"([0-9A-Fa-f]{2})", s)
        try:
            b = bytes(int(x, 16) for x in bytestr)
            return b.decode("utf-8", errors="ignore").replace("\x00", "")
        except:
            return None

    return s


# ---------------------------------------------------------
# LIST PAGE (show only monitored printers)
# ---------------------------------------------------------

@router.get("/", response_class=HTMLResponse)
async def printer_list(request: Request, db: Session = Depends(get_db), user=Depends(require_login)):
    printers = (
        db.query(Printer)
        .filter(Printer.status == True)  # only monitored
        .order_by(Printer.name)
        .all()
    )
    return templates.TemplateResponse(
        "printers/index.html",
        {"request": request, "printers": printers, "user": user, "title": "Printers"}
    )


# ---------------------------------------------------------
# ADD PRINTER (modal + post)
# ---------------------------------------------------------

@router.get("/add-modal", response_class=HTMLResponse)
async def add_printer_modal(request: Request, user=Depends(require_login)):
    return templates.TemplateResponse("printers/_add_modal.html", {"request": request})


@router.post("/add")
async def add_printer(
    name: str = Form(...),
    ip_address: str = Form(...),
    model: str = Form("Unknown"),
    db: Session = Depends(get_db),
    user=Depends(require_login),
):
    existing = db.query(Printer).filter(Printer.ip_address == ip_address).first()
    if not existing:
        p = Printer(name=name, ip_address=ip_address, model=model, status=True)
        db.add(p)
        db.commit()
        db.refresh(p)

        # seed supplies row
        sup = PrinterSupplies(printer_id=p.id)
        db.add(sup)
        db.commit()

    resp = HTMLResponse("", status_code=204)
    resp.headers["HX-Refresh"] = "true"
    return resp


# ---------------------------------------------------------
# DETAIL MODAL
# ---------------------------------------------------------

@router.get("/{printer_id}/modal", response_class=HTMLResponse)
async def printer_modal(printer_id: int, request: Request,
                        db: Session = Depends(get_db),
                        user=Depends(require_login)):

    printer = db.query(Printer).filter(Printer.id == printer_id).first()
    if not printer:
        return HTMLResponse("Printer not found", status_code=404)

    if not printer.supplies:
        printer.supplies = PrinterSupplies(printer_id=printer.id)
        db.add(printer.supplies)
        db.commit()

    return templates.TemplateResponse(
        "printers/_detail_modal.html",
        {"request": request, "printer": printer}
    )


# ---------------------------------------------------------
# SUPPLIES PARTIAL (modal uses this on load)
# ---------------------------------------------------------

@router.get("/{printer_id}/supplies", response_class=HTMLResponse)
async def printer_supplies_partial(printer_id: int, request: Request,
                                   db: Session = Depends(get_db),
                                   user=Depends(require_login)):

    printer = db.query(Printer).filter(Printer.id == printer_id).first()
    if not printer:
        return HTMLResponse("Printer not found", status_code=404)

    return templates.TemplateResponse(
        "printers/_supplies.html",
        {"request": request, "printer": printer}
    )

# ---------------------------------------------------------
# DASHBOARD WIDGET: compact monitored printers list (partial)
# ---------------------------------------------------------
@router.get("/widget", response_class=HTMLResponse)
async def printers_widget(request: Request,
                          db: Session = Depends(get_db),
                          user=Depends(require_login)):
    """
    Returns a compact table of monitored printers for the dashboard panel.
    """
    printers = (
        db.query(Printer)
        .filter(Printer.status == True)  # monitored only
        .order_by(Printer.name)
        .all()
    )
    return templates.TemplateResponse(
        "printers/_dash_list.html",
        {"request": request, "printers": printers}
    )

# ---------------------------------------------------------
# REFRESH SUPPLIES (FULL CMYK + KYOCERA SUPPORT)
# ---------------------------------------------------------

@router.post("/{printer_id}/supplies/refresh", response_class=HTMLResponse)
async def printer_supplies_refresh(printer_id: int,
                                   request: Request,
                                   db: Session = Depends(get_db),
                                   user=Depends(require_login)):

    printer = db.query(Printer).filter(Printer.id == printer_id).first()
    if not printer:
        return HTMLResponse("Printer not found", status_code=404)

    # Ensure supplies row exists
    if not printer.supplies:
        printer.supplies = PrinterSupplies(printer_id=printer.id)
        db.add(printer.supplies)
        db.commit()

    # Reset CMYK
    printer.supplies.bk = None
    printer.supplies.c = None
    printer.supplies.m = None
    printer.supplies.y = None

    # Vendors typically occupy 1–6
    indices = ["1", "2", "3", "4", "5", "6"]

    for idx in indices:
        # Description
        desc_raw = snmp_raw(printer.ip_address,
                            f"1.3.6.1.2.1.43.11.1.1.6.1.{idx}")
        desc = decode_description(desc_raw)
        if not desc:
            continue

        desc_l = desc.lower()

        # Ignore non-toner
        if "waste" in desc_l:
            continue

        # Determine colour (strict)
        colour = None

        # Standard vendor text
        if "cyan" in desc_l:
            colour = "c"
        elif "magenta" in desc_l:
            colour = "m"
        elif "yellow" in desc_l:
            colour = "y"
        elif "black" in desc_l:
            colour = "bk"

        # Kyocera kit suffix: "... C/M/Y/K" (must match final char)
        elif desc_l.endswith(" c"):
            colour = "c"
        elif desc_l.endswith(" m"):
            colour = "m"
        elif desc_l.endswith(" y"):
            colour = "y"
        elif desc_l.endswith(" k"):
            colour = "bk"

        if not colour:
            continue

        # Levels & max capacity
        level = snmp_int(printer.ip_address,
                         f"1.3.6.1.2.1.43.11.1.1.9.1.{idx}")
        maxcap = snmp_int(printer.ip_address,
                          f"1.3.6.1.2.1.43.11.1.1.8.1.{idx}")

        pct = None

        # Raw level/maxcap -> percent (Kyocera etc.)
        if level is not None and maxcap is not None and maxcap > 0 and level <= maxcap:
            pct = round((level / maxcap) * 100)
            pct = max(0, min(100, pct))
        # Already percent (HP/Brother etc.)
        elif level is not None and 0 <= level <= 100:
            pct = level

        if pct is not None:
            setattr(printer.supplies, colour, pct)

    # Mono fallback if nothing set
    if (
        printer.supplies.bk is None and
        printer.supplies.c is None and
        printer.supplies.m is None and
        printer.supplies.y is None
    ):
        lvl = snmp_int(printer.ip_address,
                       "1.3.6.1.2.1.43.11.1.1.9.1.1")
        if lvl is not None and 0 <= lvl <= 100:
            printer.supplies.bk = lvl

    printer.supplies.updated_at = datetime.utcnow()
    db.commit()

    # IMPORTANT:
    # - Modal refresh targets #modal-supplies-{{ id }} via _detail_modal.html
    # - Card refresh targets #card-supplies-{{ id }} via index.html
    # Both use the same template; either target will accept this fragment.
    # For card refresh, the wrapper id in _supplies.html should be card-supplies-{{ id }}.
    # For modal refresh, wrapper should be modal-supplies-{{ id }}.
    # If you prefer a single template, you can parameterize the id via querystring and pass target_id.

    return templates.TemplateResponse(
        "printers/_supplies.html",
        {"request": request, "printer": printer}
    )


# ---------------------------------------------------------
# REMOVE (UNMONITOR) & RE-MONITOR PRINTER
# ---------------------------------------------------------

@router.post("/{printer_id}/unmonitor", response_class=HTMLResponse)
async def unmonitor_printer(printer_id: int,
                            request: Request,
                            db: Session = Depends(get_db),
                            user=Depends(require_login)):
    """
    Soft-remove a printer from the dashboard (status=False).
    UI card is removed via HTMX outerHTML swap.
    """
    printer = db.query(Printer).filter(Printer.id == printer_id).first()
    if not printer:
        return HTMLResponse("Printer not found", status_code=404)

    printer.status = False
    db.commit()

    # Returning empty body -> removes card on front-end
    return HTMLResponse("", status_code=200)


@router.post("/{printer_id}/remonitor", response_class=HTMLResponse)
async def remonitor_printer(printer_id: int,
                            request: Request,
                            db: Session = Depends(get_db),
                            user=Depends(require_login)):
    """
    Bring a previously-unmonitored printer back.
    """
    printer = db.query(Printer).filter(Printer.id == printer_id).first()
    if not printer:
        return HTMLResponse("Printer not found", status_code=404)

    printer.status = True
    db.commit()

    return HTMLResponse("OK", status_code=200)