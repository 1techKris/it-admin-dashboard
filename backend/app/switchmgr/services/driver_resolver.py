import logging

# Import all drivers
from .cisco import CiscoSwitchDriver
from .hp import HPSwitchDriver
from .dell import DellSwitchDriver

logger = logging.getLogger(__name__)

"""
This resolver selects the correct switch driver based on:
- Vendor strings returned by sysDescr / sysName
- Manual vendor mappings
- Substring matching

It is designed to work with scanner_service and switchmgr API.
"""


# ----------------------------------------------------------------------
# DRIVER MAP
# ----------------------------------------------------------------------

DRIVERS = {
    # Cisco
    "cisco": CiscoSwitchDriver,
    "cat": CiscoSwitchDriver,
    "ios": CiscoSwitchDriver,
    "ios-xe": CiscoSwitchDriver,
    "catalyst": CiscoSwitchDriver,
    "nexus": CiscoSwitchDriver,

    # HP / HPE / Aruba / ProCurve
    "hp": HPSwitchDriver,
    "hpe": HPSwitchDriver,
    "aruba": HPSwitchDriver,
    "procurve": HPSwitchDriver,
    "2530": HPSwitchDriver,    # common HP model numbers
    "2540": HPSwitchDriver,
    "2920": HPSwitchDriver,

    # Dell
    "dell": DellSwitchDriver,
    "n-series": DellSwitchDriver,
    "nseries": DellSwitchDriver,
    "os10": DellSwitchDriver,
    "dnos": DellSwitchDriver,
    "dnos6": DellSwitchDriver,
    "dnos9": DellSwitchDriver,
}


# ----------------------------------------------------------------------
# RESOLVER LOGIC
# ----------------------------------------------------------------------

def driver_for_switch(vendor_string: str):
    """
    Given a vendor or sysDescr string, return the correct driver class.

    Example:
        vendor_string = "Cisco IOS Software C2960X"
        driver = driver_for_switch(vendor_string)
        inst = driver(ip="10.0.0.5", community="public")

    Returns None if no driver matches.
    """

    if not vendor_string:
        logger.warning("Switch driver resolver: vendor string is empty.")
        return None

    vendor = vendor_string.lower()

    # Exact and substring matching
    for key, driver in DRIVERS.items():
        if key in vendor:
            logger.info(f"Resolved switch vendor '{vendor_string}' → {driver.__name__}")
            return driver

    logger.warning(
        f"driver_for_switch: No matching driver found for vendor string '{vendor_string}'."
    )
    return None