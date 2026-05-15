# backend/app/services/fingerprint_engine.py

"""
Unified fingerprinting & classification engine.

This file receives raw scan data:
- open_ports
- banners
- hostname
- sysdescr
- etc.

And produces:
- device_class
- vendor
- model
- os

Classification is based on a weighted scoring engine.
"""

import re


def _score(scores, key, amount):
    """Increase classification score for a type."""
    scores[key] = scores.get(key, 0) + amount


def classify_device(
    ip: str,
    open_ports: list[int],
    banners: dict,
    hostname: str | None,
    sysdescr: str | None,
):
    scores = {}
    vendor = None
    model = None
    os = None

    hostname_l = (hostname or "").lower()
    sysdescr_l = (sysdescr or "").lower()

    # ----------------------------------------------------------------------
    # VENDOR EXTRACTION
    # ----------------------------------------------------------------------

    if sysdescr:
        if "cisco" in sysdescr_l:
            vendor = "Cisco"
        elif "hewlett" in sysdescr_l or "hp" in sysdescr_l or "aruba" in sysdescr_l:
            vendor = "HP/HPE/Aruba"
        elif "dell" in sysdescr_l:
            vendor = "Dell"
        elif "mikrotik" in sysdescr_l or "routeros" in sysdescr_l:
            vendor = "Mikrotik"
        elif "ubiquiti" in sysdescr_l or "unifi" in sysdescr_l:
            vendor = "Ubiquiti"
        elif "hikvision" in sysdescr_l:
            vendor = "Hikvision"
        elif "dahua" in sysdescr_l:
            vendor = "Dahua"
        elif "axis" in sysdescr_l:
            vendor = "Axis"
        elif "fortinet" in sysdescr_l or "fortigate" in sysdescr_l:
            vendor = "Fortinet"

    # ----------------------------------------------------------------------
    # BANNER VENDOR GUESS
    # ----------------------------------------------------------------------

    for b in banners.values():
        b_l = b.lower()
        if "cisco" in b_l:
            vendor = vendor or "Cisco"
        elif "mikrotik" in b_l:
            vendor = vendor or "Mikrotik"
        elif "fortigate" in b_l or "fortinet" in b_l:
            vendor = vendor or "Fortinet"
        elif "unifi" in b_l:
            vendor = vendor or "Ubiquiti"
        elif "hikvision" in b_l:
            vendor = vendor or "Hikvision"
        elif "dahua" in b_l:
            vendor = vendor or "Dahua"
        elif "axis" in b_l:
            vendor = vendor or "Axis"

    # ----------------------------------------------------------------------
    # OS detection
    # ----------------------------------------------------------------------

    for b in banners.values():
        b_l = b.lower()
        if "ubuntu" in b_l:
            os = "Linux"
        elif "debian" in b_l:
            os = "Linux"
        elif "centos" in b_l:
            os = "Linux"
        elif "alpine" in b_l:
            os = "Linux"
        elif "windows" in b_l:
            os = "Windows"

    if not os:
        if "microsoft" in sysdescr_l:
            os = "Windows"
        elif "linux" in sysdescr_l:
            os = "Linux"

    # ----------------------------------------------------------------------
    # CLASSIFICATION SCORING ENGINE
    # ----------------------------------------------------------------------

    # ---------------------------
    # SWITCH DETECTION
    # ---------------------------
    if 161 in open_ports and (22 in open_ports or 23 in open_ports):
        _score(scores, "switch", 30)

    # sysDescr patterns
    if any(x in sysdescr_l for x in ["c2960", "c3560", "c9200", "switch", "procurve", "arubaos-switch"]):
        _score(scores, "switch", 40)

    # ---------------------------
    # ROUTER DETECTION
    # ---------------------------
    if any(x in sysdescr_l for x in ["router", "isr", "edgeos", "routeros"]):
        _score(scores, "router", 40)

    if 8291 in open_ports:  # Mikrotik Winbox
        _score(scores, "router", 50)

    # ---------------------------
    # FIREWALL DETECTION
    # ---------------------------
    if any(x in sysdescr_l for x in ["fortigate", "fortios", "asa software", "palo alto"]):
        _score(scores, "firewall", 50)

    if 500 in open_ports and 4500 in open_ports:
        _score(scores, "firewall", 25)

    # ---------------------------
    # ACCESS POINT DETECTION
    # ---------------------------
    if any(x in sysdescr_l for x in ["access point", "unifi ap", "aruba instant", "aironet"]):
        _score(scores, "ap", 60)

    # ---------------------------
    # CAMERA DETECTION
    # ---------------------------
    if 554 in open_ports:  # RTSP
        _score(scores, "camera", 40)

    if any(v in sysdescr_l for v in ["hikvision", "axis", "dahua"]):
        _score(scores, "camera", 40)

    # ---------------------------
    # PRINTER DETECTION
    # ---------------------------
    if 9100 in open_ports:
        _score(scores, "printer", 40)

    if hostname_l.startswith("printer"):
        _score(scores, "printer", 20)

    # ---------------------------
    # SERVER DETECTION
    # ---------------------------
    if 3389 in open_ports:
        _score(scores, "server", 40)  # Windows

    if 22 in open_ports and os == "Linux":
        _score(scores, "server", 40)

    # ---------------------------
    # IOT DETECTION
    # ---------------------------
    if len(open_ports) == 1 and open_ports[0] not in (22, 80, 443):
        _score(scores, "iot", 30)

    if len(open_ports) <= 2 and not sysdescr and not hostname:
        _score(scores, "iot", 10)

    # ----------------------------------------------------------------------
    # FINAL CLASS DECISION
    # ----------------------------------------------------------------------
    if not scores:
        return {
            "class": "Unknown",
            "vendor": vendor,
            "model": model,
            "os": os,
        }

    best_class = max(scores, key=lambda k: scores[k])
    return {
        "class": best_class,
        "vendor": vendor,
        "model": model,
        "os": os,
    }