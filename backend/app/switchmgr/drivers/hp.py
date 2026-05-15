import asyncio
from easysnmp import Session
from .base import BaseSwitchDriver

def _walk(s, oid):
    try: return s.walk(oid)
    except: return []

def _get(s, oid):
    try:
        item = s.get(oid)
        return item.value if item else None
    except:
        return None


class HpSwitchDriver(BaseSwitchDriver):

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

    # -------------------------------
    # BASIC INFO
    # -------------------------------
    async def get_basic_info(self):
        s = await self._session()
        return {
            "sysDescr": await asyncio.to_thread(lambda: _get(s, "1.3.6.1.2.1.1.1.0")),
            "sysName": await asyncio.to_thread(lambda: _get(s, "1.3.6.1.2.1.1.5.0")),
        }

    # -------------------------------
    # PORTS
    # -------------------------------
    async def get_ports(self):
        s = await self._session()

        ifnames = await asyncio.to_thread(lambda: _walk(s, "1.3.6.1.2.1.31.1.1.1.1"))
        admin = await asyncio.to_thread(lambda: _walk(s, "1.3.6.1.2.1.2.2.1.7"))
        oper = await asyncio.to_thread(lambda: _walk(s, "1.3.6.1.2.1.2.2.1.8"))
        pvids = await asyncio.to_thread(lambda: _walk(s, "1.3.6.1.2.1.17.7.1.4.5.1.1"))

        results = []

        for i, item in enumerate(ifnames):
            idx = int(item.oid_index)

            vlan = None
            for pv in pvids:
                if int(pv.oid_index) == idx:
                    vlan = int(pv.value)
                    break

            results.append({
                "port": idx,
                "name": item.value,
                "admin_up": int(admin[i].value) == 1 if i < len(admin) else False,
                "oper_up": int(oper[i].value) == 1 if i < len(oper) else False,
                "vlan": vlan
            })

        return results

    # -------------------------------
    # ADMIN STATE
    # -------------------------------
    async def set_port_state(self, port, enabled):
        s = await self._session()

        def do():
            try:
                s.set(f"1.3.6.1.2.1.2.2.1.7.{port}", 1 if enabled else 2, "i")
                return True
            except:
                return False

        return await asyncio.to_thread(do)

    # -------------------------------
    # VLAN
    # -------------------------------
    async def set_port_vlan(self, port, vlan):
        s = await self._session()

        def do():
            try:
                s.set(f"1.3.6.1.2.1.17.7.1.4.5.1.1.{port}", vlan, "i")
                return True
            except:
                return False

        return await asyncio.to_thread(do)

    # -------------------------------
    # MAC TABLE
    # -------------------------------
    async def get_mac_table(self):
        s = await self._session()

        macs = await asyncio.to_thread(lambda: _walk(s, "1.3.6.1.2.1.17.4.3.1.1"))
        ports = await asyncio.to_thread(lambda: _walk(s, "1.3.6.1.2.1.17.4.3.1.2"))

        result = []
        for i, m in enumerate(macs):
            mac = ":".join(f"{ord(c):02x}" for c in m.value)
            result.append({"mac": mac, "port": int(ports[i].value)})
        return result

    # -------------------------------
    # LLDP
    # -------------------------------
    async def get_lldp_neighbors(self):
        s = await self._session()

        ports = await asyncio.to_thread(lambda: _walk(s, "1.0.8802.1.1.2.1.4.1.1.7"))
        names = await asyncio.to_thread(lambda: _walk(s, "1.0.8802.1.1.2.1.4.1.1.9"))

        neigh = []
        for i, p in enumerate(ports):
            neigh.append({
                "port": p.value,
                "neighbor": names[i].value if i < len(names) else None
            })

        return neigh

    # -------------------------------
    # POE (HP has several MIBs but POWER-ETHERNET-MIB is common)
    # -------------------------------
    async def set_poe_state(self, port, enabled):
        s = await self._session()

        def do():
            try:    
                s.set(f"1.3.6.1.2.1.105.1.1.1.3.{port}", 1 if enabled else 2, "i")
                return True
            except:
                return False

        return await asyncio.to_thread(do)