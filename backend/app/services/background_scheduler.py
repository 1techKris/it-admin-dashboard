# backend/app/services/background_scheduler.py

import asyncio
from app.services.vpn_service import get_vpn_sessions
from app.services.vpn_history_service import record_vpn_sessions
from app.services.vpn_alert_service import check_vpn_alerts

subscribers = []


async def vpn_monitor_loop():
    while True:
        try:
            # 1. Pull current VPN sessions (sync function)
            data = get_vpn_sessions()
            sessions = data.get("connected", [])

            # 2. Write to vpn_history.sqlite3 (sync function, OK)
            record_vpn_sessions(sessions)

            # 3. ALERT CHECK — MUST BE AWAITED (this was the bug)
            alerts = await check_vpn_alerts(sessions)

            # 4. Notify subscribers
            if alerts:
                for cb in subscribers:
                    try:
                        cb(alerts)
                    except:
                        pass

        except Exception as e:
            print(f"[vpn_monitor_loop] ERROR: {e}")

        await asyncio.sleep(60)