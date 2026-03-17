# backend/app/services/os_fingerprint.py
from typing import List, Optional

def guess_os(
    open_ports: List[int],
    ssh_banner: Optional[str],
    http_banner: Optional[str],
    netbios_name: Optional[str],
) -> str:
    # Simple heuristics:
    p = set(open_ports or [])
    name = (netbios_name or "").upper()

    # Printers (many vendor naming schemes)
    if 9100 in p or name.startswith("NPI") or name.startswith("XRX") or "HP" in name or "XEROX" in name:
        return "Printer"
    # Windows
    if 445 in p or 3389 in p or name:
        return "Windows"
    # Linux/Unix via SSH banner
    if 22 in p and ssh_banner and "OpenSSH" in ssh_banner:
        return "Linux"
    # Web-only embedded devices
    if 80 in p or 443 in p:
        return "Embedded"
    return "Unknown"