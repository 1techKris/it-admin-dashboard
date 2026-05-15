# backend/app/switchmgr/api/ws_switch.py

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.switchmgr.websocket_manager import register, unregister
from app.switchmgr.services.switch_service import fetch_and_sync_ports
from app.db.session import get_session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.switchmgr.models.switch import Switch
import asyncio

router = APIRouter(prefix="/switch/ws", tags=["switch-ws"])

@router.websocket("/{switch_id}")
async def switch_ws(websocket: WebSocket, switch_id: str):
    await websocket.accept()
    group = f"switch:{switch_id}"
    await register(group, websocket)

    try:
        while True:
            await asyncio.sleep(60)  # heartbeat/ping
    except WebSocketDisconnect:
        await unregister(group, websocket)