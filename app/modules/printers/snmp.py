# app/modules/printers/snmp.py
from typing import Dict, Optional

# ---- Replace the body of snmp_get with your actual SNMP helper ----
def snmp_get(ip: str, oid: str, community: str = "public") -> Optional[int]:
    """
    Return an integer value for the OID or None if not available.
    Plug in your SNMP library (e.g., pysnmp/easysnmp/net-snmp CLI).
    The function should:
      - return int(...) when OID resolves
      - return None on timeout, missing OID, parse error, etc.
    """
    # Example placeholder (to implement properly in your project):
    # return your_snmp_lib.get(ip=ip, community=community, oid=oid)
    return None

def clamp_pct(x: Optional[float]) -> Optional[int]:
    if x is None:
        return None
    try:
        v = round(float(x))
        return max(0, min(100, v))
    except Exception:
        return None

def derive_pct(level: Optional[int], maxcap: Optional[int]) -> Optional[int]:
    if level is None or maxcap is None or maxcap <= 0:
        return None
    return clamp_pct((level / maxcap) * 100.0)

def get_toner_levels(ip: str, community: str = "public") -> Dict[str, Optional[int]]:
    """
    Returns percentage remaining for BK/C/M/Y if present, else None.
    Strategy:
      1) Try direct percent OIDs (common on many HP models).
      2) Fallback to deriving % from level/max capacity via Printer-MIB.
    """
    # --- Direct % OIDs (commonly map 1:BK 2:C 3:M 4:Y) ---
    direct_oids = {
        "BK": "1.3.6.1.2.1.43.11.1.1.9.1.1",
        "C":  "1.3.6.1.2.1.43.11.1.1.9.1.2",
        "M":  "1.3.6.1.2.1.43.11.1.1.9.1.3",
        "Y":  "1.3.6.1.2.1.43.11.1.1.9.1.4",
    }

    res = {"toner_black": None, "toner_cyan": None, "toner_magenta": None, "toner_yellow": None}

    bk = clamp_pct(snmp_get(ip, direct_oids["BK"], community))
    cy = clamp_pct(snmp_get(ip, direct_oids["C"], community))
    mg = clamp_pct(snmp_get(ip, direct_oids["M"], community))
    yl = clamp_pct(snmp_get(ip, direct_oids["Y"], community))

    if any(v is not None for v in (bk, cy, mg, yl)):
        res.update({
            "toner_black": bk,
            "toner_cyan": cy,
            "toner_magenta": mg,
            "toner_yellow": yl,
        })
        return res

    # --- Fallback: derive from level (6) / max cap (8) ---
    # OIDs:
    #   prtMarkerSuppliesLevel        1.3.6.1.2.1.43.11.1.1.6.1.<idx>
    #   prtMarkerSuppliesMaxCapacity  1.3.6.1.2.1.43.11.1.1.8.1.<idx>
    # Common mapping (not guaranteed): 1=BK, 2=C, 3=M, 4=Y
    def pct(idx: int) -> Optional[int]:
        level = snmp_get(ip, f"1.3.6.1.2.1.43.11.1.1.6.1.{idx}", community)
        maxcap = snmp_get(ip, f"1.3.6.1.2.1.43.11.1.1.8.1.{idx}", community)
        return derive_pct(level, maxcap)

    res.update({
        "toner_black": pct(1),
        "toner_cyan": pct(2),
        "toner_magenta": pct(3),
        "toner_yellow": pct(4),
    })
    return res