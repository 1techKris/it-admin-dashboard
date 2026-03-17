# backend/app/services/ad_ou_tree.py

from __future__ import annotations
from typing import Dict, Any, Optional
from ldap3 import SUBTREE
from app.services.ad_service import _conn
from app.services import ad_config


def _domain_name_from_base_dn(base_dn: str) -> str:
    parts = []
    for seg in (base_dn or "").split(","):
        seg = seg.strip()
        if seg.upper().startswith("DC="):
            parts.append(seg[3:])
    return ".".join(parts) if parts else base_dn


def _parent_dn(dn: str) -> str:
    return ",".join(dn.split(",")[1:]) if "," in dn else ""


def build_ou_tree(base_dn: Optional[str] = None) -> Dict[str, Any]:
    """
    Build nested OU tree with users assigned to the deepest matching OU.
    Returns a guaranteed root node for the domain, even if there are no OUs.
    """
    cfg = ad_config.get_ad_config()
    base = (base_dn or cfg.get("base_dn") or "").strip()
    if not base:
        raise ValueError("Base DN is empty")

    c = _conn()

    # Fetch OUs
    c.search(
        search_base=base,
        search_filter="(objectClass=organizationalUnit)",
        search_scope=SUBTREE,
        attributes=["ou"]
    )
    ou_entries = c.entries[:]

    # Fetch users (person user, not computer)
    c.search(
        search_base=base,
        search_filter="(&(objectCategory=person)(objectClass=user)(!(objectClass=computer)))",
        search_scope=SUBTREE,
        attributes=["displayName", "sAMAccountName", "distinguishedName"]
    )
    user_entries = c.entries[:]

    c.unbind()

    # Initialize root
    nodes: Dict[str, Dict[str, Any]] = {}
    root_name = _domain_name_from_base_dn(base)
    nodes[base] = {
        "type": "ou",
        "name": root_name,
        "dn": base,
        "users": [],
        "children": []
    }

    # OU nodes
    for ou in ou_entries:
        try:
            dn = ou.entry_dn
            try:
                name = ou.ou.value
            except Exception:
                first = dn.split(",", 1)[0]  # OU=Name,...
                name = first.split("=", 1)[1] if "=" in first else dn

            nodes[dn] = {
                "type": "ou",
                "name": name,
                "dn": dn,
                "users": [],
                "children": []
            }
        except Exception:
            continue

    # Link OU nodes to parents (bubble to root if needed)
    for dn, node in list(nodes.items()):
        if dn == base:
            continue
        parent = _parent_dn(dn)
        while parent and parent not in nodes:
            parent = _parent_dn(parent)
        parent_dn = parent if parent in nodes else base
        nodes[parent_dn]["children"].append(node)

    # Assign users to deepest OU suffix; otherwise attach to root
    for u in user_entries:
        try:
            user_dn = u.entry_dn
            display = None
            sam = None
            try:
                display = u.displayName.value
            except Exception:
                pass
            try:
                sam = u.sAMAccountName.value
            except Exception:
                pass
            name = display or sam or user_dn

            best_parent = None
            best_len = -1
            for ou_dn in nodes.keys():
                if user_dn.lower().endswith(ou_dn.lower()) and len(ou_dn) > best_len:
                    best_len = len(ou_dn)
                    best_parent = ou_dn

            if best_parent is None:
                best_parent = base

            nodes[best_parent]["users"].append({
                "name": name,
                "sam": sam or "",
                "dn": user_dn,
            })
        except Exception:
            continue

    return nodes[base]


# Optional minimal tree for diagnostics (top-level OUs only)
def build_ou_tree_min(base_dn: Optional[str] = None) -> Dict[str, Any]:
    cfg = ad_config.get_ad_config()
    base = (base_dn or cfg.get("base_dn") or "").strip()
    if not base:
        raise ValueError("Base DN is empty")

    c = _conn()
    c.search(
        search_base=base,
        search_filter="(objectClass=organizationalUnit)",
        search_scope=SUBTREE,
        attributes=["ou", "distinguishedName"]
    )
    ou_entries = c.entries[:]
    c.unbind()

    root_name = _domain_name_from_base_dn(base)
    out = {
        "type": "ou",
        "name": root_name,
        "dn": base,
        "users": [],
        "children": []
    }

    for ou in ou_entries:
        try:
            dn = ou.entry_dn
            try:
                name = ou.ou.value
            except Exception:
                first = dn.split(",", 1)[0]
                name = first.split("=", 1)[1] if "=" in first else dn

            parent = _parent_dn(dn)
            if parent.lower() == base.lower():
                out["children"].append({
                    "type": "ou",
                    "name": name,
                    "dn": dn,
                    "users": [],
                    "children": []
                })
        except Exception:
            continue

    return out