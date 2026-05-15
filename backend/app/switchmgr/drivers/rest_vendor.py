import httpx
from .base import BaseSwitchDriver

class RestVendorDriver(BaseSwitchDriver):
    def __init__(self, ip, api_key, **kwargs):
        self.ip = ip
        self.api_key = api_key

    async def get_ports(self):
        async with httpx.AsyncClient() as client:
            r = await client.get(f"http://{self.ip}/rest/ports", headers={"X-API-Key": self.api_key})
            return r.json()