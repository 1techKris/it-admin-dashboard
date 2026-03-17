# backend/app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, text

from app.core.config import settings

# Unified Base (ALL MODELS MUST USE THIS)
from app.models.base import Base

# Import ALL models so SQLAlchemy registers them
from app.models import __all_models__  # critical

# Routers
from app.api.v1.routers.devices import router as devices_router
from app.api.v1.routers.alerts import router as alerts_router
from app.api.v1.routers.ad import router as ad_router
from app.api.v1.routers.settings import router as settings_router
from app.api.v1.routers.network import router as network_router
from app.api.v1.routers.devices_ws import router as devices_ws_router
from app.api.v1.routers.device_actions import router as device_actions_router
from app.api.v1.routers.device_edit import router as device_edit_router
from app.api.v1.routers.printers import router as printers_router
from app.api.v1.routers.settings_ad import router as settings_ad_router

# VPN
from app.api.v1.routers.settings_vpn import router as settings_vpn_router
from app.api.v1.routers.vpn import router as vpn_router
from app.api.v1.routers.vpn_alerts import router as vpn_alerts_router
from app.api.v1.routers.vpn_history import router as vpn_history_router

# DB
from app.db.session import engine, AsyncSessionLocal

# Background services
from app.services import device_monitor
from app.services.ad_config import warm_settings_cache
from app.services.background_scheduler import vpn_monitor_loop
from app.services.vpn_history_service import init_history_db

import os
import sqlite3
import asyncio


app = FastAPI(title=settings.APP_NAME)


# -------------------------------------------------------------------
# CORS
# -------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------------------------------------------------------
# ROUTERS
# -------------------------------------------------------------------
app.include_router(devices_router,        prefix=settings.API_V1_PREFIX)
app.include_router(alerts_router,         prefix=settings.API_V1_PREFIX)
app.include_router(ad_router,             prefix=settings.API_V1_PREFIX)
app.include_router(settings_router,       prefix=settings.API_V1_PREFIX)
app.include_router(network_router,        prefix=settings.API_V1_PREFIX)
app.include_router(devices_ws_router,     prefix=settings.API_V1_PREFIX)
app.include_router(device_actions_router, prefix=settings.API_V1_PREFIX)
app.include_router(device_edit_router,    prefix=settings.API_V1_PREFIX)
app.include_router(printers_router,       prefix=settings.API_V1_PREFIX)
app.include_router(settings_ad_router,    prefix=settings.API_V1_PREFIX)

# VPN
app.include_router(settings_vpn_router, prefix=settings.API_V1_PREFIX)
app.include_router(vpn_router,          prefix=settings.API_V1_PREFIX)
app.include_router(vpn_alerts_router,   prefix=settings.API_V1_PREFIX)
app.include_router(vpn_history_router,  prefix=settings.API_V1_PREFIX)


# -------------------------------------------------------------------
# Migration helpers
# -------------------------------------------------------------------
async def _column_exists(conn, table: str, col: str) -> bool:
    res = await conn.execute(text(f"PRAGMA table_info({table})"))
    cols = [r[1] for r in res.fetchall()]
    return col in cols


async def _safe_add_column(conn, ddl: str):
    try:
        await conn.execute(text(ddl))
    except Exception:
        pass


# -------------------------------------------------------------------
# VPN History DB (separate sqlite file)
# -------------------------------------------------------------------
VPN_DB_PATH = "/home/administrator/it-admin-dashboard/backend/vpn_history.sqlite3"

def _init_vpn_history_db_file():
    if not os.path.exists(VPN_DB_PATH):
        conn = sqlite3.connect(VPN_DB_PATH)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.close()


# -------------------------------------------------------------------
# Delay wrapper for vpn_monitor_loop
# -------------------------------------------------------------------
async def _delayed_vpn_monitor_start():
    # Allow time for DB tables to finish creation & commit
    await asyncio.sleep(3)
    await vpn_monitor_loop()


# -------------------------------------------------------------------
# STARTUP
# -------------------------------------------------------------------
@app.on_event("startup")
async def on_startup():

    # --- Ensure VPN history DB exists + table created ---
    _init_vpn_history_db_file()
    init_history_db()

    # --- Create ALL main DB tables ---
    # (ALL models imported via __all_models__)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # --- Devices migrations ---
        if not await _column_exists(conn, "devices", "archived"):
            await _safe_add_column(conn, "ALTER TABLE devices ADD COLUMN archived BOOLEAN DEFAULT 0")

        if not await _column_exists(conn, "devices", "last_seen"):
            await _safe_add_column(conn, "ALTER TABLE devices ADD COLUMN last_seen DATETIME NULL")

        if not await _column_exists(conn, "devices", "latency_ms"):
            await _safe_add_column(conn, "ALTER TABLE devices ADD COLUMN latency_ms INTEGER NULL")

        if not await _column_exists(conn, "devices", "custom_name"):
            await _safe_add_column(conn, "ALTER TABLE devices ADD COLUMN custom_name TEXT NULL")

        # --- Printers migrations ---
        if not await _column_exists(conn, "printers", "archived"):
            await _safe_add_column(conn, "ALTER TABLE printers ADD COLUMN archived BOOLEAN DEFAULT 0")

        if not await _column_exists(conn, "printers", "supplies_json"):
            await _safe_add_column(conn, "ALTER TABLE printers ADD COLUMN supplies_json TEXT NULL")

        if not await _column_exists(conn, "printers", "last_seen"):
            await _safe_add_column(conn, "ALTER TABLE printers ADD COLUMN last_seen DATETIME NULL")

    # --- Seed demo devices if empty ---
    async with AsyncSessionLocal() as db:
        from app.models.device import Device
        res = await db.execute(select(Device))
        if not res.scalars().first():
            db.add_all([
                Device(device_id="SRV-01", type="Server", os="Windows Server 2022", ip="10.0.0.21", cpu=37, mem=61, status="Healthy"),
                Device(device_id="SRV-02", type="Server", os="Ubuntu 22.04", ip="10.0.0.22", cpu=71, mem=78, status="Warning"),
                Device(device_id="CL-101", type="Client", os="Windows 11", ip="10.0.10.101", cpu=12, mem=43, status="Healthy"),
                Device(device_id="FW-01", type="Network", os="FortiOS", ip="10.0.254.1", cpu=33, mem=41, status="Critical"),
            ])
            await db.commit()

    # --- Warm AD + VPN settings ---
    await warm_settings_cache()

    # --- Start background monitors ---
    device_monitor.start(app)

    # Delayed start fixes:
    #   - "no such table: vpn_alert_rules"
    #   - "no such table: vpn_history"
    asyncio.create_task(_delayed_vpn_monitor_start())


# -------------------------------------------------------------------
# SHUTDOWN
# -------------------------------------------------------------------
@app.on_event("shutdown")
async def on_shutdown():
    await device_monitor.stop(app)


# -------------------------------------------------------------------
# HEALTHCHECK
# -------------------------------------------------------------------
@app.get("/healthz")
async def healthz():
    return {"status": "ok"}