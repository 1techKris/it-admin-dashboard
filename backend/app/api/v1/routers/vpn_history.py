from fastapi import APIRouter
from app.db.vpn_history_db import SessionLocal
from app.models.vpn_history import VPNHistory

router = APIRouter(prefix="/vpn/history", tags=["vpn-history"])

@router.get("")
async def get_vpn_history(limit: int = 200):
    db = SessionLocal()
    try:
        rows = (
            db.query(VPNHistory)
            .order_by(VPNHistory.id.desc())
            .limit(limit)
            .all()
        )
        return rows
    finally:
        db.close()