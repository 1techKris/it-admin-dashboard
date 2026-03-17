from fastapi import APIRouter
from pydantic import BaseModel
from app.services.ad_config import save_setting, get_setting

router = APIRouter(prefix="/settings/vpn", tags=["settings-vpn"])

class VPNSettingsBody(BaseModel):
    vpn_server: str
    vpn_user: str
    vpn_password: str

@router.get("")
async def get_vpn_settings():
    cfg = get_setting("vpn") or {}
    masked = cfg.copy()
    masked["vpn_password"] = None
    return masked

@router.put("")
async def put_vpn_settings(body: VPNSettingsBody):
    save_setting("vpn", body.dict())
    return {"ok": True}

@router.post("/test")
async def test_vpn_settings(body: VPNSettingsBody):
    save_setting("vpn", body.dict())
    from app.services.vpn_service import get_vpn_sessions
    result = get_vpn_sessions()
    return {"ok": True, "sample": len(result.get("connected", []))}