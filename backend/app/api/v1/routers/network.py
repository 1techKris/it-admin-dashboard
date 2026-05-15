import asyncio
from fastapi import (
    APIRouter,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
    Depends,
)
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

from app.services.scanner_service import (
    start_scan,
    get_scan,
    cancel_scan,
)
from app.services.service_labels import label_for_port

from app.models.printer import Printer
from app.models.device import Device
from app.core.config import settings

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_session


router = APIRouter(prefix="/network", tags=["network"])

DEFAULT_PORTS = [22, 80, 443, 3389, 445, 9100]

# ----------------------------------------------------------------------
# Request / Response Models
# ----------------------------------------------------------------------

class ScanRequest(BaseModel):
    cidr: str = Field(..., examples=["192.168.125.0/24"])
    ports: Optional[List[int]] = None
    concurrency: Optional[int] = None
    host_delay: Optional[float] = None
    timeouts: Optional[Dict[str, float]] = None  # NEW


class ScanResponse(BaseModel):
    id: str
    status: str
    total: int
    completed: int


# ----------------------------------------------------------------------
# Start scan
# ----------------------------------------------------------------------

@router.post("/scan", response_model=ScanResponse)
async def create_scan(req: ScanRequest):
    ports = req.ports or DEFAULT_PORTS

    state = await start_scan(
        cidr=req.cidr,
        ports=ports,
        concurrency=req.concurrency or 16,
        host_delay=req.host_delay or 0.05,
        timeouts=req.timeouts,
    )

    return ScanResponse(
        id=state.id,
        status=state.status,
        total=state.total,
        completed=state.completed,
    )


# ----------------------------------------------------------------------
# Stop scan
# ----------------------------------------------------------------------

@router.post("/scan/{scan_id}/stop")
async def stop_scan(scan_id: str):
    ok = cancel_scan(scan_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Scan not found")
    return {"status": "cancelling", "scan_id": scan_id}


# ----------------------------------------------------------------------
# Get scan status
# ----------------------------------------------------------------------

@router.get("/scan/{scan_id}")
async def get_scan_status(scan_id: str) -> Dict[str, Any]:
    state = get_scan(scan_id)
    if not state:
        raise HTTPException(status_code=404, detail="Scan not found")

    return {
        "id": state.id,
        "cidr": state.cidr,
        "status": state.status,
        "total": state.total,
        "completed": state.completed,
        "error": state.error,
        "results": [
            {
                "ip": r.ip,
                "alive": r.alive,
                "hostname": r.hostname,
                "open_ports": r.open_ports,
                "banners": r.banners,
                "os": r.os,
                "device_class": r.device_class,   # NEW
                "vendor": r.vendor,               # NEW
                "model": r.model,                 # NEW
                "labels": [label_for_port(p) for p in r.open_ports],
                "updated_at": r.updated_at,
            }
            for r in state.results.values()
        ],
    }


# ----------------------------------------------------------------------
# WebSocket – live scan updates
# ----------------------------------------------------------------------

@router.websocket("/ws/scan/{scan_id}")
async def ws_scan(websocket: WebSocket, scan_id: str):
    await websocket.accept()

    try:
        while True:
            state = get_scan(scan_id)

            if not state:
                await websocket.send_json({"error": "Scan not found"})
                await websocket.close()
                return

            payload = {
                "id": state.id,
                "cidr": state.cidr,
                "status": state.status,
                "total": state.total,
                "completed": state.completed,
                "error": state.error,
                "results": [
                    {
                        "ip": r.ip,
                        "alive": r.alive,
                        "hostname": r.hostname,
                        "open_ports": r.open_ports,
                        "banners": r.banners,
                        "os": r.os,
                        "device_class": r.device_class,  # NEW
                        "vendor": r.vendor,              # NEW
                        "model": r.model,                # NEW
                        "labels": [label_for_port(p) for p in r.open_ports],
                        "updated_at": r.updated_at,
                    }
                    for r in state.results.values()
                ],
            }

            await websocket.send_json(payload)

            if state.status in ("finished", "cancelled", "error"):
                await websocket.close()
                return

            await asyncio.sleep(1.0)

    except WebSocketDisconnect:
        return


# ----------------------------------------------------------------------
# Import scan results into database
# (unchanged except new fields available)
# ----------------------------------------------------------------------

class ImportRequest(BaseModel):
    ips: Optional[List[str]] = None


class ImportResult(BaseModel):
    created: int
    skipped: int
    details: List[Dict[str, Any]]


@router.post("/scan/{scan_id}/import", response_model=ImportResult)
async def import_scan_results(
    scan_id: str,
    req: ImportRequest,
    db: AsyncSession = Depends(get_session),
):
    state = get_scan(scan_id)
    if not state:
        raise HTTPException(status_code=404, detail="Scan not found")

    if req.ips:
        targets = [state.results[ip] for ip in req.ips if ip in state.results]
    else:
        targets = [r for r in state.results.values() if r.alive]

    created = 0
    skipped = 0
    details: List[Dict[str, Any]] = []

    # EVERYTHING BELOW IS IDENTICAL TO YOUR EXISTING IMPORT LOGIC
    # (unchanged intentionally)
    for r in targets:

        is_printer = (
            9100 in r.open_ports
            or (r.os and r.os.lower() == "printer")
            or (r.hostname and "PRINTER" in r.hostname.upper())
        )

        if is_printer:
            display_name = (r.hostname or r.ip).upper()

            existing = (
                await db.execute(select(Printer).where(Printer.ip == r.ip))
            ).scalars().first()

            if existing:
                skipped += 1
                details.append({
                    "ip": r.ip,
                    "name": existing.name,
                    "type": "Printer",
                    "action": "skipped",
                })
                continue

            new_pr = Printer(
                name=display_name,
                ip=r.ip,
                status="Unknown",
                vendor=None,
                model=None,
                serial=None,
                supplies_json=None,
                archived=False,
            )

            db.add(new_pr)
            await db.flush()

            created += 1
            details.append({
                "ip": r.ip,
                "name": display_name,
                "type": "Printer",
                "action": "created",
            })

            continue

        # Servers / Unknown
        if r.os == "Windows":
            dtype = "Server"
        elif r.os == "Linux":
            dtype = "Server"
        else:
            dtype = "Unknown"

        device_id = (r.hostname or r.ip).upper()

        existing = (
            await db.execute(
                select(Device).where(
                    (Device.ip == r.ip) | (Device.device_id == device_id)
                )
            )
        ).scalars().first()

        if existing:
            skipped += 1
            details.append({
                "ip": r.ip,
                "device_id": existing.device_id,
                "type": dtype,
                "action": "skipped",
            })
            continue

        new_dev = Device(
            device_id=device_id,
            type=dtype,
            os=r.os or "Unknown",
            ip=r.ip,
            cpu=0,
            mem=0,
            status="Discovered",
            custom_name=None,
        )

        db.add(new_dev)
        await db.flush()

        created += 1
        details.append({
            "ip": r.ip,
            "device_id": device_id,
            "type": dtype,
            "action": "created",
        })

    await db.commit()
    return ImportResult(created=created, skipped=skipped, details=details)