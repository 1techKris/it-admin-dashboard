from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Any, Dict, Optional
import json
from ldap3 import Server, Connection, ALL
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_session
from app.models.app_setting import AppSetting
from app.services import ad_config

router = APIRouter(prefix="/settings", tags=["settings"])

SETTINGS_KEY_AD = "ad"

class ADSettingsBody(BaseModel):
    server: Optional[str] = Field(default=None)
    user: Optional[str] = Field(default=None)
    password: Optional[str] = Field(default=None)  # None/empty means "do not change" on update
    base_dn: Optional[str] = Field(default=None)
    use_ssl: Optional[bool] = Field(default=None)
    page_size: Optional[int] = Field(default=None)

def _load(db_value: Optional[str]) -> Dict[str, Any]:
    try:
        return json.loads(db_value) if db_value else {}
    except Exception:
        return {}

async def _get_setting(db: AsyncSession) -> Dict[str, Any]:
    row = (await db.execute(select(AppSetting).where(AppSetting.key == SETTINGS_KEY_AD))).scalars().first()
    return _load(row.value) if row else {}

async def _save_setting(db: AsyncSession, cfg: Dict[str, Any]):
    row = (await db.execute(select(AppSetting).where(AppSetting.key == SETTINGS_KEY_AD))).scalars().first()
    if not row:
        row = AppSetting(key=SETTINGS_KEY_AD, value=json.dumps(cfg))
        db.add(row)
    else:
        row.value = json.dumps(cfg)
    await db.commit()

@router.get("/ad")
async def get_ad_settings(db: AsyncSession = Depends(get_session)):
    db_cfg = await _get_setting(db)
    # merge with current cache/defaults (and mask password)
    if db_cfg:
        ad_config.set_ad_config(db_cfg)
    return ad_config.masked_config()

@router.put("/ad")
async def put_ad_settings(body: ADSettingsBody, db: AsyncSession = Depends(get_session)):
    # Load current from DB, merge fields; if password is None/empty, keep previous
    current = await _get_setting(db)
    merged = dict(current)
    for k in ("server", "user", "base_dn", "use_ssl", "page_size"):
        v = getattr(body, k)
        if v is not None:
            merged[k] = v
    # Password handling
    if body.password is not None and body.password != "":
        merged["password"] = body.password
    elif "password" not in merged and body.password is None:
        merged["password"] = None  # no prior, still None

    await _save_setting(db, merged)
    # refresh in-process cache
    ad_config.set_ad_config(merged)
    return {"ok": True}

class ADSettingsTestBody(ADSettingsBody):
    pass

@router.post("/ad/test")
async def test_ad_settings(body: ADSettingsTestBody):
    # Test with provided body merged over current cache/defaults
    cfg = ad_config.get_ad_config().copy()
    for k in ("server", "user", "base_dn", "use_ssl", "page_size"):
        v = getattr(body, k)
        if v is not None:
            cfg[k] = v
    if body.password is not None and body.password != "":
        cfg["password"] = body.password
    # Try bind
    try:
        srv = Server(cfg["server"], use_ssl=cfg.get("use_ssl", False), get_info=ALL)
        conn = Connection(srv, user=cfg["user"], password=cfg.get("password"), auto_bind=True)
        conn.unbind()
        return {"ok": True}
    except Exception as e:
        raise HTTPException(400, f"Bind failed: {e}")