from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_session
from app.models.device import Device
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(prefix="/servers", tags=["servers"])

class DeviceOut(BaseModel):
    device_id: str
    type: str
    os: str
    ip: str
    cpu: int
    mem: int
    status: str
    archived: bool | None = False
    last_seen: datetime | None = None
    latency_ms: int | None = None

    class Config:
        from_attributes = True

@router.get("", response_model=List[DeviceOut])
async def list_devices(
    q: str | None = Query(default=None),
    status: str | None = Query(default=None),
    page: int = 1,
    page_size: int = 50,
    include_archived: bool = False,
    db: AsyncSession = Depends(get_session),
):
    stmt = select(Device)
    if not include_archived:
        stmt = stmt.where(Device.archived == False)  # noqa: E712
    if status and status.lower() != "all":
        stmt = stmt.where(Device.status == status)
    if q:
        like = f"%{q.lower()}%"
        # basic like on device_id or ip
        # SQLite is case-insensitive by default for ascii
        stmt = stmt.where((Device.device_id.ilike(like)) | (Device.ip.ilike(like)))
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(stmt)).scalars().all()
    return [DeviceOut.model_validate(r) for r in rows]

@router.delete("/{device_id}")
async def archive_device(device_id: str, db: AsyncSession = Depends(get_session)):
    row = (await db.execute(select(Device).where(Device.device_id == device_id))).scalars().first()
    if not row:
        raise HTTPException(status_code=404, detail="Device not found")
    row.archived = True
    await db.commit()
    return {"ok": True, "device_id": device_id, "archived": True}

@router.post("/{device_id}/restore")
async def restore_device(device_id: str, db: AsyncSession = Depends(get_session)):
    row = (await db.execute(select(Device).where(Device.device_id == device_id))).scalars().first()
    if not row:
        raise HTTPException(status_code=404, detail="Device not found")
    row.archived = False
    await db.commit()
    return {"ok": True, "device_id": device_id, "archived": False}