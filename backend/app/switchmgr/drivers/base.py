class BaseSwitchDriver:
    """All vendor drivers must implement these."""
    
    def __init__(self, ip: str, community="public", **kwargs):
        self.ip = ip
        self.community = community

    async def get_basic_info(self):
        raise NotImplementedError

    async def get_ports(self):
        raise NotImplementedError

    async def set_port_state(self, port: int, enabled: bool):
        raise NotImplementedError

    async def set_port_vlan(self, port: int, vlan: int):
        raise NotImplementedError

    async def get_mac_table(self):
        raise NotImplementedError

    async def get_lldp_neighbors(self):
        raise NotImplementedError

    async def set_poe_state(self, port: int, enabled: bool):
        raise NotImplementedError