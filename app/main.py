from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse

from app.core.security import router as auth_router, require_login, get_role_for
from app.core.database import Base, engine

from app.modules.printers.routers import router as printers_router
from app.modules.servers.routers import router as servers_router
from app.modules.active_directory.routers import router as ad_router
from app.modules.admin.routers import router as admin_router
from app.modules.network_scanner.routers import router as network_router
from app.modules.servers.monitor import start_server_monitor
from app.modules.dashboard.routers import router as dashboard_router


app = FastAPI(title="IT Admin Dashboard")

templates = Jinja2Templates(directory="app/templates")

# ---------------------------
# ROUTERS
# ---------------------------
# Dashboard MUST come first to own "/"
app.include_router(dashboard_router, prefix="", tags=["Dashboard"])
app.include_router(auth_router)
app.include_router(printers_router, prefix="/printers", tags=["Printers"])
app.include_router(servers_router, prefix="/servers", tags=["Servers"])
app.include_router(ad_router, prefix="/ad", tags=["Active Directory"])
app.include_router(admin_router, prefix="/admin", tags=["Admin"])
app.include_router(network_router, prefix="/network", tags=["Network"])

# ---------------------------
# STARTUP
# ---------------------------
@app.on_event("startup")
def init_db():
    Base.metadata.create_all(bind=engine)
    start_server_monitor()

# ---------------------------
# 401 Redirect to login
# ---------------------------
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code == 401:
        return RedirectResponse("/login", status_code=303)
    raise exc