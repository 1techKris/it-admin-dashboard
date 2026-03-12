from fastapi import APIRouter, Depends, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.security import require_role, get_role_for
from app.core.database import SessionLocal
from app.modules.admin.models import DashboardUser
from app.core.passwords import hash_password

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


# ----------------------------
# DB SESSION DEPENDENCY
# ----------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ----------------------------
# LIST USERS (ADMIN ONLY)
# ----------------------------
@router.get("/users", response_class=HTMLResponse)
async def list_users(
    request: Request,
    db: Session = Depends(get_db),
    user: str = Depends(require_role("admin"))
):
    """Display all dashboard users."""
    all_users = db.query(DashboardUser).all()
    role = get_role_for(user)

    return templates.TemplateResponse(
        "admin/users.html",
        {
            "request": request,
            "users": all_users,
            "user": user,
            "role": role,
        }
    )


# ----------------------------
# ADD USER (ADMIN ONLY)
# ----------------------------
@router.post("/users/add")
async def add_user(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    db: Session = Depends(get_db),
    user: str = Depends(require_role("admin"))
):
    """Add a new dashboard user (admin‑only)."""

    hashed = hash_password(password)

    new_user = DashboardUser(
        username=username,
        password_hash=hashed,
        role=role
    )
    db.add(new_user)
    db.commit()

    return RedirectResponse("/admin/users", status_code=303)


# ----------------------------
# PERMISSIONS MATRIX (ADMIN ONLY)
# ----------------------------
@router.get("/permissions", response_class=HTMLResponse)
async def permissions_page(
    request: Request,
    user: str = Depends(require_role("admin"))
):
    """Display static permissions matrix."""
    role = get_role_for(user)

    return templates.TemplateResponse(
        "admin/permissions.html",
        {
            "request": request,
            "user": user,
            "role": role,
        }
    )