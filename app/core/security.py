from fastapi import APIRouter, Request, Form, HTTPException, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.modules.admin.models import DashboardUser
from app.core.passwords import verify_password

templates = Jinja2Templates(directory="app/templates")
router = APIRouter()


# -----------------------------
# DB session helper
# -----------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# -----------------------------
# Get role for logged-in user
# -----------------------------
def get_role_for(username: str):
    db = SessionLocal()
    try:
        user = (
            db.query(DashboardUser)
            .filter(DashboardUser.username == username)
            .first()
        )
        return user.role if user else None
    finally:
        db.close()


# -----------------------------
# Require login
# -----------------------------
def require_login(request: Request):
    user = request.cookies.get("user")
    if not user:
        raise HTTPException(status_code=401)
    return user


# -----------------------------
# Require specific role
# -----------------------------
def require_role(role: str):
    def checker(
        request: Request,
        user: str = Depends(require_login),
        db: Session = Depends(get_db)
    ):
        record = (
            db.query(DashboardUser)
            .filter(DashboardUser.username == user)
            .first()
        )
        if not record:
            raise HTTPException(status_code=401)

        if record.role != role:
            raise HTTPException(status_code=403, detail="Insufficient permissions")

        return user

    return checker


# -----------------------------
# LOGIN PAGE
# -----------------------------
@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if request.cookies.get("user"):
        return RedirectResponse("/", status_code=303)

    return templates.TemplateResponse("login.html", {"request": request})


# -----------------------------
# LOGIN SUBMIT
# -----------------------------
@router.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    if request.cookies.get("user"):
        return RedirectResponse("/", status_code=303)

    user = (
        db.query(DashboardUser)
        .filter(DashboardUser.username == username)
        .first()
    )

    if user and verify_password(password, user.password_hash):
        response = RedirectResponse("/", status_code=303)
        response.set_cookie("user", username, httponly=True)
        return response

    return templates.TemplateResponse(
        "login.html",
        {"request": request, "error": "Invalid username or password"},
    )


# -----------------------------
# LOGOUT
# -----------------------------
@router.get("/logout")
async def logout():
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie("user")
    return response