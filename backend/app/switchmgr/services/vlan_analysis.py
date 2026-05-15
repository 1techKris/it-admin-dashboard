from easysnmp import Session

async def read_vlan_table(ip: str, community="public"):
    """
    Read VLAN membership using Q-BRIDGE-MIB.
    Returns:
        {
            vlan_id: {
                "untagged": [ifIndex...],
                "tagged": [ifIndex...],
            },
            ...
        }
    """
    try:
        sess = Session(
            hostname=ip,
            community=community,
            version=2,
            timeout=2,
            retries=1,
        )

        # dot1qVlanStaticUntaggedPorts
        untag = sess.walk("1.3.6.1.2.1.17.7.1.4.3.1.4")
        # dot1qVlanStaticEgressPorts
        tag = sess.walk("1.3.6.1.2.1.17.7.1.4.3.1.2")

        vlan_map = {}

        for u in untag:
            vlan = int(u.oid_index)
            vlan_map.setdefault(vlan, {"untagged": [], "tagged": []})
            vlan_map[vlan]["untagged"] = [i for i in u.value]  # raw bitmask

        for t in tag:
            vlan = int(t.oid_index)
            vlan_map.setdefault(vlan, {"untagged": [], "tagged": []})
            vlan_map[vlan]["tagged"] = [i for i in t.value]

        return vlan_map
    except Exception:
        return {}