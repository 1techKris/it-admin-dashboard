# app/modules/active_directory/routers.py

from fastapi import APIRouter, Depends, Form, Query
from fastapi.responses import JSONResponse
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from app.core.security import require_login  # adjust if your project stores this elsewhere

# AD client (NTLM, domain-wide scope, full logging)
from app.modules.active_directory.ad_client import ADClient, ADConfig

router = APIRouter(prefix="/ad", tags=["Active Directory"])


# --------------------------
# Helpers
# --------------------------
def _winfiletime_to_iso(winfiletime: Optional[int]) -> Optional[str]:
    """
    Convert Windows FILETIME (100-nanosecond intervals since Jan 1, 1601 UTC)
    to ISO-8601 string. Returns None if zero/invalid.
    AD time properties often use this: lastLogonTimestamp, badPasswordTime, etc.
    """
    if not winfiletime:
        return None
    try:
        # Many AD props are 0 when unset
        if int(winfiletime) == 0:
            return None
        # FILETIME -> Unix epoch
        EPOCH_DIFF_100NS = 116444736000000000  # 1601->1970 offset in 100ns
        ts_ms = (int(winfiletime) - EPOCH_DIFF_100NS) / 10_000
        dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
        return dt.isoformat()
    except Exception:
        return None


def _entry_attr(entry, name: str, default=None):
    try:
        v = entry[name].value
        return v if v is not None else default
    except Exception:
        return default


def _serialize_user_entry(entry) -> Dict[str, Any]:
    """
    Produce the shape your UI expects:
      - SamAccountName, Name, EmailAddress, Enabled, LockedOut, DistinguishedName
    """
    # Enabled/locked are derived; simplest pass-through with None fallback
    # Enabled often requires UAC bit logic; if your client sets it, you can trust it.
    return {
        "SamAccountName": _entry_attr(entry, "sAMAccountName"),
        "Name": _entry_attr(entry, "name"),
        "EmailAddress": _entry_attr(entry, "mail"),
        "Enabled": None,  # optional to fill from computed UAC bit (client could expose)
        "LockedOut": None,  # optional to fill from lockout properties
        "DistinguishedName": _entry_attr(entry, "distinguishedName"),
    }


def _serialize_ou_entry(entry) -> Dict[str, Any]:
    name = _entry_attr(entry, "ou") or _entry_attr(entry, "name")
    return {
        "Name": name,
        "DistinguishedName": _entry_attr(entry, "distinguishedName"),
    }


# --------------------------
# Users
# --------------------------
@router.get("/users")
async def ad_users(query: Optional[str] = Query(None), user=Depends(require_login)):
    """
    GET /ad/users?query=smith
    Returns an array of user summaries for the UI list.
    """
    try:
        ad = ADClient()
        if query:
            entries = ad.search_users(query, size_limit=500)
        else:
            # domain-wide, return some reasonable default set of users
            entries = ad._search(ad.cfg.base_dn, "(&(objectCategory=Person)(objectClass=User))", size_limit=200)

        return JSONResponse([_serialize_user_entry(e) for e in entries])
    except Exception as e:
        return JSONResponse({"error": f"{e}"}, status_code=500)


@router.get("/users/locked")
async def ad_users_locked(user=Depends(require_login)):
    """
    GET /ad/users/locked
    Return users that appear locked out (heuristic using lockoutTime>0).
    """
    try:
        ad = ADClient()
        conn = ad._ensure_conn()
        # Heuristic: lockoutTime >= 1 means locked at some point.
        # You may prefer msDS-User-Account-Control-Computed bit checks in your environment.
        ok = conn.search(
            ad.cfg.base_dn,
            "(&(objectCategory=Person)(objectClass=User)(lockoutTime>=1))",
            attributes=["sAMAccountName", "name", "distinguishedName"]
        )
        if not ok:
            return JSONResponse({"error": str(conn.result)}, status_code=500)
        data = []
        for e in conn.entries:
            data.append({
                "SamAccountName": _entry_attr(e, "sAMAccountName"),
                "Name": _entry_attr(e, "name"),
                "DistinguishedName": _entry_attr(e, "distinguishedName")
            })
        return JSONResponse(data)
    except Exception as e:
        return JSONResponse({"error": f"{e}"}, status_code=500)


