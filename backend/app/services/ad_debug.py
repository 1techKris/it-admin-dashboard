# backend/app/services/ad_debug.py

from __future__ import annotations
import time
import socket
from typing import Dict, Any
from ldap3 import Server, Connection, ALL, SUBTREE

from app.services import ad_config
from app.services.ad_service import _normalize_server


def run_ad_debug() -> Dict[str, Any]:
    cfg = ad_config.get_ad_config()

    raw_server = cfg.get("server", "")
    clean_server = _normalize_server(raw_server)
    user = cfg.get("user")
    pw = cfg.get("password")
    base_dn = cfg.get("base_dn")
    use_ssl = bool(cfg.get("use_ssl"))

    results: Dict[str, Any] = {
        "input_server": raw_server,
        "clean_server": clean_server,
        "server_dns": None,
        "server_reachable": None,
        "bind_ok": False,
        "bind_error": None,
        "sample_user_count": None,
        "latency_ms": None,
        "base_dn": base_dn,
        "use_ssl": use_ssl,
        "user": user,
    }

    # Resolve hostname → IP
    try:
        results["server_dns"] = socket.gethostbyname(clean_server)
        results["server_reachable"] = True
    except Exception as e:
        results["server_dns"] = f"Resolution failed: {e}"
        results["server_reachable"] = False
        return results  # cannot continue

    # LDAP bind
    try:
        t0 = time.time()
        srv = Server(clean_server, use_ssl=use_ssl, get_info=ALL)
        conn = Connection(srv, user=user, password=pw, auto_bind=True)
        t1 = time.time()

        results["bind_ok"] = True
        results["latency_ms"] = int((t1 - t0) * 1000)

        # Sample count — quick user search
        conn.search(
            search_base=base_dn,
            search_filter="(&(objectCategory=person)(objectClass=user))",
            search_scope=SUBTREE,
            attributes=["sAMAccountName"],
            size_limit=20,
        )
        results["sample_user_count"] = len(conn.response)
        conn.unbind()

    except Exception as e:
        results["bind_ok"] = False
        results["bind_error"] = str(e)

    return results