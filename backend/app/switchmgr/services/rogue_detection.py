ENTERPRISE_VENDORS = {
    "cisco", "aruba", "hp", "hewlett", "dell", "fortinet", "ubiquiti", "juniper"
}

async def detect_rogue_switches(graph):
    rogue = []

    for n in graph.get("nodes", []):
        vendor = (n.get("vendor") or "").lower()

        if vendor and any(ev in vendor for ev in ENTERPRISE_VENDORS):
            continue  # trusted

        # Unknown vendor → rogue
        rogue.append({
            "device": n["id"],
            "vendor": n.get("vendor"),
            "reason": "Unknown or unapproved vendor"
        })

    return rogue