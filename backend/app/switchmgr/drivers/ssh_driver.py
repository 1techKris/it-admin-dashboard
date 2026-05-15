import asyncssh

class SshDriver:
    def __init__(self, ip, username, password):
        self.ip = ip
        self.username = username
        self.password = password

    async def run(self, cmd):
        async with asyncssh.connect(self.ip, username=self.username, password=self.password) as conn:
            return await conn.run(cmd)