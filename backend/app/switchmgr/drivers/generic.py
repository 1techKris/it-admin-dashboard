import asyncio
from easysnmp import Session
from .base import BaseSwitchDriver


def _snmp_get(session, oid):
    """Wrapper for SNMP GET with safety."""
    try:
        item = session.get(oid)
        return item.value if item and item.value else None
    except Exception:
        return None


def _snmp_walk(session, oid):
    """Wrapper for SNMP WALK with safety."""
    try:
        return session.walk(oid)
    except Exception:
        return []


class GenericSwitchDriver(BaseSwitchDriver):
    """
    Generic SNMP switch driver.
    Uses common IF-MIB, Q-BRIDGE-MIB, BRIDGE-MIB, LLDP-MIB.
    """

    async def _session(self):
        """Run SNMP session in executor (non-blocking)."""
        return await asyncio.to_thread(
            lambda: Session(
                hostname=self.ip,
                community=self.community,
                version=2,
                timeout=2,
                retries=1,
            )
        )

    # ------------------------------------------------------------------
    # BASIC INFO
    # ------------------------------------------------------------------
    async def get_basic_info(self):
        session = await self._session()

        sysdescr = await asyncio.to_thread(
            lambda: _snmp_get(session, "1.3.6.1.2.1.1.1.0")
        )
        sysname = await asyncio.to_thread(
            lambda: _snmp_get(session, "1.3.6.1.2.1.1.5.0")
        )

        return {
            "sysDescr": sysdescr,
            "sysName": sysname,
        }

    # ------------------------------------------------------------------
    # PORT LIST
    #
    # ifName            1.3.6.1.2.1.31.1.1.1.1
    # ifAdminStatus     1.3.6.1.2.1.2.2.1.7
    # ifOperStatus      1.3.6.1.2.1.2.2.1.8
    # Q-BRIDGE-MIB VLAN assignment (pvid)
    #   dot1qPvid       1.3.6.1.2.1.17.7.1.4.5.1.1
    # ------------------------------------------------------------------
    async def get_ports(self):
        session = await self._session()

        # Walks
        ifnames = await asyncio.to_thread(
            lambda: _snmp_walk(session, "1.3.6.1.2.1.31.1.1.1.1")
        )
        admin = await asyncio.to_thread(
            lambda: _snmp_walk(session, "1.3.6.1.2.1.2.2.1.7")
        )
        oper = await asyncio.to_thread(
            lambda: _snmp_walk(session, "1.3.6.1.2.1.2.2.1.8")
        )
        vlans = await asyncio.to_thread(
            lambda: _snmp_walk(session, "1.3.6.1.2.1.17.7.1.4.5.1.1")
        )

        result = []

        for i, item in enumerate(ifnames):
            idx = int(item.oid_index)
            name = item.value

            admin_status = (
                int(admin[i].value) if i < len(admin) else None
            )  # 1=up,2=down
            oper_status = (
                int(oper[i].value) if i < len(oper) else None
            )  # 1=up,2=down
            pvid = None

            # VLAN PVID lookup
            for v in vlans:
                if int(v.oid_index) == idx:
                    pvid = int(v.value)
                    break

            result.append(
                {
                    "port": idx,
                    "name": name,
                    "admin_up": admin_status == 1,
                    "oper_up": oper_status == 1,
                    "vlan": pvid,
                }
            )

        return result

    # ------------------------------------------------------------------
    # SET PORT ADMIN STATE
    #
    # ifAdminStatus writable: 1=up, 2=down
    # ------------------------------------------------------------------
    async def set_port_state(self, port: int, enabled: bool):
        session = await self._session()

        def set_state():
            try:
                val = 1 if enabled else 2
                session.set(f"1.3.6.1.2.1.2.2.1.7.{port}", val, "i")
                return True
            except Exception:
                return False

        return await asyncio.to_thread(set_state)

    # ------------------------------------------------------------------
    # SET PORT VLAN (PVID)
    #
    # dot1qPvid is writable on many switches
    # ------------------------------------------------------------------
    async def set_port_vlan(self, port: int, vlan: int):
        session = await self._session()

        def set_vlan():
            try:
                session.set(
                    f"1.3.6.1.2.1.17.7.1.4.5.1.1.{port}", vlan, "i"
                )
                return True
            except Exception:
                return False

        return await asyncio.to_thread(set_vlan)

    # ------------------------------------------------------------------
    # MAC ADDRESS TABLE
    #
    # dot1dTpFdbTable for MACs
    #   dot1dTpFdbAddress   1.3.6.1.2.1.17.4.3.1.1
    #   dot1dTpFdbPort      1.3.6.1.2.1.17.4.3.1.2
    # ------------------------------------------------------------------
    async def get_mac_table(self):
        session = await self._session()

        macs = await asyncio.to_thread(
            lambda: _snmp_walk(session, "1.3.6.1.2.1.17.4.3.1.1")
        )
        ports = await asyncio.to_thread(
            lambda: _snmp_walk(session, "1.3.6.1.2.1.17.4.3.1.2")
        )

        table = []
        for i, item in enumerate(macs):
            mac_hex = ":".join(f"{ord(c):02x}" for c in item.value)
            port = int(ports[i].value) if i < len(ports) else None
            table.append({"mac": mac_hex, "port": port})

        return table

    # ------------------------------------------------------------------
    # LLDP NEIGHBOURS
    #
    # lldpRemTable
    #   lldpRemPortId   1.0.8802.1.1.2.1.4.1.1.7
    #   lldpRemSysName  1.0.8802.1.1.2.1.4.1.1.9
    # ------------------------------------------------------------------
    async def get_lldp_neighbors(self):
        session = await self._session()

        rem_port = await asyncio.to_thread(
            lambda: _snmp_walk(session, "1.0.8802.1.1.2.1.4.1.1.7")
        )
        rem_name = await asyncio.to_thread(
            lambda: _snmp_walk(session, "1.0.8802.1.1.2.1.4.1.1.9")
        )

        neighbors = []
        for i, item in enumerate(rem_port):
            port = item.value
            name = rem_name[i].value if i < len(rem_name) else None
            neighbors.append({"port": port, "neighbor": name})

        return neighbors

    # ------------------------------------------------------------------
    # PoE Control (If supported)
    #
    # Some vendors expose PoE via:
    #   POWER-ETHERNET-MIB
    #   pethPsePortAdminEnable   1.3.6.1.2.1.105.1.1.1.3
    # ------------------------------------------------------------------
    async def set_poe_state(self, port: int, enabled: bool):
        session = await self._session()

        def set_poe():
            try:
                val = 1 if enabled else 2
                session.set(
                    f"1.3.6.1.2.1.105.1.1.1.3.{port}", val, "i"
                )
                return True
            except Exception:
                return False

        return await asyncio.to_thread(set_poe)