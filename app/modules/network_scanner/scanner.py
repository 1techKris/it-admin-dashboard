import subprocess
import socket
import fcntl, struct, array
import os
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional, Dict

# OPTIONAL: Only import pysnmp if installed; deep scan will skip SNMP otherwise
try:
    from pysnmp.hlapi import (
        SnmpEngine, CommunityData, UdpTransportTarget, ContextData,
        ObjectType, ObjectIdentity, getCmd
    )
    PYSNMP_AVAILABLE = True
except Exception:
    PYSNMP_AVAILABLE = False

# ---------- Ping ----------
def ping(ip: str) -> bool:
    result = subprocess.run(
        ["ping", "-c", "1", "-W", "1", ip],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    return result.returncode == 0

# ---------- Reverse DNS ----------
def resolve_hostname(ip: str) -> Optional[str]:
    try:
        return socket.gethostbyaddr(ip)[0]
    except Exception:
        return None

# ---------- Port scan (extendable) ----------
COMMON_PORTS = [
    22,   # SSH
    80,   # HTTP
    443,  # HTTPS
    3389, # RDP
    445,  # SMB
    139,  # NetBIOS
    9100, # RAW printing (JetDirect)
    515,  # LPD
    161,  # SNMP
]

def scan_ports(ip: str) -> List[int]:
    open_ports = []
    for port in COMMON_PORTS:
        s = socket.socket()
        s.settimeout(0.25)
        try:
            s.connect((ip, port))
            open_ports.append(port)
        except Exception:
            pass
        finally:
            s.close()
    return open_ports

# ---------- OS Guess ----------
def guess_os(hostname: Optional[str], open_ports: List[int]) -> Optional[str]:
    if 3389 in open_ports or 445 in open_ports:
        return "Windows (guess)"
    if 22 in open_ports and 445 not in open_ports:
        return "Linux/Unix (guess)"
    if hostname and ("printer" in hostname.lower() or "hp" in hostname.lower() or "xerox" in hostname.lower()):
        return "Printer (guess)"
    return None

# ---------- SNMP Printer probe ----------
# Returns (is_printer, model_string) if SNMP available and looks like printer
def probe_snmp_printer(ip: str, community: str = "public") -> (bool, Optional[str]):
    if not PYSNMP_AVAILABLE:
        return (False, None)
    try:
        # sysDescr (basic info)
        iterator = getCmd(
            SnmpEngine(),
            CommunityData(community, mpModel=0),
            UdpTransportTarget((ip, 161), timeout=0.5, retries=1),
            ContextData(),
            ObjectType(ObjectIdentity('1.3.6.1.2.1.1.1.0')) # sysDescr.0
        )
        errorIndication, errorStatus, errorIndex, varBinds = next(iterator)
        if errorIndication or errorStatus:
            return (False, None)
        descr = str(varBinds[0][1]).lower()
        # Heuristics: many printers mention hp, epson, kyocera, lexmark, canon, brother, xerox etc.
        if any(x in descr for x in ["printer", "hp", "xerox", "kyocera", "lexmark", "canon", "brother", "ricoh", "epson"]):
            return (True, str(varBinds[0][1]))
        return (False, None)
    except Exception:
        return (False, None)

# ---------- Host type detection ----------
def detect_host_type(hostname: Optional[str], open_ports: List[int]) -> str:
    # SNMP + JetDirect + LPD strongly suggests a printer
    if 9100 in open_ports or 515 in open_ports or 161 in open_ports:
        return "printer"
    if 3389 in open_ports or 445 in open_ports:
        return "server"
    if 22 in open_ports and 80 not in open_ports and 3389 not in open_ports and 445 not in open_ports:
        return "server"  # likely Linux
    # Could extend to detect switches/routers by ports 22/23/80 and no SMB/RDP
    return "unknown"

# ---------- MAC vendor: requires ARP table inspection (best effort) ----------
def get_mac_from_arp(ip: str) -> Optional[str]:
    # Parse /proc/net/arp (Linux) to get MAC if present
    try:
        with open("/proc/net/arp", "r") as f:
            lines = f.read().strip().splitlines()[1:]
        for line in lines:
            parts = line.split()
            if parts[0] == ip and parts[3] != "00:00:00:00:00:00":
                return parts[3].lower()
    except Exception:
        return None
    return None

def mac_to_vendor(mac: Optional[str]) -> Optional[str]:
    if not mac or len(mac) < 8:
        return None
    # A tiny static mapping for common vendors (extendable or replace with local OUI file)
    oui = mac[:8].upper()
    VENDORS = {
        "00:1A:4B": "Hewlett Packard",
        "00:1B:78": "Hewlett Packard",
        "00:80:77": "Lexmark",
        "00:1F:29": "Kyocera",
        "00:00:0C": "Cisco",
        "00:1C:BF": "Dell",
        "F4:4E:05": "Microsoft",
    }
    return VENDORS.get(oui, None)

# ---------- Single IP scan (deep) ----------
def scan_ip(ip: str, snmp_community: str = "public") -> Optional[Dict]:
    if not ping(ip):
        return None

    hostname = resolve_hostname(ip)
    ports = scan_ports(ip)

    # SNMP probe for printers (optional)
    is_printer, printer_info = probe_snmp_printer(ip, snmp_community)
    os_guess_val = guess_os(hostname, ports) or ("Printer (SNMP)" if is_printer else None)

    mac = get_mac_from_arp(ip)
    vendor = mac_to_vendor(mac)

    host_type = "printer" if is_printer else detect_host_type(hostname, ports)

    return {
        "ip": ip,
        "hostname": hostname,
        "ports": ports,
        "vendor": vendor,
        "os_guess": os_guess_val,
        "host_type": host_type,
    }

# ---------- Subnet scanner ----------
def scan_subnet(subnet_ips: List[str], snmp_community: str = "public") -> List[Dict]:
    results = []
    with ThreadPoolExecutor(max_workers=64) as pool:
        for result in pool.map(lambda ip: scan_ip(ip, snmp_community), subnet_ips):
            if result:
                results.append(result)
    return results

# ---------- Auto-detect local subnet (best effort) ----------
def get_default_cidr_fallback() -> str:
    # Simple fallback
    return "192.168.1.0/24"

def detect_local_cidr() -> str:
    # Best effort: parse ip route to find default interface and CIDR
    try:
        route = subprocess.check_output(["ip", "-o", "route", "show", "to", "default"]).decode()
        parts = route.strip().split()
        dev_index = parts.index("dev") + 1
        iface = parts[dev_index]
        addr = subprocess.check_output(["ip", "-o", "-f", "inet", "addr", "show", iface]).decode()
        # pick first inet line
        for line in addr.splitlines():
            if " inet " in line:
                # line like: "2: eth0    inet 192.168.125.50/24 brd ..."
                tokens = line.strip().split()
                cidr = tokens[tokens.index("inet")+1]
                network_prefix = cidr.split('/')[1]
                ip_only = cidr.split('/')[0]
                # compute network by simple mask conversion
                # but we will just return ip/mask; router will expand hosts via ipaddress
                return f"{ip_only}/{network_prefix}"
    except Exception:
        pass
    return get_default_cidr_fallback()