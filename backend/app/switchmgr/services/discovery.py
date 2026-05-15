from app.models.device import Device
from app.switchmgr.models.switch import Switch
from sqlalchemy.ext.asyncio import AsyncSession

SWITCH_KEYWORDS = ["switch", "cisco", "hp", "aruba", "ubnt", "mikrotik", "netgear"]


async def detect_switch(r):
    """Return True if a scan HostResult is likely a switch."""
    dev = (r.os or "").lower()
    name = (r.hostname or "").lower()
    vendor = (r.vendor or "").lower()

    for kw in SWITCH_KEYWORDS:
        if kw in dev or kw in name or kw in vendor:
            return True
    return False


async def import_switches_from_scan(scan_state, db: AsyncSession):
    created = 0
    for r in scan_state.results.values():
        if not await detect_switch(r):
            continue

        sw = await db.get(Switch, r.ip)
        if sw:
            continue

        new_sw = Switch(
            id=r.ip,
            ip=r.ip,
            hostname=r.hostname,
            vendor=r.vendor,
            model=r.model,
            os_version=r.os,
        )

        db.add(new_sw)
        created += 1

    await db.commit()
    return created