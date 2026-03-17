# backend/app/services/vpn_service.py

import winrm
import json
from datetime import datetime, timezone, timedelta
from app.services.ad_config import get_setting
from app.services.geoip_service import lookup_geoip


def _normalize_endpoint(server: str) -> str:
    s = server.strip()
    if s.startswith("http://") or s.startswith("https://"):
        return s
    return f"http://{s}:5985"


def _parse_windows_date(value):
    """
    Handles /Date(1773642006572)/ timestamps and regular strings.
    Returns ISO UTC string or None.
    """
    if not value:
        return None

    # Handle /Date(xxxxx)/
    if isinstance(value, str) and value.startswith("/Date("):
        try:
            ms = int(value.strip("/Date()").rstrip("/"))
            dt = datetime.fromtimestamp(ms / 1000, tz=timezone.utc)
            return dt.isoformat()
        except Exception:
            return None

    # Try plain ISO
    try:
        return datetime.fromisoformat(value).astimezone(timezone.utc).isoformat()
    except Exception:
        return None


def get_vpn_sessions():
    cfg = get_setting("vpn") or {}
    server = cfg.get("vpn_server")
    user = cfg.get("vpn_user")
    password = cfg.get("vpn_password")

    if not server or not user or not password:
        return {"connected": []}

    endpoint = _normalize_endpoint(server)

    session = winrm.Session(endpoint, auth=(user, password), transport="ntlm")

    ps_script = r"""
    $sessions = Get-RemoteAccessConnectionStatistics |
        Select-Object Username,
                      ClientIPv4Address,
                      ConnectionStartTime,
                      ConnectionDuration,
                      TunnelEndpoint,
                      CallingStationID

    $sessions | ConvertTo-Json -Depth 4
    """

    result = session.run_ps(ps_script)

    if result.status_code != 0:
        return {"connected": []}

    output = result.std_out.decode().strip()
    try:
        data = json.loads(output)
        if isinstance(data, dict):
            data = [data]
    except Exception:
        return {"connected": []}

    normalized = []

    for s in data:
        if not isinstance(s, dict):
            continue

        # --- CLEAN USERNAME ---
        u = s.get("Username")
        if isinstance(u, list):
            u = u[0] if u else None
        if isinstance(u, dict):
            u = None
        if u is not None:
            u = str(u)

        # --- CLEAN IPv4 ---
        ipv4 = None
        raw_ip = s.get("ClientIPv4Address")
        if isinstance(raw_ip, str):
            ipv4 = raw_ip
        elif isinstance(raw_ip, dict):
            ipv4 = raw_ip.get("IPAddressToString")

        # --- Clean Duration ---
        dur = s.get("ConnectionDuration")
        duration = None
        if isinstance(dur, int):
            duration = {"Seconds": dur}
        elif isinstance(dur, dict):
            duration = dur
        else:
            duration = None

        # --- Clean Timestamp ---
        start_time = _parse_windows_date(s.get("ConnectionStartTime"))

        # --- Source IP ---
        from_ip = s.get("TunnelEndpoint") or s.get("CallingStationID")

        # --- GeoIP ---
        geo = lookup_geoip(from_ip) if from_ip else {}

        normalized.append({
            "Username": u,
            "ClientIPv4Address": ipv4,
            "ConnectionStartTime": start_time,
            "ConnectionDuration": duration,
            "ConnectedFrom": from_ip,
            "Geo": geo,
        })

    return {"connected": normalized}


def disconnect_vpn_user(username: str):
    cfg = get_setting("vpn") or {}
    server = cfg.get("vpn_server")
    user = cfg.get("vpn_user")
    password = cfg.get("vpn_password")

    endpoint = _normalize_endpoint(server)
    session = winrm.Session(endpoint, auth=(user, password), transport="ntlm")

    ps = fr"""
    $sessions = Get-RemoteAccessConnectionStatistics |
        Where-Object {{ $_.Username -eq '{username}' }}

    foreach ($s in $sessions) {{
        Disconnect-VpnUser -UserName $s.Username -PassThru
    }}
    """

    result = session.run_ps(ps)
    return result.status_code == 0