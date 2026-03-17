# backend/app/api/v1/routers/ad.py

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_session

# AD services
from app.services import ad_service as ad
from app.services.ad_ou_tree import build_ou_tree, build_ou_tree_min
from app.services import ad_config
from app.services.ad_debug import run_ad_debug


router = APIRouter(prefix="/ad", tags=["active-directory"])


# ----------------------------
# Helpers
# ----------------------------

def str_to_bool(val: Optional[str]) -> Optional[bool]:
    if val is None or val == "":
        return None
    v = val.lower().strip()
    if v == "true":
        return True
    if v == "false":
        return False
    return None


# ----------------------------
# Request bodies
# ----------------------------

class ResetPasswordBody(BaseModel):
    new_password: str
    must_change: bool = True


class MoveUserBody(BaseModel):
    target_ou_dn: str


class GroupMemberBody(BaseModel):
    member_dn: str


# ----------------------------
# Users
# ----------------------------

@router.get("/users")
async def list_users(
    q: Optional[str] = None,
    enabled: Optional[str] = None,
    locked: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
    db: AsyncSession = Depends(get_session),
):
    try:
        enabled_bool = str_to_bool(enabled)
        locked_bool = str_to_bool(locked)

        items = ad.search_users(
            q or "",
            enabled_bool,
            locked_bool,
            page,
            page_size
        )

        return {
            "items": items,
            "page": page,
            "page_size": page_size
        }

    except Exception as e:
        raise HTTPException(500, f"AD error: {e}")


@router.post("/users/{user_dn}/reset-password")
async def reset_password(user_dn: str, body: ResetPasswordBody):
    ok = ad.user_reset_password(user_dn, body.new_password, body.must_change)
    if not ok:
        raise HTTPException(500, "Failed to reset password")
    return {"ok": True}


@router.post("/users/{user_dn}/disable")
async def disable_user(user_dn: str):
    ok = ad.user_disable(user_dn)
    if not ok:
        raise HTTPException(500, "Failed to disable user")
    return {"ok": True}


@router.post("/users/{user_dn}/enable")
async def enable_user(user_dn: str):
    ok = ad.user_enable(user_dn)
    if not ok:
        raise HTTPException(500, "Failed to enable user")
    return {"ok": True}


@router.post("/users/{user_dn}/unlock")
async def unlock_user(user_dn: str):
    ok = ad.user_unlock(user_dn)
    if not ok:
        raise HTTPException(500, "Failed to unlock user")
    return {"ok": True}


@router.post("/users/{user_dn}/move")
async def move_user(user_dn: str, body: MoveUserBody):
    ok = ad.user_move(user_dn, body.target_ou_dn)
    if not ok:
        raise HTTPException(500, "Failed to move user")
    return {"ok": True}


# ----------------------------
# Groups
# ----------------------------

@router.get("/groups")
async def list_groups(
    q: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
):
    try:
        items = ad.search_groups(q or "", page, page_size)
        return {
            "items": items,
            "page": page,
            "page_size": page_size
        }
    except Exception as e:
        raise HTTPException(500, f"AD error: {e}")


@router.get("/groups/{group_dn}/members")
async def list_group_members(group_dn: str):
    try:
        members = ad.group_members(group_dn)
        return {"members": members}
    except Exception as e:
        raise HTTPException(500, f"AD error: {e}")


@router.post("/groups/{group_dn}/members/add")
async def add_group_member(group_dn: str, body: GroupMemberBody):
    if not ad.add_group_member(group_dn, body.member_dn):
        raise HTTPException(500, "Failed to add member")
    return {"ok": True}


@router.post("/groups/{group_dn}/members/remove")
async def remove_group_member(group_dn: str, body: GroupMemberBody):
    if not ad.remove_group_member(group_dn, body.member_dn):
        raise HTTPException(500, "Failed to remove member")
    return {"ok": True}


# ----------------------------
# Computers
# ----------------------------

@router.get("/computers")
async def list_computers(
    q: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
):
    try:
        items = ad.search_computers(q or "", page, page_size)
        return {
            "items": items,
            "page": page,
            "page_size": page_size
        }
    except Exception as e:
        raise HTTPException(500, f"AD error: {e}")


# ----------------------------
# OU Tree (for OU-based browsing)
# ----------------------------

@router.get("/ou-tree")
async def get_ou_tree():
    try:
        base_dn = ad_config.get_ad_config().get("base_dn")
        tree = build_ou_tree(base_dn)
        return tree
    except Exception as e:
        raise HTTPException(500, f"OU tree error: {e}")


@router.get("/ou-tree/min")
async def get_ou_tree_min():
    try:
        base_dn = ad_config.get_ad_config().get("base_dn")
        tree = build_ou_tree_min(base_dn)
        return tree
    except Exception as e:
        raise HTTPException(500, f"OU tree (min) error: {e}")


# ----------------------------
# Debug
# ----------------------------

@router.get("/debug")
async def ad_debug():
    try:
        return run_ad_debug()
    except Exception as e:
        raise HTTPException(500, f"AD Debug error: {e}")