import asyncio
from easysnmp import Session
from .base import BaseSwitchDriver

def _safe_get(session, oid):
    try:
        item = session.get(oid)
        return item.value if item and item.value else None
    except:
        return None

def _safe_walk(session, oid):
    try:
        return session.walk(oid)
    except:
        return []


class CiscoSwitchDriver(BaseSwitchDriver):
    """
    Cisco SNMP driver — supports Catalyst / Nexus / SMB series.
    """

    async def _session(self):
        return await asyncio.to_thread(
            lambda: Session(
                hostname=self.ip,
                community=self.community,
                version=2,
                timeout=2,
                retries=1
            )
        )

    # ---------------------------------------------------------------
    # BASIC INFO
    # ---------------------------------------------------------------
    async def get_basic_info(self):
        s = await self._session()

        sysdescr = await asyncio.to_thread(
            lambda: _safe_get(s, "1.3.6.1.2.1.1.1.0")
        )
        sysname = await asyncio.to_thread(
            lambda: _safe_get(s, "1.3.6.1.2.1.1.5.0")
        )

        # Cisco OS version from CISCO-PRODUCTS-MIB if available
        os_ver = None
        try:
            ver = _safe_walk(s, "1.3.6.1.4.1.9.2.1.73")  # ciscoFlashMisc
            if ver and len(ver):
                os_ver = ver[0].value
        except:
            pass

        return {
            "sysDescr": sysdescr,
            "sysName": sysname,
            "osVersion": os_ver,
        }

    # ---------------------------------------------------------------
    # PORT LIST
    # ---------------------------------------------------------------
    async def get_ports(self):
        s = await self._session()

        ifnames = await asyncio.to_thread(lambda: _safe_walk(s, "1.3.6.1.2.1.31.1.1.1.1"))
        admin = await asyncio.to_thread(lambda: _safe_walk(s, "1.3.6.1.2.1.2.2.1.7"))
        oper = await asyncio.to_thread(lambda: _safe_walk(s, "1.3.6.1.2.1.2.2.1.8"))

        # VLAN PVID via Q-BRIDGE-MIB
        pvids = await asyncio.to_thread(
            lambda: _safe_walk(s, "1.3.6.1.2.1.17.7.1.4.5.1.1")
        )

        results = []

        for i, item in enumerate(ifnames):
            idx = int(item.oid_index)
            name = item.value

            admin_up = int(admin[i].value) == 1 if i < len(admin) else False
            oper_up = int(oper[i].value) == 1 if i < len(oper) else False

            vlan = None
            for pv in pvids:
                if int(pv.oid_index) == idx:
                    vlan = int(pv.value)
                    break

            results.append({
                "port": idx,
                "name": name,
                "admin_up": admin_up,
                "oper_up": oper_up,
                "vlan": vlan
            })

        return results

    # ---------------------------------------------------------------
    # SET PORT ADMIN STATE (Cisco supports IF-MIB)
    # ---------------------------------------------------------------
    async def set_port_state(self, port: int, enabled: bool):
        s = await self._session()

        def do():
            try:
                s.set(f"1.3.6.1.2.1.2.2.1.7.{port}", 1 if enabled else 2, "i")
                return True
            except:
                return False

        return await asyncio.to_thread(do)

    # ---------------------------------------------------------------
    # VLAN CONTROL (PVID)
    # ---------------------------------------------------------------
    async def set_port_vlan(self, port: int, vlan: int):
        s = await self._session()

        def do():
            try:
                s.set(f"1.3.6.1.2.1.17.7.1.4.5.1.1.{port}", vlan, "i")
                return True
            except:
                return False

        return await asyncio.to_thread(do)

    # ---------------------------------------------------------------
    # MAC TABLE
    # ---------------------------------------------------------------
    async def get_mac_table(self):
        s = await self._session()

        macs = await asyncio.to_thread(lambda: _safe_walk(s, "1.3.6.1.2.1.17.4.3.1.1"))
        ports = await asyncio.to_thread(lambda: _safe_walk(s, "1.3.6.1.2.1.17.4.3.1.2"))

        table = []
        for i, item in enumerate(macs):
            mac = ":".join(f"{ord(c):02x}" for c in item.value)
            port = int(ports[i].value) if i < len(ports) else None
            table.append({"mac": mac, "port": port})

        return table

    # ---------------------------------------------------------------
    # LLDP
    # ---------------------------------------------------------------
    async def get_lldp_neighbors(self):
        s = await self._session()

        rem_port = await asyncio.to_thread(lambda: _safe_walk(s, "1.0.8802.1.1.2.1.4.1.1.7"))
        rem_name = await asyncio.to_thread(lambda: _safe_walk(s, "1.0.8802.1.1.2.1.4.1.1.9"))

        neighbors = []
        for i, item in enumerate(rem_port):
            neighbors.append({
                "port": item.value,
                "neighbor": rem_name[i].value if i < len(rem_name) else None
            })

        return neighbors

    # ---------------------------------------------------------------
    # PoE (Cisco uses POWER-ETHERNET-MIB)
    # ---------------------------------------------------------------
    async def set_poe_state(self, port: int, enabled: bool):
        s = await self._session()

        def do():
            try:
                s.set(f"1.3.6.1.2.1.105.1.1.1.3.{port}", 1 if enabled else 2, "i")
                return True
            except:
                return False

        return await asyncio.to_thread(do)