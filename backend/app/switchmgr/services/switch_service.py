from .driver_resolver import driver_for_switch

async def load_switch_driver(switch):
    Driver = driver_for_switch(switch.vendor)
    return Driver(switch.ip, community="public")

async def get_port_list(switch):
    drv = await load_switch_driver(switch)
    return await drv.get_ports()

async def set_port_state(switch, port, enabled):
    drv = await load_switch_driver(switch)
    return await drv.set_port_state(port, enabled)

async def set_port_vlan(switch, port, vlan):
    drv = await load_switch_driver(switch)
    return await drv.set_port_vlan(port, vlan)