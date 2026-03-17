from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

from app.services.scanner_service import start_scan, get_scan
from app.services.service_labels import label_for_port
from app.models.printer import Printer
from app.core.config import settings

router = APIRouter(prefix="/network", tags=["network"])

# Default ports used if none are sent
DEFAULT_PORTS = [22, 80, 443, 3389, 445, 9100]


#
# Request/response models
#

class ScanRequest(BaseModel):
    cidr: str = Field(..., examples=["192.168.125.0/24"])
    ports: Optional[List[int]] = Field(default=None)


class ScanResponse(BaseModel):
    id: str
    status: str
    total: int
    completed: int


#
# Start a new scan
#

@router.post("/scan", response_model=ScanResponse)
async def create_scan(req: ScanRequest):
    ports = req.ports or DEFAULT_PORTS
    state = await start_scan(req.cidr, ports)

    return ScanResponse(
        id=state.id,
        status=state.status,
        total=state.total,
        completed=state.completed,
    )


#
# Get current scan status
#

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
                "labels": [label_for_port(p) for p in r.open_ports],
            }
            for r in state.results.values()
        ],
    }


#
# WebSocket: live scan feed
#

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
                        "labels": [label_for_port(p) for p in r.open_ports],
                    }
                    for r in state.results.values()
                ],
            }

            await websocket.send_json(payload)

            if state.status == "finished":
                await websocket.close()
                return

            if state.status == "error":
                await websocket.send_json({"error": state.error})
                await websocket.close()
                return

            # Yield update every second
            import asyncio
            await asyncio.sleep(1.0)

    except WebSocketDisconnect:
        return


#
# Import scan results → Devices DB
#

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import Depends

from app.db.session import get_session
from app.models.device import Device


class ImportRequest(BaseModel):
    ips: Optional[List[str]] = None  # import specific IPs; None = import all alive hosts


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

    # Choose results to import
    if req.ips:
        targets = [state.results[ip] for ip in req.ips if ip in state.results]
    else:
        targets = [r for r in state.results.values() if r.alive]

    created = 0
    skipped = 0
    details: List[Dict[str, Any]] = []

    for r in targets:
        # ---------------------------
        # Classify printer vs non-printer
        # ---------------------------
        is_printer = (
            9100 in r.open_ports
            or (r.os and r.os.lower() == "printer")
            or (r.hostname and "PRINTER" in r.hostname.upper())
        )

        if is_printer:
            # ---------------------------
            # PRINTERS → printers table
            # ---------------------------
            display_name = (r.hostname or r.ip).upper()

            # already in printers?
            pr_exists = (
                await db.execute(select(Printer).where(Printer.ip == r.ip))
            ).scalars().first()

            if pr_exists:
                skipped += 1
                details.append({"ip": r.ip, "name": pr_exists.name, "type": "Printer", "action": "skipped"})
                continue

            # create new Printer row (minimal; SNMP will enrich later)
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
            details.append({"ip": r.ip, "name": display_name, "type": "Printer", "action": "created"})

            # OPTIONAL: trigger an immediate SNMP refresh here (synchronous).
            # If you want that, import fetch_printer_snapshot and uncomment below.
            # from app.services.printer_snmp import fetch_printer_snapshot
            # snap = fetch_printer_snapshot(
            #     ip=r.ip,
            #     community=settings.PRINTER_SNMP_COMMUNITY,
            #     timeout=settings.PRINTER_SNMP_TIMEOUT,
            #     retries=settings.PRINTER_SNMP_RETRIES,
            # )
            # new_pr.vendor = snap.get("vendor")
            # new_pr.model  = snap.get("model")
            # new_pr.serial = snap.get("serial")
            # new_pr.supplies_json = json.dumps(snap)
            # new_pr.status = "Healthy"
            # await db.flush()

            continue

        # ---------------------------
        # NON-PRINTERS → devices table
        # ---------------------------
        if r.os == "Windows":
            dtype = "Server"
        elif r.os == "Linux":
            dtype = "Server"
        else:
            dtype = "Unknown"

        device_id = (r.hostname or r.ip).upper()

        dev_exists = (
            await db.execute(
                select(Device).where(
                    (Device.ip == r.ip) | (Device.device_id == device_id)
                )
            )
        ).scalars().first()

        if dev_exists:
            skipped += 1
            details.append({"ip": r.ip, "device_id": dev_exists.device_id, "type": dtype, "action": "skipped"})
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
        details.append({"ip": r.ip, "device_id": device_id, "type": dtype, "action": "created"})

    await db.commit()
    return ImportResult(created=created, skipped=skipped, details=details)