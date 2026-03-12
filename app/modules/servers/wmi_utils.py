import socket

def port_open(ip, port, timeout=1.0):
    try:
        s = socket.create_connection((ip, port), timeout=timeout)
        s.close()
        return True
    except Exception:
        return False

def is_windows_host(ip: str) -> bool:
    """
    Returns True if the remote host looks like a Windows WSMan endpoint.
    Logic:
      - If port 5985 (HTTP WSMan) is open → likely Windows
      - If port 5986 (HTTPS WSMan) is open → likely Windows
      - If both closed → safely assume non-Windows
    This avoids needing credentials entirely.
    """
    if port_open(ip, 5985):   # WinRM HTTP
        return True
    if port_open(ip, 5986):   # WinRM HTTPS
        return True
    return False