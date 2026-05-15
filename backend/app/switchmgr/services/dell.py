import asyncio
import logging
from easysnmp import Session

logger = logging.getLogger(__name__)


class DellSwitchDriver:
    """
    Full Dell (DNOS6, DNOS9, OS10) SNMP-based switch driver.

    Supports:
    - sysDescr, sysName
    - Interface list (IF-MIB)
    - Admin / Oper state
    - VLAN table (Q-BRIDGE-MIB)
    - LLDP neighbors (LLDP-MIB)
    - MAC address table (BRIDGE-MIB)

    This is compatible with:
    - Dell N-series (DNOS6)
    - Dell S-series (DNOS9)
    - OS10 (Enterprise)
    """

    def __init__(self, ip: str, community: str = "public", timeout: int = 2, retries: int = 1):
        self.ip = ip
        self.community = community
        self.timeout = timeout
        self.retries = retries

    # -------------------------------------------------------------
    # Internal SNMP wrapper
    # -------------------------------------------------------------

    def _snmp(self, oid: str, walk=False):
        """Internal SNMP helper with safety."""
        try:
            s = Session(
                hostname=self.ip,
                community=self.community,
                version=2,
                timeout=self.timeout,
                retries=self.retries,
            )
            if walk:
                return s.walk(oid)
            else:
                v = s.get(oid)
                return v.value if v else None
        except Exception as e:
            logger.warning(f"Dell SNMP error {self.ip}: {e}")
            return None

    # -------------------------------------------------------------
    # Switch INFO
    # -------------------------------------------------------------

    async def get_status(self):
        return {
            "vendor": "Dell",
            "model": await self.get_model(),
            "sys_descr": await self.get_sysdescr(),
            "sys_name": await self.get_sysname(),
        }

    async def get_sysdescr(self):
        return await asyncio.to_thread(self._snmp, "1.3.6.1.2.1.1.1.0")

    async def get_sysname(self):
        return await asyncio.to_thread(self._snmp, "1.3.6.1.2.1.1.5.0")

    async def get_model(self):
        descr = await self.get_sysdescr()
        if not descr:
            return "Unknown"
        parts = descr.split()
        if "Dell" in parts:
            try:
                idx = parts.index("Dell")
                return parts[idx + 1]
            except Exception:
                return descr
        return descr

    # -------------------------------------------------------------
    # Interfaces (IF-MIB)
    # -------------------------------------------------------------

    async def get_interfaces(self):
        """
        Returns port list, with:
        - index
        - name
        - admin status
        - oper status
        """

        names = await asyncio.to_thread(self._snmp, "1.3.6.1.2.1.31.1.1.1.1", True)
        admins = await asyncio.to_thread(self._snmp, "1.3.6.1.2.1.2.2.1.7", True)
        opers = await asyncio.to_thread(self._snmp, "1.3.6.1.2.1.2.2.1.8", True)

        if not names or not admins or not opers:
            return []

        interfaces = []
        for n, a, o in zip(names, admins, opers):
            try:
                idx = int(n.oid_index)
                interfaces.append({
                    "index": idx,
                    "name": n.value,
                    "admin_status": int(a.value),
                    "oper_status": int(o.value),
                })
            except Exception:
                continue

        return interfaces

    # -------------------------------------------------------------
    # LLDP Neighbors
    # -------------------------------------------------------------

    async def get_lldp_neighbors(self):
        """
        Returns LLDP neighbors for Dell.
        """

        # LLDP remote system name
        names = await asyncio.to_thread(self._snmp, "1.0.8802.1.1.2.1.4.1.1.9", True)
        # LLDP remote port description
        ports = await asyncio.to_thread(self._snmp, "1.0.8802.1.1.2.1.4.1.1.8", True)

        if not names or not ports:
            return []

        neighbors = []
        for nn, pp in zip(names, ports):
            try:
                local_port = nn.oid_index.split(".")[1]
                neighbors.append({
                    "local_port": local_port,
                    "remote_name": nn.value,
                    "remote_port": pp.value,
                })
            except Exception:
                continue

        return neighbors

    # -------------------------------------------------------------
    # VLANs (Q-BRIDGE-MIB)
    # -------------------------------------------------------------

    async def get_vlans(self):
        """Returns VLAN ID -> name mapping."""

        vlan_names = await asyncio.to_thread(self._snmp, "1.3.6.1.2.1.17.7.1.4.3.1.1", True)
        if not vlan_names:
            return {}

        vlans = {}
        for v in vlan_names:
            try:
                vid = int(v.oid_index)
                vlans[vid] = v.value
            except Exception:
                continue

        return vlans

    # -------------------------------------------------------------
    # MAC Address Table (BRIDGE-MIB)
    # -------------------------------------------------------------

    async def get_mac_table(self):
        """
        Returns MAC table:
        [
            { mac, port }
        ]
        """

        macs = await asyncio.to_thread(self._snmp, "1.3.6.1.2.1.17.4.3.1.1", True)
        ports = await asyncio.to_thread(self._snmp, "1.3.6.1.2.1.17.4.3.1.2", True)

        if not macs or not ports:
            return []

        table = []
        for m, p in zip(macs, ports):
            try:
                mac_bytes = m.value
                mac_hex = "".join(f"{ord(c):02x}" for c in mac_bytes)
                table.append({
                    "mac": mac_hex,
                    "port": int(p.value),
                })
            except Exception:
                continue

        return table