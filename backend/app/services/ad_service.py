# backend/app/services/ad_service.py

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from ldap3 import (
    Server,
    Connection,
    ALL,
    SUBTREE,
    ALL_ATTRIBUTES,
    ALL_OPERATIONAL_ATTRIBUTES,
    MODIFY_REPLACE,
)

from app.services import ad_config


# ----------------------------
# Helpers: server + time utils
# ----------------------------

def _normalize_server(raw: str) -> str:
    """
    ldap3.Server() requires a clean hostname/IP, not a URI.
    - Strips ldap:// or ldaps:// prefixes
    - Lowercases the hostname (DNS is case-insensitive; ldap3/socket can be picky)
    - Trims whitespace and trailing slashes
    """
    if not raw:
        return ""
    s = raw.strip()
    lower = s.lower()
    if lower.startswith("ldap://"):
        s = s[7:]
    elif lower.startswith("ldaps://"):
        s = s[8:]
    s = s.strip().strip("/")
    return s.lower()


def _filetime_to_iso(ft: Optional[str]) -> Optional[str]:
    """
    Convert AD Windows FILETIME (int) to ISO timestamp.
    Returns None on invalid/missing.
    """
    try:
        v = int(ft)
        if v <= 0:
            return None
        epoch_start = datetime(1601, 1, 1, tzinfo=timezone.utc)
        dt = epoch_start + timedelta(microseconds=v / 10)
        return dt.isoformat()
    except Exception:
        return None


def _dn_to_ou(dn: str) -> str:
    """
    Extract OU path from a DN (e.g., OU=Sales/OU=Users)
    """
    parts = [p for p in (dn or "").split(",") if p.startswith("OU=")]
    return "/".join(p.split("=", 1)[1] for p in parts) if parts else ""


def _uac_disabled(uac: Any) -> bool:
    """
    Check if userAccountControl has ACCOUNTDISABLE (2) bit set.
    """
    try:
        return (int(uac) & 2) == 2
    except Exception:
        return False


def _conn() -> Connection:
    """
    Create and return a bound ldap3.Connection using the current cached AD settings.
    Applies normalization to the server string so ldap3 gets a clean host.
    """
    cfg = ad_config.get_ad_config()

    server_raw = (cfg.get("server") or "").strip()
    server_clean = _normalize_server(server_raw)
    if not server_clean:
        raise Exception(f"Invalid AD server: '{server_raw}'")

    use_ssl = bool(cfg.get("use_ssl", False))
    user = cfg.get("user")
    password = cfg.get("password")

    srv = Server(server_clean, use_ssl=use_ssl, get_info=ALL)
    conn = Connection(srv, user=user, password=password, auto_bind=True)
    return conn


# ----------------------------
# Users
# ----------------------------

def search_users(
    q: str,
    enabled: Optional[bool],
    locked: Optional[bool],
    page: int,
    page_size: int,
) -> List[Dict[str, Any]]:
    """
    Return a page of users. Filters:
      - q: search displayName/sAMAccountName/userPrincipalName (contains)
      - enabled: True/False/None
      - locked: (soft default; many domains hide lockoutTime to non-admin binds)
    """
    c = _conn()
    base = ad_config.get_ad_config().get("base_dn") or ""

    filt = "(&(objectCategory=person)(objectClass=user)(!(objectClass=computer)))"

    if enabled is True:
        filt = f"(&{filt}(!userAccountControl:1.2.840.113556.1.4.803:=2))"
    elif enabled is False:
        filt = f"(&{filt}(userAccountControl:1.2.840.113556.1.4.803:=2))"

    if q:
        text = q.replace("*", r"\2a")
        filt = f"(&{filt}(|(displayName=*{text}*)(sAMAccountName=*{text}*)(userPrincipalName=*{text}*)))"

    c.extend.standard.paged_search(
        search_base=base,
        search_filter=filt,
        search_scope=SUBTREE,
        attributes=[ALL_ATTRIBUTES, ALL_OPERATIONAL_ATTRIBUTES],
        paged_size=max(50, min(2000, int(ad_config.get_ad_config().get("page_size", 200)))),
        generator=False,
    )

    entries = [e for e in c.response if e.get("type") == "searchResEntry"]

    start = max(0, (int(page) - 1) * int(page_size))
    end = start + int(page_size)
    entries = entries[start:end]

    rows: List[Dict[str, Any]] = []
    for e in entries:
        attrs = e.get("attributes", {}) or {}
        uac = attrs.get("userAccountControl")
        dn = e.get("dn") or ""
        display_name = attrs.get("displayName")
        cn = attrs.get("cn")
        name = display_name or cn

        rows.append(
            {
                "dn": dn,
                "name": name,
                "sam": attrs.get("sAMAccountName"),
                "upn": attrs.get("userPrincipalName"),
                "enabled": not _uac_disabled(uac),
                "locked": False,
                "ou": _dn_to_ou(dn),
                "lastLogon": _filetime_to_iso(attrs.get("lastLogonTimestamp")),
                "mail": attrs.get("mail"),
            }
        )

    c.unbind()
    return rows


