from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import asyncio
import random

router = APIRouter(prefix="/devices/ws", tags=["devices"])

@router.websocket("/{device_id}")
async def device_ws(websocket: WebSocket, device_id: str):
    await websocket.accept()
    t = 0
    try:
        while True:
            # Replace with REAL METRICS later
            payload = {
                "t": t,
                "cpu": random.randint(5, 95),
                "mem": random.randint(20, 90),
                "latency": random.randint(1, 50),
                "alive": True,
            }
            await websocket.send_json(payload)
            t += 1
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        return