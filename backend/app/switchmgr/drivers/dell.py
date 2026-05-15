import asyncio
from easysnmp import Session
from .base import BaseSwitchDriver

def safe_get(s, oid):
    try:
        i = s.get(oid)
        return i.value if i else None
    except:
        return None

def safe_walk(s, oid):
    try: return s.walk(oid)
    except: return []


class DellSwitchDriver(BaseSwitchDriver):
    """
    Dell N-Series / Force10 generic SNMP driver.
    """

    async def _session(self):
        return await asyncio.to_thread(
            lambda: Session(
                hostname=self.ip,
                community=self.community,
                version=2,
                timeout=2,
                retries=1,
            )
        )

    async def get_basic_info(self):
        s = await self._session()
        return {
            "sysDescr": await asyncio.to_thread(lambda: safe_get(s, "1.3.6.1.2.1.1.1.0")),
            "sysName": await asyncio.to_thread(lambda: safe_get(s, "1.3.6.1.2.1.1.5.0")),
        }

    async def get_ports(self):
        s = await self._session()

        ifnames = await asyncio.to_thread(lambda: safe_walk(s, "1.3.6.1.2.1.31.1.1.1.1"))
        admin = await asyncio.to_thread(lambda: safe_walk(s, "1.3.6.1.2.1.2.2.1.7"))
        oper = await asyncio.to_thread(lambda: safe_walk(s, "1.3.6.1.2.1.2.2.1.8"))
        pvids = await asyncio.to_thread(lambda: safe_walk(s, "1.3.6.1.2.1.17.7.1.4.5.1.1"))

        ports = []

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

            ports.append({
                "port": idx,
                "name": name,
                "admin_up": admin_up,
                "oper_up": oper_up,
                "vlan": vlan,
            })

        return ports

    async def set_port_state(self, port, enabled):
        s = await self._session()

        def do():
            try:
                s.set(f"1.3.6.1.2.1.2.2.1.7.{port}", 1 if enabled else 2, "i")
                return True
            except:
                return False

        return await asyncio.to_thread(do)

    async def set_port_vlan(self, port, vlan):
        s = await self._session()

        def do():
            try:
                s.set(f"1.3.6.1.2.1.17.7.1.4.5.1.1.{port}", vlan, "i")
                return True
            except:
                return False

        return await asyncio.to_thread(do)

    async def get_mac_table(self):
        s = await self._session()

        macs = await asyncio.to_thread(lambda: safe_walk(s, "1.3.6.1.2.1.17.4.3.1.1"))
        ports = await asyncio.to_thread(lambda: safe_walk(s, "1.3.6.1.2.1.17.4.3.1.2"))

        table = []
        for i, m in enumerate(macs):
            mac = ":".join(f"{ord(c):02x}" for c in m.value)
            table.append({
                "mac": mac,
                "port": int(ports[i].value) if i < len(ports) else None,
            })

        return table

    async def get_lldp_neighbors(self):
        s = await self._session()

        rem_port = await asyncio.to_thread(lambda: safe_walk(s, "1.0.8802.1.1.2.1.4.1.1.7"))
        rem_name = await asyncio.to_thread(lambda: safe_walk(s, "1.0.8802.1.1.2.1.4.1.1.9"))

        neighbors = []
        for i, p in enumerate(rem_port):
            neighbors.append({
                "port": p.value,
                "neighbor": rem_name[i].value if i < len(rem_name) else None
            })

        return neighbors

    async def set_poe_state(self, port, enabled):
        s = await self._session()

        def do():
            try:
                s.set(f"1.3.6.1.2.1.105.1.1.1.3.{port}", 1 if enabled else 2, "i")
                return True
            except:
                return False

        return await asyncio.to_thread(do)