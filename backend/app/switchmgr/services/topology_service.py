import asyncio
from easysnmp import Session
from app.switchmgr.services.driver_resolver import driver_for_switch


async def probe_sysdescr(ip: str, community: str = "public", timeout: int = 2):
    try:
        sess = Session(
            hostname=ip,
            community=community,
            version=2,
            timeout=timeout,
            retries=1,
        )
        d = sess.get("1.3.6.1.2.1.1.1.0")
        return d.value if d else None
    except Exception:
        return None


async def load_drv(ip: str, community="public"):
    desc = await probe_sysdescr(ip, community)
    if not desc:
        return None
    cls = driver_for_switch(desc)
    return cls(ip=ip, community=community) if cls else None


async def get_stp_info(drv):
    try:
        sess = Session(
            hostname=drv.ip,
            community=drv.community,
            version=2,
            timeout=2,
            retries=1,
        )
        root = sess.get("1.3.6.1.2.1.17.2.5.0")  # dot1dStpDesignatedRoot
        root_port = sess.get("1.3.6.1.2.1.17.2.7.0")  # dot1dStpRootPort
        return {
            "root_bridge": root.value if root else None,
            "root_port": root_port.value if root_port else None,
        }
    except Exception:
        return {}


async def get_vlan_map(drv):
    try:
        # Q-BRIDGE-MIB
        sess = Session(
            hostname=drv.ip,
            community=drv.community,
            version=2,
            timeout=2,
            retries=1,
        )
        vlans = sess.walk("1.3.6.1.2.1.17.7.1.4.3.1.1")
        res = {}
        for v in vlans:
            vlan = int(v.oid_index)
            res[vlan] = v.value
        return res
    except Exception:
        return {}


async def analyze_loops(graph):
    """
    Simple heuristic loop detection:
    If two switches report each other on more than one port unexpectedly.
    """
    pairs = {}
    for link in graph["links"]:
        key = tuple(sorted([link["source"], link["target"]]))
        pairs.setdefault(key, 0)
        pairs[key] += 1

    loops = [p for p, count in pairs.items() if count > 2]
    return loops


async def build_topology(switch_ips: list[str], community="public"):
    graph = {"nodes": [], "links": [], "stp": {}, "loops": [], "vlans": {}}
    drivers = {}

    # Load drivers
    for ip in switch_ips:
        drv = await load_drv(ip, community)
        if drv:
            drivers[ip] = drv

    # Basic nodes
    for ip, drv in drivers.items():
        status = await drv.get_status()
        graph["nodes"].append({
            "id": ip,
            "vendor": status.get("vendor"),
            "model": status.get("model"),
            "sysname": status.get("sys_name"),
        })

    # Links
    for ip, drv in drivers.items():
        lldp = await drv.get_lldp_neighbors()
        for n in lldp:
            graph["links"].append({
                "source": ip,
                "target": n["remote_name"],
                "local_port": n["local_port"],
                "remote_port": n["remote_port"],
                "type": "lldp",
            })

        if hasattr(drv, "get_cdp_neighbors"):
            try:
                cdp = await drv.get_cdp_neighbors()
            except Exception:
                cdp = []
            for n in cdp:
                graph["links"].append({
                    "source": ip,
                    "target": n["remote_name"],
                    "local_port": n["local_port"],
                    "remote_port": n["remote_port"],
                    "type": "cdp",
                })

    # STP info
    for ip, drv in drivers.items():
        graph["stp"][ip] = await get_stp_info(drv)

    # VLAN map
    for ip, drv in drivers.items():
        graph["vlans"][ip] = await get_vlan_map(drv)

    # Loop detection
    graph["loops"] = await analyze_loops(graph)

    return graph