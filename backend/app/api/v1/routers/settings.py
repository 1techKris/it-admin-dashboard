import httpx
from fastapi import APIRouter, HTTPException
from app.core.config import settings

router = APIRouter(prefix="/settings", tags=["settings"])

@router.post("/teams/test")
async def teams_test():
    if not settings.TEAMS_WEBHOOK_URL:
        raise HTTPException(status_code=400, detail="Teams webhook not configured")
    payload = {
        "@type": "MessageCard", "@context": "http://schema.org/extensions",
        "summary": "Test notification", "themeColor": "0078D7",
        "title": "Test Notification", "text": "Hello from IT Admin Dashboard!"
    }
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(settings.TEAMS_WEBHOOK_URL, json=payload)
        r.raise_for_status()
    return {"ok": True}
