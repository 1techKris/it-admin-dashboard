# backend/app/switchmgr/services/port_realtime.py

import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.switchmgr.websocket_manager import broadcast
from app.switchmgr.models.switch import Switch
from app.switchmgr.services.switch_service import fetch_and_sync_ports
from app.db.session import AsyncSessionLocal


async def watch_switch(switch: Switch):
    """Continuously poll switch ports and broadcast changes."""
    prev_state = {}

    while True:
        try:
            async with AsyncSessionLocal() as db:
                ports = await fetch_and_sync_ports(switch, db)

            # Convert to dict keyed by port number
            latest = {p["port"]: p for p in ports}

            # Detect changes
            changed = []
            for port, info in latest.items():
                if port not in prev_state or prev_state[port] != info:
                    changed.append(info)

            if changed:
                await broadcast(
                    f"switch:{switch.id}",
                    {"type": "port_update", "switch_id": switch.id, "ports": changed},
                )

            prev_state = latest

        except Exception as e:
            print(f"[REALTIME] Error watching switch {switch.id}: {e}")

        await asyncio.sleep(5)  # poll interval