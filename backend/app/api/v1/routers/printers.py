# backend/app/api/v1/routers/printers.py

import asyncio
import json
from datetime import datetime, timezone
from typing import List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_session
from app.models.printer import Printer
from app.services.printer_snmp import fetch_printer_snapshot
from app.core.config import settings

router = APIRouter(prefix="/printers", tags=["printers"])

# ---------------------------
# Pydantic Schemas
# ---------------------------

from pydantic import BaseModel

class PrinterCreate(BaseModel):
    ip: str
    name: str | None = None

class PrinterOut(BaseModel):
    id: int
    name: str
    ip: str
    status: str
    vendor: str | None = None
    model: str | None = None
    last_seen: datetime | None = None
    archived: bool = False

    class Config:
        from_attributes = True

class PrinterDetail(BaseModel):
    id: int
    name: str
    ip: str
    status: str
    vendor: str | None
    model: str | None
    serial: str | None
    last_seen: datetime | None
    supplies: List[Dict[str, Any]]

# ---------------------------
# REST Endpoints
# ---------------------------

@router.get("", response_model=List[PrinterOut])
async def list_printers(include_archived: bool = False, db: AsyncSession = Depends(get_session)):
    stmt = select(Printer)
    if not include_archived:
        stmt = stmt.where(Printer.archived == False)
    rows = (await db.execute(stmt)).scalars().all()
    return rows

@router.post("", response_model=PrinterOut)
async def add_printer(req: PrinterCreate, db: AsyncSession = Depends(get_session)):
    exists = (await db.execute(select(Printer).where(Printer.ip == req.ip))).scalars().first()
    if exists:
        return exists

    p = Printer(
        ip=req.ip,
        name=req.name or req.ip,
        status="Unknown",
        archived=False
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return p

@router.delete("/{printer_id}")
async def archive_printer(printer_id: int, db: AsyncSession = Depends(get_session)):
    row = (await db.execute(select(Printer).where(Printer.id == printer_id))).scalars().first()
    if not row:
        raise HTTPException(404, "Printer not found")
    row.archived = True
    await db.commit()
    return {"ok": True}

@router.post("/{printer_id}/restore")
async def restore_printer(printer_id: int, db: AsyncSession = Depends(get_session)):
    row = (await db.execute(select(Printer).where(Printer.id == printer_id))).scalars().first()
    if not row:
        raise HTTPException(404, "Printer not found")
    row.archived = False
    await db.commit()
    return {"ok": True}

@router.get("/{printer_id}", response_model=PrinterDetail)
async def get_printer(printer_id: int, db: AsyncSession = Depends(get_session)):
    row = (await db.execute(select(Printer).where(Printer.id == printer_id))).scalars().first()
    if not row:
        raise HTTPException(404, "Printer not found")

    supplies = []
    if row.supplies_json:
        try:
            supplies = json.loads(row.supplies_json).get("supplies", [])
        except:
            supplies = []

    return PrinterDetail(
        id=row.id,
        name=row.name,
        ip=row.ip,
        status=row.status,
        vendor=row.vendor,
        model=row.model,
        serial=row.serial,
        last_seen=row.last_seen,
        supplies=supplies
    )

@router.post("/{printer_id}/refresh")
async def refresh_printer(printer_id: int, db: AsyncSession = Depends(get_session)):
    row = (await db.execute(select(Printer).where(Printer.id == printer_id))).scalars().first()
    if not row:
        raise HTTPException(404, "Printer not found")

    snap = fetch_printer_snapshot(
        ip=row.ip,
        community=settings.PRINTER_SNMP_COMMUNITY,
        timeout=settings.PRINTER_SNMP_TIMEOUT,
        retries=settings.PRINTER_SNMP_RETRIES,
    )
    row.vendor = snap.get("vendor")
    row.model = snap.get("model")
    row.serial = snap.get("serial")
    row.last_seen = datetime.now(timezone.utc)
    row.status = "Healthy"
    row.supplies_json = json.dumps(snap)
    await db.commit()

    return {"ok": True, "snapshot": snap}

# ---------------------------
# WebSocket for live toner feed
# ---------------------------

@router.websocket("/ws/{printer_id}")
async def ws_printer(websocket: WebSocket, printer_id: int, db: AsyncSession = Depends(get_session)):
    await websocket.accept()

    try:
        while True:
            row = (await db.execute(select(Printer).where(Printer.id == printer_id))).scalars().first()
            if not row:
                await websocket.send_json({"error": "not_found"})
                await websocket.close()
                return

            snap = fetch_printer_snapshot(
                ip=row.ip,
                community=settings.PRINTER_SNMP_COMMUNITY,
                timeout=settings.PRINTER_SNMP_TIMEOUT,
                retries=settings.PRINTER_SNMP_RETRIES,
            )

            row.vendor = snap.get("vendor")
            row.model = snap.get("model")
            row.serial = snap.get("serial")
            row.status = "Healthy"
            row.last_seen = datetime.now(timezone.utc)
            row.supplies_json = json.dumps(snap)
            await db.commit()

            await websocket.send_json({
                "id": row.id,
                "name": row.name,
                "ip": row.ip,
                "vendor": row.vendor,
                "model": row.model,
                "serial": row.serial,
                "status": row.status,
                "last_seen": row.last_seen.isoformat() if row.last_seen else None,
                "supplies": snap.get("supplies", []),
                "ts": snap.get("ts"),
            })

            await asyncio.sleep(settings.PRINTER_WS_INTERVAL_SEC)

    except WebSocketDisconnect:
        return