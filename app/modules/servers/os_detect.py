import paramiko
import socket

def detect_linux(ip, username="root", password=None, timeout=3):
    """Returns Linux distribution string or None."""
    try:
        sock = socket.create_connection((ip, 22), timeout=timeout)
        sock.close()
    except:
        return None  # Port 22 closed → not Linux or SSH disabled

    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(ip, username=username, password=password, timeout=timeout)

        stdin, stdout, stderr = client.exec_command(
            "grep '^PRETTY_NAME=' /etc/os-release | cut -d '=' -f2 | tr -d '\"'"
        )

        result = stdout.read().decode().strip()
       