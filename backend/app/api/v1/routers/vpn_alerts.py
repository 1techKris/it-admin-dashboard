from fastapi import APIRouter
from app.db.vpn_history_db import SessionLocal
from app.models.vpn_alert_rule import VPNAlertRule

router = APIRouter(prefix="/vpn/alerts", tags=["vpn-alerts"])

@router.get("/rules")
async def list_rules():
    db = SessionLocal()
    try:
        return db.query(VPNAlertRule).all()
    finally:
        db.close()

@router.post("/rules/add")
async def add_rule(username: str):
    db = SessionLocal()
    try:
        r = VPNAlertRule(username=username.lower(), enabled=True)
        db.add(r)
        db.commit()
        return {"ok": True}
    finally:
        db.close()

@router.post("/rules/remove")
async def remove_rule(username: str):
    db = SessionLocal()
    try:
        row = db.query(VPNAlertRule).filter(VPNAlertRule.username == username.lower()).first()
        if row:
            db.delete(row)
            db.commit()
        return {"ok": True}
    finally:
        db.close()