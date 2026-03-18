# backend/app/services/os_fingerprint.py
from typing import List, Optional, Dict, Any

def guess_device_type(
    open_ports: List[int],
    hostname: Optional[str] = None,
    ssh_banner: Optional[str] = None,
    http_banner: Optional[str] = None,
    netbios_name: Optional[str] = None,
    sysdescr: Optional[str] = None,          # ← NEW: from SNMP
) -> Dict[str, str]:
    """
    Returns a best-guess inventory dict:
    {
        "device_type": "Switch" | "Server" | "Printer" | ...
        "vendor": "...",
        "model": "..."
    }
    """
    p = set(open_ports or [])
    name = (hostname or netbios_name or "").upper()
    banners = (ssh_banner or "") + (http_banner or "") + (sysdescr or "")
    banners_upper = banners.upper()

    # === SNMP sysDescr is the gold standard when available ===
    if sysdescr:
        if any(k in sysdescr for k in ["Catalyst", "Switch", "2960", "3560", "3750", "3850"]):
            return {"device_type": "Switch", "vendor": "Cisco", "model": sysdescr[:100]}
        if any(k in sysdescr for k in ["HPE", "Aruba", "ProCurve", "Switch"]):
            return {"device_type": "Switch", "vendor": "HPE", "model": sysdescr[:100]}
        if "Juniper" in sysdescr or "EX Series" in sysdescr:
            return {"device_type": "Switch", "vendor": "Juniper", "model": sysdescr[:100]}
        if any(k in sysdescr for k in ["Forti", "Firewall", "Router"]):
            return {"device_type": "Router/Firewall", "vendor": "Fortinet", "model": sysdescr[:100]}

    # === Fallback heuristics ===
    if 9100 in p or any(k in name for k in ["NPI", "XRX", "HP", "XEROX", "BROTHER", "CANON"]):
        return {"device_type": "Printer", "vendor": "Unknown", "model": name or "Printer"}

    if any(k in name for k in ["SW", "SWITCH", "CISCO", "ARUBA", "DELL", "JUNIPER", "HPE"]) or "SWITCH" in banners_upper:
        return {"device_type": "Switch", "vendor": "Unknown", "model": name or "Network Switch"}

    if 445 in p or 3389 in p or "SERVER" in name or "DC-" in name:
        return {"device_type": "Server", "vendor": "Unknown", "model": name or "Windows Server"}

    if 22 in p and "OpenSSH" in (ssh_banner or ""):
        return {"device_type": "Server", "vendor": "Linux", "model": "Linux Server"}

    if 80 in p or 443 in p:
        return {"device_type": "Embedded", "vendor": "Unknown", "model": name or "Web Device"}

    return {"device_type": "Client/Unknown", "vendor": "Unknown", "model": name or "Unknown Device"}