@router.get("/user/logoninfo")
async def ad_user_logoninfo(dn: str = Query(...), user=Depends(require_login)):
    """
    GET /ad/user/logoninfo?dn=...
    Returns { LastLogonDate, LastBadPasswordAttempt } in ISO-8601 for your UI.
    """
    try:
        ad = ADClient()
        conn = ad._ensure_conn()
        ok = conn.search(
            dn,
            "(objectClass=*)",
            attributes=["lastLogonTimestamp", "badPasswordTime"]
        )
        if not ok or not conn.entries:
            return JSONResponse({"error": str(conn.result) if ok else "Not found"}, status_code=404)

        e = conn.entries[0]
        last_logon_iso = _winfiletime_to_iso(_entry_attr(e, "lastLogonTimestamp"))
        last_bad_iso = _winfiletime_to_iso(_entry_attr(e, "badPasswordTime"))

        return JSONResponse({
            "LastLogonDate": last_logon_iso,
            "LastBadPasswordAttempt": last_bad_iso
        })
    except Exception as e:
        return JSONResponse({"error": f"{e}"}, status_code=500)


# --------------------------
# Groups for a user (by SAM)
# --------------------------
@router.get("/user/groups")
async def ad_user_groups(sam: str = Query(...), user=Depends(require_login)):
    """
    GET /ad/user/groups?sam=j.smith
    Return an array of { Name } for groups where user is a direct member.
    """
    try:
        ad = ADClient()
        # Resolve user DN by sAMAccountName
        ures = ad._search(ad.cfg.base_dn, f"(&(objectCategory=Person)(objectClass=User)(sAMAccountName={ad._escape(sam)}))", size_limit=1)
        if not ures:
            return JSONResponse([])

        user_dn = _entry_attr(ures[0], "distinguishedName")
        conn = ad._ensure_conn()
        ok = conn.search(
            ad.cfg.base_dn,
            f"(&(objectClass=group)(member={ad._escape(user_dn)}))",
            attributes=["cn", "name"]
        )
        if not ok:
            return JSONResponse({"error": str(conn.result)}, status_code=500)

        data = []
        for e in conn.entries:
            name = _entry_attr(e, "cn") or _entry_attr(e, "name")
            data.append({"Name": name})
        return JSONResponse(data)
    except Exception as e:
        return JSONResponse({"error": f"{e}"}, status_code=500)


@router.post("/user/groups/add")
async def ad_user_groups_add(
    sam: str = Form(...),
    group: str = Form(...),
    user=Depends(require_login)
):
    """
    POST /ad/user/groups/add  (sam, group)
    Adds user to group. Group may be CN or sAMAccountName.
    """
    try:
        ad = ADClient()
        # Find user DN
        ures = ad._search(ad.cfg.base_dn, f"(&(objectCategory=Person)(objectClass=User)(sAMAccountName={ad._escape(sam)}))", size_limit=1)
        if not ures:
            return JSONResponse({"error": "User not found"}, status_code=404)
        user_dn = _entry_attr(ures[0], "distinguishedName")

        # Find group DN by CN or sAMAccountName
        gres = ad._search(ad.cfg.base_dn, f"(&(objectClass=group)(|(cn={ad._escape(group)})(sAMAccountName={ad._escape(group)})))", size_limit=1)
        if not gres:
            return JSONResponse({"error": "Group not found"}, status_code=404)
        group_dn = _entry_attr(gres[0], "distinguishedName")

        ok = ad.add_user_to_group(user_dn, group_dn)
        if not ok:
            return JSONResponse({"error": "Failed to add to group"}, status_code=500)
        return JSONResponse({"ok": True})
    except Exception as e:
        return JSONResponse({"error": f"{e}"}, status_code=500)


@router.post("/user/groups/remove")
async def ad_user_groups_remove(
    sam: str = Form(...),
    group: str = Form(...),
    user=Depends(require_login)
):
    """
    POST /ad/user/groups/remove  (sam, group)
    Removes user from group.
    """
    try:
        ad = ADClient()
        # Find user DN
        ures = ad._search(ad.cfg.base_dn, f"(&(objectCategory=Person)(objectClass=User)(sAMAccountName={ad._escape(sam)}))", size_limit=1)
        if not ures:
            return JSONResponse({"error": "User not found"}, status_code=404)
        user_dn = _entry_attr(ures[0], "distinguishedName")

        # Find group DN by CN or sAMAccountName
        gres = ad._search(ad.cfg.base_dn, f"(&(objectClass=group)(|(cn={ad._escape(group)})(sAMAccountName={ad._escape(group)})))", size_limit=1)
        if not gres:
            return JSONResponse({"error": "Group not found"}, status_code=404)
        group_dn = _entry_attr(gres[0], "distinguishedName")

        ok = ad.remove_user_from_group(user_dn, group_dn)
        if not ok:
            return JSONResponse({"error": "Failed to remove from group"}, status_code=500)
        return JSONResponse({"ok": True})
    except Exception as e:
        return JSONResponse({"error": f"{e}"}, status_code=500)


