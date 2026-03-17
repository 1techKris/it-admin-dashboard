from fastapi import APIRouter, HTTPException
import asyncio
import subprocess
import platform

router = APIRouter(prefix="/servers", tags=["server-actions"])

def is_windows():
    return platform.system().lower().startswith("win")

@router.post("/{device_id}/actions/reboot")
async def reboot(device_id: str):
    # Replace with WMI/SSH later
    print(f"Rebooting {device_id}")
    return {"ok": True}

@router.post("/{device_id}/actions/shutdown")
async def shutdown(device_id: str):
    print(f"Shutdown {device_id}")
    return {"ok": True}

@router.post("/{device_id}/actions/run-update")
async def run_update(device_id: str):
    print(f"Updating {device_id}")
    return {"ok": True}