async def stp_mismatch(graph):
    issues = []
    stp = graph.get("stp", {})

    for ip, info in stp.items():
        root = info.get("root_bridge")
        rp = info.get("root_port")

        if not root:
            issues.append({
                "device": ip,
                "issue": "No STP root detected",
            })
        if rp == "0":
            issues.append({
                "device": ip,
                "issue": "Switch thinks it is root (check config)",
            })

    return issues


async def lacp_mismatch(graph):
    # Very basic placeholder — real implementation requires LACP-MIB polling
    issues = []
    for link in graph.get("links", []):
        if link["type"] == "cdp" and link["local_port"] == link["remote_port"]:
            issues.append({
                "devices": f"{link['source']} ↔ {link['target']}",
                "issue": "Suspicious identical port on both sides — possible mismatch",
            })
    return issues