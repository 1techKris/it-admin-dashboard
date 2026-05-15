import asyncio
from app.switchmgr.services.topology_service import load_drv
from easysnmp import Session


async def get_lldp_neighbors_safe(drv):
    try:
        return await drv.get_lldp_neighbors()
    except Exception:
        return []


async def get_cdp_neighbors_safe(drv):
    if not hasattr(drv, "get_cdp_neighbors"):
        return []
    try:
        return await drv.get_cdp_neighbors()
    except Exception:
        return []


async def get_fdb_links(ip, community="public"):
    """Return MAC-based inferred links from the switch FDB table."""
    try:
        sess = Session(
            hostname=ip,
            community=community,
            version=2,
            timeout=2,
            retries=1,
        )
        fdb = sess.walk("1.3.6.1.2.1.17.4.3.1.2")  # dot1dTpFdbPort
        mapping = {}  # port -> count
        for e in fdb:
            port = int(e.value)
            mapping.setdefault(port, 0)
            mapping[port] += 1
        # Ports with heavy MAC concentration usually lead to uplinks
        return mapping
    except Exception:
        return {}


async def discover_switches(seed_ips: list[str], community="public"):
    """
    Multi-phase switch discovery:
    1. LLDP/CDP crawl
    2. Bridge-MIB FDB uplink inference
    3. ARP table discovery
    """
    discovered = set()
    queue = list(seed_ips)
    drivers = {}

    while queue:
        ip = queue.pop(0)
        if ip in discovered:
            continue

        drv = await load_drv(ip, community)
        if not drv:
            continue

        drivers[ip] = drv
        discovered.add(ip)

        # Phase 1 — LLDP/CDP neighbors
        lldp = await get_lldp_neighbors_safe(drv)
        for n in lldp:
            neigh = n["remote_name"]
            if neigh not in discovered:
                queue.append(neigh)

        cdp = await get_cdp_neighbors_safe(drv)
        for n in cdp:
            neigh = n["remote_name"]
            if neigh not in discovered:
                queue.append(neigh)

        # Phase 2 — Bridge-MIB link inference
        fdb = await get_fdb_links(ip, community)
        # Ports with many MACs tend to be uplinks to switches
        uplink_ports = [p for p, count in fdb.items() if count > 50]

        # No direct IP from FDB; real logic matches MAC→IP if you want.
        # For now, we just record uplink ports inside results.
        # They can be displayed in UI.
        drv._uplinks = uplink_ports

    return {
        "switches": sorted(discovered),
        "uplinks": {ip: drv._uplinks for ip, drv in drivers.items()},
    }