# backend/app/services/ad_config.py

from __future__ import annotations
import json
from typing import Any, Dict, Optional
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.app_setting import AppSetting

"""
This module provides:
 - AD configuration cache (legacy)
 - Generic AppSetting: get_setting(key), save_setting(key, dict)
"""

# ---------------------------
# AD CONFIG (legacy behavior)
# ---------------------------

_ad_cache: Dict[str, Any] = {
    "server": "",
    "user": "",
    "password": "",
    "base_dn": "",
    "use_ssl": False,
    "page_size": 200,
}


def set_ad_config(cfg: Dict[str, Any]):
    """Update in‑memory AD config cache."""
    global _ad_cache
    _ad_cache.update(cfg)


def get_ad_config() -> Dict[str, Any]:
    """Return current AD config cache."""
    return _ad_cache


# ---------------------------
# GENERIC APP SETTINGS (VPN, SMTP, etc)
# ---------------------------

_settings_cache: Dict[str, Dict[str, Any]] = {}  # key → value dict


async def _db_get_setting(key: str) -> Optional[Dict[str, Any]]:
    async with AsyncSessionLocal() as db:
        row = (
            await db.execute(select(AppSetting).where(AppSetting.key == key))
        ).scalars().first()

        if row:
            try:
                return json.loads(row.value)
            except Exception:
                return None
        return None


async def _db_save_setting(key: str, value: Dict[str, Any]):
    async with AsyncSessionLocal() as db:
        row = (
            await db.execute(select(AppSetting).where(AppSetting.key == key))
        ).scalars().first()

        if row:
            row.value = json.dumps(value)
        else:
            row = AppSetting(key=key, value=json.dumps(value))
            db.add(row)

        await db.commit()


# ---------------------------
# PUBLIC API
# ---------------------------

def get_setting(key: str) -> Optional[Dict[str, Any]]:
    """Return a setting from cache, or load from DB if missing."""
    return _settings_cache.get(key)


def set_setting_in_cache(key: str, cfg: Dict[str, Any]):
    """Store setting in memory only (used after PUT endpoints)."""
    _settings_cache[key] = cfg


def save_setting(key: str, cfg: Dict[str, Any]):
    """
    Synchronous wrapper to:
      - update cache
      - write to DB (fire & forget)
    """
    _settings_cache[key] = cfg

    # async DB write — schedule for next event loop tick
    import asyncio
    asyncio.create_task(_db_save_setting(key, cfg))


# ---------------------------
# STARTUP INITIALIZATION
# ---------------------------

async def warm_settings_cache():
    """Warm both caches on startup (AD + generic)."""
    # Load AD settings → AD cache
    ad_cfg = await _db_get_setting("ad")
    if ad_cfg:
        set_ad_config(ad_cfg)

    # Load VPN, SMTP or others if present
    for key in ("vpn", "smtp", "email", "notifications"):
        cfg = await _db_get_setting(key)
        if cfg:
            set_setting_in_cache(key, cfg)