import subprocess
import re

PING_CMD = ["ping", "-c", "1", "-W", "1"]  # Linux ping: 1 packet, 1s timeout
PING_REGEX = re.compile(r"time[=<]([0-9.]+)\s*ms")

def ping_ip_ms(ip: str) -> tuple[bool, float | None]:
    """
    Returns (online, ping_ms). ping_ms is None if unknown.
    """
    try:
        result = subprocess.run(PING_CMD + [ip], capture_output=True, text=True)
        online = (result.returncode == 0)
        ping_ms = None
        if online:
            # Try to parse "time=XX.X ms" or "time<1 ms"
            m = PING_REGEX.search(result.stdout or "")
            if m:
                ping_ms = float(m.group(1))
            elif "time<" in (result.stdout or ""):
                ping_ms = 0.5
        return online, ping_ms
    except Exception:
        return False, None