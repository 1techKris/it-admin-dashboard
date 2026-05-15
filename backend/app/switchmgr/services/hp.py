import asyncio
import logging
from easysnmp import Session

logger = logging.getLogger(__name__)


class HPSwitchDriver:
    """
    Full HP / HPE / ArubaOS-Switch driver.
    SNMP-Based.

    Supports:
    - sysDescr, sysName
    - Interface list (IF-MIB)
    - Admin/Oper state
    - LLDP neighbors (LLDP-MIB)
    - VLAN names (Q-BRIDGE-MIB)
    - MAC address table (BRIDGE-MIB)
    """

    def __init__(self, ip: str, community: str = "public", timeout: int = 2, retries: int = 1):
        self.ip = ip
        self.community = community
        self.timeout = timeout
        self.retries = retries

    # ---------------------------------------------------------
    # Internal SNMP helper
    # ---------------------------------------------------------

    def _snmp(self, oid: str, walk=False):
        """Internal SNMP wrapper with HP-safe defaults."""
        try:
            sess = Session(
                hostname=self.ip,
                community=self.community,
                version=2,
                timeout=self.timeout,
                retries=self.retries,
            )
            if walk:
                return sess.walk(oid)
            else:
                v = sess.get(oid)
                return v.value if v else None
        except Exception as e:
            logger.warning(f"HP SNMP error {self.ip}: {e}")
            return None

    # ---------------------------------------------------------
    # High-Level API used by your switchmgr UI
    # ---------------------------------------------------------

    async def get_status(self):
        """
        Returns basic switch info.
        """
        return {
            "vendor": "HP",
            "model": await self.get_model(),
            "sys_descr": await self.get_sysdescr(),
            "sys_name": await self.get_sysname(),
        }

    async def get_model(self):
        descr = await self.get_sysdescr()
        if descr:
            # sysDescr usually includes model (e.g. "HP J9776A 2530-24G POE+")
            parts = descr.split()
            return parts[1] if len(parts) > 1 else descr
        return "Unknown"

    async def get_sysdescr(self):
        return await asyncio.to_thread(self._snmp, "1.3.6.1.2.1.1.1.0")

    async def get_sysname(self):
        return await asyncio.to_thread(self._snmp, "1.3.6.1.2.1.1.5.0")

    # ---------------------------------------------------------
    # Interfaces (IF-MIB)
    # ---------------------------------------------------------

    async def get_interfaces(self):
        """
        Returns list of ports with admin/oper state.
        """
        names = await asyncio.to_thread(self._snmp, "1.3.6.1.2.1.31.1.1.1.1", True)
        admin = await asyncio.to_thread(self._snmp, "1.3.6.1.2.1.2.2.1.7", True)
        oper = await asyncio.to_thread(self._snmp, "1.3.6.1.2.1.2.2.1.8", True)

        interfaces = []
        if not names or not admin or not oper:
            return interfaces

        for n, a, o in zip(names, admin, oper):
            try:
                idx = int(n.oid_index)
                interfaces.append({
                    "index": idx,
                    "name": n.value,
                    "admin_status": int(a.value),
                    "oper_status": int(o.value),
                })
            except Exception:
                pass

        return interfaces

    # ---------------------------------------------------------
    # LLDP neighbors (LLDP-MIB)
    # ---------------------------------------------------------

    async def get_lldp_neighbors(self):
        """
        Returns LLDP neighbor table.
        """

        # lldpRemSysName
        names = await asyncio.to_thread(self._snmp, "1.0.8802.1.1.2.1.4.1.1.9", True)
        # lldpRemPortDesc
        ports = await asyncio.to_thread(self._snmp, "1.0.8802.1.1.2.1.4.1.1.8", True)

        neighbors = []
        if not names or not ports:
            return neighbors

        for nn, pp in zip(names, ports):
            try:
                neighbors.append({
                    "local_port": nn.oid_index.split('.')[1],  # rough extraction
                    "remote_name": nn.value,
                    "remote_port": pp.value,
                })
            except Exception:
                pass

        return neighbors

    # ---------------------------------------------------------
    # VLANs (Q-BRIDGE-MIB)
    # ---------------------------------------------------------

    async def get_vlans(self):
        """
        Returns VLAN ID -> Name mapping
        """

        vlan_names = await asyncio.to_thread(self._snmp, "1.3.6.1.2.1.17.7.1.4.3.1.1", True)
        vlans = {}

        if not vlan_names:
            return vlans

        for v in vlan_names:
            try:
                vlan_id = int(v.oid_index)
                vlans[vlan_id] = v.value
            except Exception:
                pass

        return vlans

    # ---------------------------------------------------------
    # MAC Address Table (BRIDGE-MIB)
    # ---------------------------------------------------------

    async def get_mac_table(self):
        """
        Retrieve MAC address table with port mappings.
        Useful for your dashboard port view.
        """

        # learned MAC addresses
        macs = await asyncio.to_thread(self._snmp, "1.3.6.1.2.1.17.4.3.1.1", True)

        # port associated with MAC
        ports = await asyncio.to_thread(self._snmp, "1.3.6.1.2.1.17.4.3.1.2", True)

        results = []
        if not macs or not ports:
            return results

        for m, p in zip(macs, ports):
            try:
                mac_hex = "".join(f"{ord(c):02x}" for c in m.value)
                results.append({
                    "mac": mac_hex,
                    "port": int(p.value),
                })
            except Exception:
                pass

        return results