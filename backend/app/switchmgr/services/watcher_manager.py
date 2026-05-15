# backend/app/switchmgr/services/watcher_manager.py

import asyncio
from app.db.session import AsyncSessionLocal
from sqlalchemy import select
from app.switchmgr.models.switch import Switch
from .port_realtime import watch_switch


async def start_watchers():
    """Start a watch task for each switch."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Switch))
        switches = result.scalars().all()

    for sw in switches:
        asyncio.create_task(watch_switch(sw))

    print(f"[WATCHERS] Started {len(switches)} switch watchers.")