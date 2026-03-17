from fastapi import APIRouter
from pydantic import BaseModel
from typing import List

router = APIRouter(prefix="/alerts", tags=["alerts"])

class Alert(BaseModel):
    id: str
    severity: str
    source: str
    message: str
    time: str

ALERTS: list[Alert] = [
    Alert(id="AL-000231", severity="Critical", source="FW-01", message="High CPU on firewall", time="09:42"),
    Alert(id="AL-000232", severity="Warning", source="SRV-02", message="Disk space above 85%", time="09:40"),
    Alert(id="AL-000233", severity="Info", source="SRV-01", message="Windows Updates available", time="09:28"),
]

@router.get("", response_model=List[Alert])
async def list_alerts():
    return ALERTS

@router.post("/{alert_id}/ack")
async def ack_alert(alert_id: str):
    global ALERTS
    ALERTS = [a for a in ALERTS if a.id != alert_id]
    return {"ok": True}