# --------------------------
# Move user
# --------------------------
@router.post("/user/move")
async def ad_user_move(
    dn: str = Form(...),
    ou: str = Form(...),
    user=Depends(require_login)
):
    """
    POST /ad/user/move (dn, ou)
    Moves user to the specified OU DN.
    """
    try:
        ad = ADClient()
        ok = ad.move_user(dn, ou)
        if not ok:
            return JSONResponse({"error": "Move failed"}, status_code=500)
        return JSONResponse({"ok": True})
    except Exception as e:
        return JSONResponse({"error": f"{e}"}, status_code=500)


# --------------------------
# Reset password
# --------------------------
@router.post("/user/reset-password")
async def ad_user_reset_password(
    dn: str = Form(...),
    password: str = Form(...),
    user=Depends(require_login)
):
    """
    POST /ad/user/reset-password (dn, password)
    """
    try:
        ad = ADClient()
        ok = ad.reset_password(dn, password, force_change_next_logon=False)
        if not ok:
            return JSONResponse({"error": "Reset failed"}, status_code=500)
        return JSONResponse({"ok": True})
    except Exception as e:
        return JSONResponse({"error": f"{e}"}, status_code=500)


# --------------------------
# Enable / Disable
# --------------------------
@router.post("/user/enable")
async def ad_user_enable(dn: str = Form(...), user=Depends(require_login)):
    try:
        ad = ADClient()
        ok = ad.set_user_enabled(dn, True)
        if not ok:
            return JSONResponse({"error": "Enable failed"}, status_code=500)
        return JSONResponse({"ok": True})
    except Exception as e:
        return JSONResponse({"error": f"{e}"}, status_code=500)


@router.post("/user/disable")
async def ad_user_disable(dn: str = Form(...), user=Depends(require_login)):
    try:
        ad = ADClient()
        ok = ad.set_user_enabled(dn, False)
        if not ok:
            return JSONResponse({"error": "Disable failed"}, status_code=500)
        return JSONResponse({"ok": True})
    except Exception as e:
        return JSONResponse({"error": f"{e}"}, status_code=500)


# --------------------------
# Delete user
# --------------------------
@router.post("/user/delete")
async def ad_user_delete(dn: str = Form(...), user=Depends(require_login)):
    """
    POST /ad/user/delete (dn)
    """
    try:
        ad = ADClient()
        conn = ad._ensure_conn()
        ok = conn.delete(dn)
        if not ok:
            return JSONResponse({"error": str(conn.result)}, status_code=500)
        return JSONResponse({"ok": True})
    except Exception as e:
        return JSONResponse({"error": f"{e}"}, status_code=500)


# --------------------------
# OU listing & create
# --------------------------
@router.get("/ou")
async def ad_ou_list(user=Depends(require_login)):
    """
    GET /ad/ou
    Return OUs for OU picker (move/create user flows).
    """
    try:
        ad = ADClient()
        entries = ad.list_ous()
        return JSONResponse([_serialize_ou_entry(e) for e in entries])
    except Exception as e:
        return JSONResponse({"error": f"{e}"}, status_code=500)


@router.post("/ou/create")
async def ad_ou_create(
    name: str = Form(...),
    path: str = Form(...),
    user=Depends(require_login)
):
    """
    POST /ad/ou/create (name, path)
    Creates an OU at:  OU=<name>,<path>
    """
    try:
        ad = ADClient()
        conn = ad._ensure_conn()
        dn = f"OU={name},{path}"
        ok = conn.add(dn, ["top", "organizationalUnit"], {"ou": name})
        if not ok:
            return JSONResponse({"error": str(conn.result)}, status_code=500)
        return JSONResponse({"ok": True, "dn": dn})
    except Exception as e:
        return JSONResponse({"error": f"{e}"}, status_code=500)