# ----------------------------
# Groups
# ----------------------------

def search_groups(q: str, page: int, page_size: int) -> List[Dict[str, Any]]:
    c = _conn()
    base = ad_config.get_ad_config().get("base_dn") or ""

    filt = "(&(objectCategory=group)(objectClass=group))"
    if q:
        text = q.replace("*", r"\2a")
        filt = f"(&{filt}(|(cn=*{text}*)(name=*{text}*)))"

    c.extend.standard.paged_search(
        search_base=base,
        search_filter=filt,
        search_scope=SUBTREE,
        attributes=[ALL_ATTRIBUTES],
        paged_size=max(50, min(2000, int(ad_config.get_ad_config().get("page_size", 200)))),
        generator=False,
    )

    entries = [e for e in c.response if e.get("type") == "searchResEntry"]
    start = max(0, (int(page) - 1) * int(page_size))
    end = start + int(page_size)
    entries = entries[start:end]

    rows = []
    for e in entries:
        attrs = e.get("attributes", {}) or {}
        rows.append(
            {
                "dn": e.get("dn"),
                "name": attrs.get("cn"),
                "description": attrs.get("description"),
                "members": attrs.get("member") or [],
            }
        )

    c.unbind()
    return rows


def group_members(group_dn: str) -> List[Dict[str, Any]]:
    c = _conn()
    rows: List[Dict[str, Any]] = []

    if c.search(group_dn, "(objectClass=*)", attributes=["member"]) and c.entries:
        try:
            mem_dns = c.entries[0]["member"].values  # type: ignore[index]
        except Exception:
            mem_dns = []
        for mdn in mem_dns:
            if c.search(mdn, "(objectClass=*)", attributes=["displayName", "sAMAccountName", "objectClass"]):
                ent = c.entries[0]
                try:
                    classes = {x.lower() for x in ent["objectClass"].values}  # type: ignore[index]
                except Exception:
                    classes = set()

                if "group" in classes:
                    otype = "group"
                elif "computer" in classes:
                    otype = "computer"
                elif "user" in classes:
                    otype = "user"
                else:
                    otype = "object"

                display = None
                try:
                    display = ent["displayName"].value  # type: ignore[index]
                except Exception:
                    pass

                sam = None
                try:
                    sam = ent["sAMAccountName"].value  # type: ignore[index]
                except Exception:
                    pass

                rows.append(
                    {
                        "dn": mdn,
                        "name": display or sam or mdn,
                        "sam": sam,
                        "type": otype,
                    }
                )

    c.unbind()
    return rows


def add_group_member(group_dn: str, member_dn: str) -> bool:
    c = _conn()
    try:
        ok = c.modify(group_dn, {"member": [(c.MODIFY_ADD if hasattr(c, "MODIFY_ADD") else 0, [member_dn])]})
        if not ok:
            ok = c.modify(group_dn, {"member": [(MODIFY_REPLACE, [member_dn])]})
        return ok
    finally:
        c.unbind()


