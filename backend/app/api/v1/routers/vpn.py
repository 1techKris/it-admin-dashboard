# backend/app/api/v1/routers/vpn.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.vpn_service import get_vpn_sessions, disconnect_vpn_user

router = APIRouter(prefix="/vpn", tags=["vpn"])


class DisconnectBody(BaseModel):
    username: str


@router.get("/sessions")
async def vpn_sessions():
    return get_vpn_sessions()


@router.post("/disconnect")
async def vpn_disconnect(body: DisconnectBody):
    ok = disconnect_vpn_user(body.username)
    if not ok:
        raise HTTPException(500, "Failed to disconnect VPN user")
    return {"ok": True}