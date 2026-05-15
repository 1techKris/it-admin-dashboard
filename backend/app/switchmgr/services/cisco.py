import asyncio
import logging
from easysnmp import Session

logger = logging.getLogger(__name__)


class CiscoSwitchDriver:
    """
    Full Cisco SNMP-based switch driver.

    Supports:
    - sysDescr, sysName
    - Admin/Oper status (IF-MIB)
    - LLDP neighbors (LLDP-MIB)
    - Cisco Discovery Protocol (CDP-MIB)
    - VLAN list (Q-BRIDGE-MIB)
    - MAC address table (BRIDGE-MIB)

    Compatible with:
    - Cisco Catalyst IOS
    - Cisco Catalyst IOS-XE
    - Cisco Nexus (partial)
    """

    def __init__(self, ip: str, community: str = "public", timeout: int = 2, retries: int = 1):
        self.ip = ip
        self.community = community
        self.timeout = timeout
        self.retries = retries

    # ============================================================
    # SNMP Helper
    # ============================================================

    def _snmp(self, oid: str, walk=False):
        try:
            session = Session(
                hostname=self.ip,
                community=self.community,
                version=2,
                timeout=self.timeout,
                retries=self.retries,
            )
            if walk:
                return session.walk(oid)
            else:
                v = session.get(oid)
                return v.value if v else None
        except Exception as e:
            logger.warning(f"Cisco SNMP error {self.ip}: {e}")
            return None

    # ============================================================
    # Basic Switch Information
    # ============================================================

    async def get_sysdescr(self):
        return await asyncio.to_thread(self._snmp, "1.3.6.1.2.1.1.1.0")

    async def get_sysname(self):
        return await asyncio.to_thread(self._snmp, "1.3.6.1.2.1.1.5.0")

    async def get_model(self):
        descr = await self.get_sysdescr()
        if not descr:
            return "Unknown"
        # Cisco banners are usually: "Cisco IOS Software ... C2960X ..."
        for token in descr.split():
            if token.upper().startswith("C") and any(c.isdigit() for c in token):
                return token
        return descr

    async def get_status(self):
        return {
            "vendor": "Cisco",
            "model": await self.get_model(),
            "sys_descr": await self.get_sysdescr(),
            "sys_name": await self.get_sysname(),
        }

    # ============================================================
    # Interfaces (IF-MIB)
    # ============================================================

    async def get_interfaces(self):
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
            except:
                pass

        return interfaces

    # ============================================================
    # LLDP Neighbors (LLDP-MIB)
    # ============================================================

    async def get_lldp_neighbors(self):
        # lldpRemSysName
        names = await asyncio.to_thread(self._snmp, "1.0.8802.1.1.2.1.4.1.1.9", True)
        # lldpRemPortDesc
        ports = await asyncio.to_thread(self._snmp, "1.0.8802.1.1.2.1.4.1.1.8", True)

        if not names or not ports:
            return []

        neighbors = []
        for n, p in zip(names, ports):
            try:
                parts = n.oid_index.split(".")
                local_port = parts[1] if len(parts) > 1 else "?"

                neighbors.append({
                    "local_port": local_port,
                    "remote_name": n.value,
                    "remote_port": p.value,
                })
            except:
                pass

        return neighbors

    # ============================================================
    # CDP Neighbors (Cisco Discovery Protocol)
    # ============================================================

    async def get_cdp_neighbors(self):
        """
        Cisco proprietary neighbor discovery.
        OIDs:
        - cdpCacheDeviceId     1.3.6.1.4.1.9.9.23.1.2.1.1.6
        - cdpCacheDevicePort   1.3.6.1.4.1.9.9.23.1.2.1.1.7
        """

        dev_ids = await asyncio.to_thread(self._snmp, "1.3.6.1.4.1.9.9.23.1.2.1.1.6", True)
        dev_ports = await asyncio.to_thread(self._snmp, "1.3.6.1.4.1.9.9.23.1.2.1.1.7", True)

        if not dev_ids or not dev_ports:
            return []

        neighbors = []
        for d, p in zip(dev_ids, dev_ports):
            try:
                idx_parts = d.oid_index.split(".")
                local_port = idx_parts[1] if len(idx_parts) > 1 else "?"

                neighbors.append({
                    "local_port": local_port,
                    "remote_name": d.value,
                    "remote_port": p.value,
                })
            except:
                pass

        return neighbors

    # ============================================================
    # VLAN Table (Q-BRIDGE-MIB)
    # ============================================================

    async def get_vlans(self):
        vlan_names = await asyncio.to_thread(self._snmp, "1.3.6.1.2.1.17.7.1.4.3.1.1", True)

        vlans = {}
        if not vlan_names:
            return vlans

        for v in vlan_names:
            try:
                vid = int(v.oid_index)
                vlans[vid] = v.value
            except:
                pass

        return vlans

    # ============================================================
    # MAC Address Table (BRIDGE-MIB)
    # ============================================================

    async def get_mac_table(self):
        macs = await asyncio.to_thread(self._snmp, "1.3.6.1.2.1.17.4.3.1.1", True)
        ports = await asyncio.to_thread(self._snmp, "1.3.6.1.2.1.17.4.3.1.2", True)

        table = []
        if not macs or not ports:
            return table

        for m, p in zip(macs, ports):
            try:
                mac_bytes = m.value
                mac_hex = "".join(f"{ord(c):02x}" for c in mac_bytes)
                table.append({
                    "mac": mac_hex,
                    "port": int(p.value),
                })
            except:
                pass

        return table