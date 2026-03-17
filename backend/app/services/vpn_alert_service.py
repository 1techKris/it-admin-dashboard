# backend/app/services/vpn_alert_service.py

from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.vpn_alert_rule import VPNAlertRule
from datetime import datetime

_active_alerted_users = set()


async def check_vpn_alerts(active_sessions: list):
    async with AsyncSessionLocal() as db:
        # Load enabled alert rules
        result = await db.execute(
            select(VPNAlertRule).where(VPNAlertRule.enabled == True)
        )
        rules = result.scalars().all()

        rule_users = {r.username.lower(): r for r in rules}
        alerts = []

        # Evaluate rules
        for s in active_sessions:
            user = s.get("Username") or ""
            if not user:
                continue

            u = user.lower()

            if u in rule_users and u not in _active_alerted_users:
                alerts.append({
                    "type": "vpn_alert",
                    "username": user,
                    "timestamp": datetime.utcnow().isoformat()
                })
                _active_alerted_users.add(u)

        # Remove users no longer connected
        active_usernames = {s.get("Username", "").lower() for s in active_sessions}
        _active_alerted_users.intersection_update(active_usernames)

        return alerts