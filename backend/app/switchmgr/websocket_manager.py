# backend/app/switchmgr/websocket_manager.py

from typing import Dict, Set
from fastapi import WebSocket

# Dictionary of groups → connected websockets
# Example: "switch:10.0.0.2" → {ws1, ws2}
groups: Dict[str, Set[WebSocket]] = {}


async def register(group: str, websocket: WebSocket):
    """Add WebSocket connection to a group."""
    if group not in groups:
        groups[group] = set()
    groups[group].add(websocket)


async def unregister(group: str, websocket: WebSocket):
    """Remove WebSocket from group."""
    if group in groups and websocket in groups[group]:
        groups[group].remove(websocket)


async def broadcast(group: str, payload: dict):
    """Send JSON to all clients in a group."""
    dead = []

    for ws in groups.get(group, []):
        try:
            await ws.send_json(payload)
        except:
            dead.append(ws)

    for ws in dead:
        await unregister(group, ws)