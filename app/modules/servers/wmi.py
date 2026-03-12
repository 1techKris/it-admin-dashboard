import winrm
import json
from datetime import datetime


class WmiTransportError(Exception):
    pass


def _session(host, username, password, transport):
    """
    pywinrm >= 0.5 compatible session.
    transport: ntlm, plaintext, ssl
    """
    return winrm.Session(
        host,
        auth=(username, password),
        transport=transport,
        server_cert_validation="ignore",
    )


def fetch_wmi(host, username, password):
    """
    Super-simple WMI collector.
    - Always returns clean JSON or error text.
    - Never uses indexing.
    - Never parses manually.
    - Never crashes on empty output.
    """

    transports = ["ntlm", "plaintext", "ssl"]
    session = None
    last_error = None

    # Try transports until one connects
    for t in transports:
        try:
            s = _session(host, username, password, t)
            # Probe
            s.run_ps("hostname")
            session = s
            break
        except Exception as e:
            last_error = e

    if session is None:
        raise WmiTransportError(f"WinRM unreachable: {last_error}")

    def run_json(ps):
        """Run a PS command that outputs JSON, return parsed dict or error."""
        try:
            script = ps + " | ConvertTo-Json -Depth 4"
            r = session.run_ps(script)
            out = (r.std_out or b"").decode(errors="ignore").strip()
            err = (r.std_err or b"").decode(errors="ignore").strip()

            if not out:
                return {"error": err or "Empty output"}

            try:
                return json.loads(out)
            except Exception:
                return {"error": "Invalid JSON", "raw": out}

        except Exception as e:
            return {"error": str(e)}

    # VERY simple: just query raw CIM classes
    os_info   = run_json("(Get-CimInstance Win32_OperatingSystem)")
    cpu_info  = run_json("(Get-CimInstance Win32_Processor)")
    ram_info  = run_json("(Get-CimInstance Win32_ComputerSystem)")
    disks     = run_json("(Get-CimInstance Win32_LogicalDisk -Filter 'DriveType=3')")
    adapters  = run_json("(Get-CimInstance Win32_NetworkAdapterConfiguration -Filter 'IPEnabled=True')")

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "os": os_info,
        "cpu": cpu_info,
        "ram": ram_info,
        "disks": disks,
        "adapters": adapters,
    }