def remove_group_member(group_dn: str, member_dn: str) -> bool:
    c = _conn()
    try:
        ok = c.modify(group_dn, {"member": [(c.MODIFY_DELETE if hasattr(c, "MODIFY_DELETE") else 2, [member_dn])]})
        return ok
    finally:
        c.unbind()


# ----------------------------
# Computers
# ----------------------------

def search_computers(q: str, page: int, page_size: int) -> List[Dict[str, Any]]:
    c = _conn()
    base = ad_config.get_ad_config().get("base_dn") or ""

    filt = "(&(objectCategory=computer)(objectClass=computer))"
    if q:
        text = q.replace("*", r"\2a")
        filt = f"(&{filt}(|(cn=*{text}*)(name=*{text}*)))"

    c.extend.standard.paged_search(
        search_base=base,
        search_filter=filt,
        search_scope=SUBTREE,
        attributes=[ALL_ATTRIBUTES, ALL_OPERATIONAL_ATTRIBUTES],
        paged_size=max(50, min(2000, int(ad_config.get_ad_config().get("page_size", 200)))),
        generator=False,
    )

    entries = [e for e in c.response if e.get("type") == "searchResEntry"]
    start = max(0, (int(page) - 1) * int(page_size))
    end = start + int(page_size)
    entries = entries[start:end]

    rows = []
    for e in entries:
        a = e.get("attributes", {}) or {}
        rows.append(
            {
                "dn": e.get("dn"),
                "name": a.get("cn"),
                "os": a.get("operatingSystem"),
                "osVersion": a.get("operatingSystemVersion"),
                "lastLogon": _filetime_to_iso(a.get("lastLogonTimestamp")),
                "ou": _dn_to_ou(e.get("dn") or ""),
                "enabled": not _uac_disabled(a.get("userAccountControl")),
            }
        )

    c.unbind()
    return rows


# ----------------------------
# User actions
# ----------------------------

def user_reset_password(user_dn: str, new_password: str, must_change_at_next_logon: bool) -> bool:
    quoted = f'"{new_password}"'.encode("utf-16-le")
    c = _conn()
    try:
        ok = c.extend.microsoft.modify_password(user_dn, new_password=quoted, old_password=None)
        if ok and must_change_at_next_logon:
            c.modify(user_dn, {"pwdLastSet": [(MODIFY_REPLACE, [0])]})
        return ok
    finally:
        c.unbind()


def user_disable(user_dn: str) -> bool:
    c = _conn()
    try:
        if not c.search(user_dn, "(objectClass=user)", attributes=["userAccountControl"]):
            return False
        if not c.entries:
            return False
        uac = int(c.entries[0]["userAccountControl"].value)  # type: ignore[index]
        new_uac = uac | 2
        ok = c.modify(user_dn, {"userAccountControl": [(MODIFY_REPLACE, [new_uac])]})
        return ok
    finally:
        c.unbind()


def user_enable(user_dn: str) -> bool:
    c = _conn()
    try:
        if not c.search(user_dn, "(objectClass=user)", attributes=["userAccountControl"]):
            return False
        if not c.entries:
            return False
        uac = int(c.entries[0]["userAccountControl"].value)  # type: ignore[index]
        new_uac = uac & ~2
        ok = c.modify(user_dn, {"userAccountControl": [(MODIFY_REPLACE, [new_uac])]})
        return ok
    finally:
        c.unbind()


def user_unlock(user_dn: str) -> bool:
    c = _conn()
    try:
        ok = c.modify(user_dn, {"lockoutTime": [(MODIFY_REPLACE, [0])]})
        return ok
    finally:
        c.unbind()


def user_move(user_dn: str, target_ou_dn: str) -> bool:
    c = _conn()
    try:
        cn = user_dn.split(",")[0]
        ok = c.modify_dn(user_dn, cn, new_superior=target_ou_dn)
        return ok
    finally:
        c.unbind()