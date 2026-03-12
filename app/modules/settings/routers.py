# app/modules/settings/routers.py

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.security import require_login, get_role_for

# Reuse get_setting/set_setting from servers model
from app.modules.servers.models import get_setting, set_setting

# AD client for test
from app.modules.active_directory.ad_client import ADClient

templates = Jinja2Templates(directory="app/templates")
router = APIRouter()


# ---------------------------
# DB dependency
# ---------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------
# GET: /settings
# ---------------------------
@router.get("/", response_class=HTMLResponse)
async def settings_page(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_login),
):
    # Optional admin gate
    try:
        if get_role_for(user) != "admin":
            return HTMLResponse("<div class='p-4 text-red-400'>Access denied.</div>", status_code=403)
    except Exception:
        # If you don't use roles, ignore
        pass

    context = {
        "request": request,
        "title": "Settings",

        # WMI
        "wmi_username": get_setting(db, "wmi_username"),
        "wmi_password": get_setting(db, "wmi_password"),

        # AD
        "ad_domain": get_setting(db, "ad_domain"),
        "ad_dc_host": get_setting(db, "ad_dc_host"),
        "ad_dc_ip": get_setting(db, "ad_dc_ip"),
        "ad_base_dn": get_setting(db, "ad_base_dn"),
        "ad_default_user_ou": get_setting(db, "ad_default_user_ou"),
        "ad_username": get_setting(db, "ad_username"),
        "ad_password": get_setting(db, "ad_password"),
    }

    return templates.TemplateResponse("admin/settings.html", context)


# ---------------------------
# POST: /settings/wmi
# ---------------------------
@router.post("/wmi", response_class=HTMLResponse)
async def save_wmi_settings(
    username: str = Form(""),
    password: str = Form(""),
    db: Session = Depends(get_db),
    user=Depends(require_login),
):
    try:
        if get_role_for(user) != "admin":
            return HTMLResponse("<div class='text-red-400'>Access denied.</div>", status_code=403)
    except Exception:
        pass

    set_setting(db, "wmi_username", username)
    set_setting(db, "wmi_password", password)

    return HTMLResponse("<div class='text-green-400'>WMI settings saved.</div>")


# ---------------------------
# POST: /settings/ad
# ---------------------------
@router.post("/ad", response_class=HTMLResponse)
async def save_ad_settings(
    ad_domain: str = Form(...),
    ad_dc_host: str = Form(...),
    ad_dc_ip: str = Form(""),
    ad_base_dn: str = Form(...),
    ad_default_user_ou: str = Form(...),
    ad_username: str = Form(...),
    ad_password: str = Form(...),
    db: Session = Depends(get_db),
    user=Depends(require_login),
):
    try:
        if get_role_for(user) != "admin":
            return HTMLResponse("<div class='text-red-400'>Access denied.</div>", status_code=403)
    except Exception:
        pass

    set_setting(db, "ad_domain", ad_domain.strip())
    set_setting(db, "ad_dc_host", ad_dc_host.strip())
    set_setting(db, "ad_dc_ip", (ad_dc_ip or "").strip())
    set_setting(db, "ad_base_dn", ad_base_dn.strip())
    set_setting(db, "ad_default_user_ou", ad_default_user_ou.strip())
    set_setting(db, "ad_username", ad_username.strip())
    set_setting(db, "ad_password", ad_password)

    return HTMLResponse("<div class='text-green-400'>AD settings saved.</div>")


# ---------------------------
# POST: /settings/ad/test
# ---------------------------
@router.post("/ad/test")
async def test_ad_connection(
    db: Session = Depends(get_db),
    user=Depends(require_login),
):
    try:
        if get_role_for(user) != "admin":
            return JSONResponse({"error": "Access denied"}, status_code=403)
    except Exception:
        pass

    try:
        # Optionally pass db to ADClient to reuse the same session
        ad = ADClient(db=db)
        ad.connect()
        return JSONResponse({"ok": True, "message": "AD connection successful!"})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
