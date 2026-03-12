from fastapi import APIRouter, Form, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from app.core.database import SessionLocal
from app.modules.servers.models import set_setting, get_setting
from app.core.security import require_login

router = APIRouter(tags=["Settings"])

@router.get("/settings/ad", response_class=HTMLResponse)
async def settings_ad_page(request, user=Depends(require_login)):
    db = SessionLocal()
    settings = {
        "ad_domain": get_setting(db, "ad_domain"),
        "ad_dc_host": get_setting(db, "ad_dc_host"),
        "ad_dc_ip": get_setting(db, "ad_dc_ip"),
        "ad_base_dn": get_setting(db, "ad_base_dn"),
        "ad_default_user_ou": get_setting(db, "ad_default_user_ou"),
        "ad_username": get_setting(db, "ad_username"),
        "ad_password": get_setting(db, "ad_password"),
    }
    return request.state.templates.TemplateResponse("settings/ad.html", {"request": request, "settings": settings})


@router.post("/settings/ad", response_class=HTMLResponse)
async def settings_ad_save(
    ad_domain: str = Form(...),
    ad_dc_host: str = Form(...),
    ad_dc_ip: str = Form(None),
    ad_base_dn: str = Form(...),
    ad_default_user_ou: str = Form(...),
    ad_username: str = Form(...),
    ad_password: str = Form(...),
    user=Depends(require_login),
):
    db = SessionLocal()
    set_setting(db, "ad_domain", ad_domain)
    set_setting(db, "ad_dc_host", ad_dc_host)
    set_setting(db, "ad_dc_ip", ad_dc_ip)
    set_setting(db, "ad_base_dn", ad_base_dn)
    set_setting(db, "ad_default_user_ou", ad_default_user_ou)
    set_setting(db, "ad_username", ad_username)
    set_setting(db, "ad_password", ad_password)

    return "<div class='text-green-400 text-sm'>Settings saved.</div>"