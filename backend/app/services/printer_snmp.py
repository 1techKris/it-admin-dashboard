# backend/app/services/printer_snmp.py

from easysnmp import Session, EasySNMPError
from typing import Dict, Any, List
import time

# Printer-MIB supplies table:
# prtMarkerSuppliesDescription: 1.3.6.1.2.1.43.11.1.1.6
# prtMarkerSuppliesMaxCapacity: 1.3.6.1.2.1.43.11.1.1.8
# prtMarkerSuppliesLevel:       1.3.6.1.2.1.43.11.1.1.9

OID_BASE_DESC = "1.3.6.1.2.1.43.11.1.1.6"
OID_BASE_MAX  = "1.3.6.1.2.1.43.11.1.1.8"
OID_BASE_LVL  = "1.3.6.1.2.1.43.11.1.1.9"

# Optional:
OID_SYSDESCR       = "1.3.6.1.2.1.1.1.0"
OID_DEVICE_NAME    = "1.3.6.1.2.1.43.5.1.1.16.1"
OID_DEVICE_SERIAL  = "1.3.6.1.2.1.43.5.1.1.17.1"


def _session(ip: str, community: str, timeout: float, retries: int) -> Session:
    return Session(
        hostname=ip,
        community=community,
        version=2,
        timeout=int(timeout),
        retries=int(retries)
    )


def _safe_get(session: Session, oid: str) -> str | None:
    try:
        item = session.get(oid)
        return item.value if item else None
    except EasySNMPError:
        return None
    except Exception:
        return None


def _safe_walk(session: Session, oid: str) -> List[Any]:
    try:
        return session.walk(oid)
    except EasySNMPError:
        return []
    except Exception:
        return []


def fetch_printer_snapshot(ip: str, community: str, timeout: float = 2.0, retries: int = 1) -> Dict[str, Any]:
    """
    Builds a snapshot:
    {
      "ip": ip,
      "vendor": "...",
      "model": "...",
      "serial": "...",
      "name": "...",
      "supplies": [{...}],
      "ts": epoch
    }
    """

    s = _session(ip, community, timeout, retries)

    sysdescr = _safe_get(s, OID_SYSDESCR) or ""
    dev_name = _safe_get(s, OID_DEVICE_NAME)
    serial = _safe_get(s, OID_DEVICE_SERIAL)

    vendor = None
    model = None

    if sysdescr:
        parts = sysdescr.split()
        if parts:
            vendor = parts[0][:64]
        model = sysdescr[:128]

    descs = _safe_walk(s, OID_BASE_DESC)
    maxes = _safe_walk(s, OID_BASE_MAX)
    lvls  = _safe_walk(s, OID_BASE_LVL)

    def extract_index(oid: str) -> int:
        try:
            return int(oid.split(".")[-1])
        except:
            return -1

    dmap: Dict[int, Dict[str, Any]] = {}

    for item in descs:
        i = extract_index(item.oid)
        if i >= 0:
            dmap.setdefault(i, {})["description"] = item.value

    for item in maxes:
        i = extract_index(item.oid)
        if i >= 0:
            try:
                dmap.setdefault(i, {})["max"] = int(item.value)
            except:
                dmap.setdefault(i, {})["max"] = -1

    for item in lvls:
        i = extract_index(item.oid)
        if i >= 0:
            try:
                dmap.setdefault(i, {})["level"] = int(item.value)
            except:
                dmap.setdefault(i, {})["level"] = -3

    supplies = []
    for i, row in sorted(dmap.items(), key=lambda x: x[0]):
        level = row.get("level", -3)
        maxc = row.get("max", -1)
        percent = None

        # normal case
        if level >= 0 and maxc > 0:
            percent = max(0, min(100, int((level / maxc) * 100)))
        # fallback if max is meaningless
        elif level >= 0:
            if 0 <= level <= 100:
                percent = level

        supplies.append({
            "index": i,
            "description": row.get("description") or f"Supply {i}",
            "level": level,
            "max": maxc,
            "percent": percent,
        })

    return {
        "ip": ip,
        "vendor": vendor,
        "model": model,
        "serial": serial,
        "name": dev_name,
        "supplies": supplies,
        "ts": int(time.time()),
    }