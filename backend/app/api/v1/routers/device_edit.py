from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_session
from app.models.device import Device

router = APIRouter(prefix="/servers", tags=["servers"])

class EditDeviceRequest(BaseModel):
    os: str | None = None
    custom_name: str | None = None
    type: str | None = None
    status: str | None = None

@router.post("/{device_id}/edit")
async def edit_device(device_id: str, req: EditDeviceRequest, db: AsyncSession = Depends(get_session)):
    row = (await db.execute(select(Device).where(Device.device_id == device_id))).scalars().first()
    if not row:
        raise HTTPException(status_code=404, detail="Device not found")

    if req.os is not None:
        row.os = req.os

    if req.custom_name is not None:
        row.custom_name = req.custom_name

    if req.type is not None:
        row.type = req.type

    if req.status is not None:
        row.status = req.status

    await db.commit()
    return {"ok": True, "device_id": device_id}