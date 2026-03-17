# backend/app/services/scanner_service.py
import asyncio
import contextlib
import ipaddress
import shlex
import socket
import shutil
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .banner_grabber import grab_http_banner, grab_ssh_banner, grab_smb_banner_from_name
from .os_fingerprint import guess_os

# ----------------------------- Data Models -----------------------------

@dataclass
class HostResult:
    ip: str
    alive: bool = False
    hostname: Optional[str] = None
    open_ports: List[int] = field(default_factory=list)
    banners: Dict[int, str] = field(default_factory=dict)
    os: Optional[str] = None

@dataclass
class ScanState:
    id: str
    cidr: str
    ports: List[int]
    status: str = "running"  # running | finished | error
    total: int = 0
    completed: int = 0
    results: Dict[str, HostResult] = field(default_factory=dict)
    error: Optional[str] = None

# ----------------------------- In-Memory Store -----------------------------

SCANS: Dict[str, ScanState] = {}
_CONCURRENCY = 128  # adjust based on hardware

# ----------------------------- Helper Functions -----------------------------

async def _ping_host(ip: str, timeout_s: float = 1.0) -> bool:
    """
    ICMP ping check using system 'ping'.
    If blocked, host may still be detected alive based on open ports.
    """
    try:
        cmd = f"ping -c 1 -W {int(timeout_s)} {ip}"
        proc = await asyncio.create_subprocess_exec(
            *shlex.split(cmd),
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        try:
            await asyncio.wait_for(proc.communicate(), timeout=timeout_s + 0.5)
        except asyncio.TimeoutError:
            with contextlib.suppress(ProcessLookupError):
                proc.kill()
            return False
        return proc.returncode == 0
    except Exception:
        return False

async def _check_port(ip: str, port: int, timeout_s: float = 2.5) -> bool:
    """
    TCP connect scan with extended timeout for Windows hosts.
    """
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(ip, port),
            timeout=timeout_s
        )
        writer.close()
        with contextlib.suppress(Exception):
            await writer.wait_closed()
        return True
    except Exception:
        return False

async def _rdns(ip: str) -> Optional[str]:
    """
    Reverse DNS (PTR lookup). Non-blocking using a thread.
    """
    try:
        return await asyncio.to_thread(lambda: socket.gethostbyaddr(ip)[0])
    except Exception:
        return None

async def _netbios_name(ip: str) -> Optional[str]:
    """
    Resolve NetBIOS hostname via 'nmblookup -A IP'.
    Use full path (systemd may have reduced PATH).
    """
    nmb_path = shutil.which("nmblookup")
    if not nmb_path:
        return None

    try:
        proc = await asyncio.create_subprocess_exec(
            nmb_path, "-A", ip,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=2.5)
        text = out.decode("utf-8", errors="ignore")

        for line in text.splitlines():
            line = line.strip()
            if "<00>" in line and "<GROUP>" not in line:
                name = line.split("<")[0].strip()
                if name:
                    return name
    except Exception:
        return None

    return None

# ----------------------------- Host Scanning -----------------------------

async def _scan_host(ip: str, ports: List[int], sem: asyncio.Semaphore) -> HostResult:
    res = HostResult(ip=ip)

    # Try ping (non-fatal if fails)
    async with sem:
        res.alive = await _ping_host(ip)

    # DNS + NetBIOS lookups concurrently (non-blocking)
    dns_task = asyncio.create_task(_rdns(ip))
    nb_task = asyncio.create_task(_netbios_name(ip))

    async def probe(port: int) -> Optional[int]:
        async with sem:
            is_open = await _check_port(ip, port)
            if is_open:
                return port
        return None

    port_tasks = [asyncio.create_task(probe(p)) for p in ports]

    # Collect port results + names first
    for coro in asyncio.as_completed(port_tasks + [dns_task, nb_task]):
        result = await coro
        # Open port
        if isinstance(result, int):
            res.open_ports.append(result)
            continue
        # DNS or NetBIOS hostname
        if isinstance(result, str) and result:
            if res.hostname is None:
                res.hostname = result

    # If ping fails but open ports found → host is alive
    if not res.alive and res.open_ports:
        res.alive = True

    # Banner grabbing (best-effort)
    banner_tasks: List[asyncio.Task] = []

    if 22 in res.open_ports:
        banner_tasks.append(asyncio.create_task(grab_ssh_banner(ip, 22)))
    if 80 in res.open_ports:
        banner_tasks.append(asyncio.create_task(grab_http_banner(ip, 80, use_ssl=False)))
    if 443 in res.open_ports:
        banner_tasks.append(asyncio.create_task(grab_http_banner(ip, 443, use_ssl=True)))
    if 445 in res.open_ports:
        banner_tasks.append(asyncio.create_task(grab_smb_banner_from_name(res.hostname)))

    # Map banners back to ports in same order as tasks above
    idx = 0
    for port in [22, 80, 443, 445]:
        if port in res.open_ports:
            try:
                banner = await banner_tasks[idx]
                if banner:
                    res.banners[port] = banner
            except Exception:
                pass
            idx += 1

    # OS fingerprint
    ssh_banner = res.banners.get(22)
    http_banner = res.banners.get(80) or res.banners.get(443)
    res.os = guess_os(res.open_ports, ssh_banner, http_banner, res.hostname)

    return res

# ----------------------------- Scan Controller -----------------------------

async def start_scan(cidr: str, ports: List[int]) -> ScanState:
    """
    Initialize scan state and spawn background scan task.
    """
    try:
        net = ipaddress.ip_network(cidr, strict=False)
    except Exception as e:
        raise ValueError(f"Invalid CIDR: {cidr} ({e})")

    hosts = [str(h) for h in net.hosts()]
    scan_id = str(uuid.uuid4())

    state = ScanState(
        id=scan_id,
        cidr=cidr,
        ports=sorted(set(ports)),
        status="running",
        total=len(hosts),
        completed=0,
        results={},
    )
    SCANS[scan_id] = state

    asyncio.create_task(_run_scan(state, hosts))
    return state

async def _run_scan(state: ScanState, hosts: List[str]):
    """
    Scan each host in subnet using concurrency-limited async tasks.
    """
    sem = asyncio.Semaphore(_CONCURRENCY)
    try:
        for start in range(0, len(hosts), _CONCURRENCY):
            chunk = hosts[start:start + _CONCURRENCY]
            tasks = [
                asyncio.create_task(_scan_host(ip, state.ports, sem))
                for ip in chunk
            ]
            for task in asyncio.as_completed(tasks):
                host_result = await task
                state.results[host_result.ip] = host_result
                state.completed += 1
        state.status = "finished"
    except Exception as e:
        state.status = "error"
        state.error = str(e)

# ----------------------------- Query Scans -----------------------------

def get_scan(scan_id: str) -> Optional[ScanState]:
    return SCANS.get(scan_id)