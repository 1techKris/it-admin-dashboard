from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Any, Dict

from app.switchmgr.services.driver_resolver import driver_for_switch
from app.models.device import Device
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_session

router = APIRouter(prefix="/switch", tags=["switch"])


# ----------------------------------------------------------
# Utility: detect vendor using sysDescr/sysName
# ----------------------------------------------------------

async def detect_vendor_and_driver(ip: str):
    """
    SNMP query sysDescr/sysName using a temporary Cisco/Hp/Dell guess.
    Since sysDescr always exists, use a generic session approach.
    """

    # temporary generic session
    from easysnmp import Session

    try:
        sess = Session(
            hostname=ip,
            community="public",
            version=2,
            timeout=2,
            retries=1,
        )
        descr = sess.get("1.3.6.1.2.1.1.1.0")
        sysdescr = descr.value if descr else ""
    except Exception:
        sysdescr = ""

    if not sysdescr:
        raise HTTPException(400, f"Switch at {ip} unreachable via SNMP.")

    driver_class = driver_for_switch(sysdescr)
    if not driver_class:
        raise HTTPException(400, f"No driver found for vendor: '{sysdescr}'")

    return driver_class(ip=ip)


# ----------------------------------------------------------
# Pydantic Response Models
# ----------------------------------------------------------

class SwitchBasic(BaseModel):
    vendor: str
    model: str
    sys_descr: str
    sys_name: str


# ----------------------------------------------------------
# /switch/{ip}
# ----------------------------------------------------------

@router.get("/{ip}", response_model=SwitchBasic)
async def get_switch_basic(ip: str):
    driver = await detect_vendor_and_driver(ip)
    status = await driver.get_status()
    return SwitchBasic(**status)


# ----------------------------------------------------------
# /switch/{ip}/interfaces
# ----------------------------------------------------------

@router.get("/{ip}/interfaces")
async def get_switch_interfaces(ip: str):
    driver = await detect_vendor_and_driver(ip)
    return {"interfaces": await driver.get_interfaces()}


# ----------------------------------------------------------
# /switch/{ip}/neighbors   (LLDP + CDP)
# ----------------------------------------------------------

@router.get("/{ip}/neighbors")
async def get_switch_neighbors(ip: str):
    driver = await detect_vendor_and_driver(ip)
    lldp = await driver.get_lldp_neighbors()

    # Not all drivers implement get_cdp_neighbors
    cdp = []
    if hasattr(driver, "get_cdp_neighbors"):
        try:
            cdp = await driver.get_cdp_neighbors()
        except Exception:
            cdp = []

    return {
        "lldp": lldp,
        "cdp": cdp,
    }


# ----------------------------------------------------------
# /switch/{ip}/vlans
# ----------------------------------------------------------

@router.get("/{ip}/vlans")
async def get_switch_vlans(ip: str):
    driver = await detect_vendor_and_driver(ip)
    vlans = await driver.get_vlans()
    return {"vlans": vlans}


# ----------------------------------------------------------
# /switch/{ip}/mac-table
# ----------------------------------------------------------

@router.get("/{ip}/mac-table")
async def get_switch_mac_table(ip: str):
    driver = await detect_vendor_and_driver(ip)
    table = await driver.get_mac_table()
    return {"mac_table": table}


# ----------------------------------------------------------
# /switch/{ip}/all  (Unified Snapshot)
# ----------------------------------------------------------

@router.get("/{ip}/all")
async def get_switch_full_snapshot(ip: str):
    driver = await detect_vendor_and_driver(ip)

    basic = await driver.get_status()
    interfaces = await driver.get_interfaces()
    vlans = await driver.get_vlans()
    lldp = await driver.get_lldp_neighbors()

    # CDP optional
    cdp = []
    if hasattr(driver, "get_cdp_neighbors"):
        try:
            cdp = await driver.get_cdp_neighbors()
        except Exception:
            pass

    mac = await driver.get_mac_table()

    return {
        "status": basic,
        "interfaces": interfaces,
        "vlans": vlans,
        "neighbors": {
            "lldp": lldp,
            "cdp": cdp,
        },
        "mac_table": mac,
    }