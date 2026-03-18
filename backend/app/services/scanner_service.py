import asyncio
import contextlib
import ipaddress
import shlex
import socket
import shutil
import uuid
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor

from easysnmp import Session

from .banner_grabber import grab_http_banner, grab_ssh_banner, grab_smb_banner_from_name
from .os_fingerprint import guess_device_type


logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------------------
# Safe Defaults & Executors
# --------------------------------------------------------------------------------------

SNMP_EXECUTOR = ThreadPoolExecutor(max_workers=20, thread_name_prefix="snmp_worker")

DEFAULT_CONCURRENCY = 16      # Safer than 64
DEFAULT_HOST_DELAY = 0.05     # 50ms between hosts (throttling)


# --------------------------------------------------------------------------------------
# Data Models
# --------------------------------------------------------------------------------------

@dataclass
class HostResult:
    ip: str
    alive: bool = False
    hostname: Optional[str] = None
    open_ports: List[int] = field(default_factory=list)
    banners: Dict[int, str] = field(default_factory=dict)
    os: Optional[str] = None
    device_type: Optional[str] = None
    vendor: Optional[str] = None
    model: Optional[str] = None
    sysdescr: Optional[str] = None


@dataclass
class ScanState:
    id: str
    cidr: str
    ports: List[int]
    status: str = "running"
    total: int = 0
    completed: int = 0
    results: Dict[str, HostResult] = field(default_factory=dict)
    error: Optional[str] = None


SCANS: Dict[str, ScanState] = {}   # In‑memory store


# --------------------------------------------------------------------------------------
# Helper Functions
# --------------------------------------------------------------------------------------

async def _run_cmd(cmd: str, timeout: float) -> int:
    """Execute a shell command with timeout and return exit code."""
    try:
        proc = await asyncio.create_subprocess_exec(
            *shlex.split(cmd),
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return proc.returncode
    except asyncio.TimeoutError:
        with contextlib.suppress(ProcessLookupError):
            proc.kill()
        return 1
    except Exception:
        return 1


async def _ping_host(ip: str, timeout_s: float = 1.0) -> bool:
    """Ping a host using the system ping command."""
    cmd = f"ping -c 1 -W {int(timeout_s)} {ip}"
    return await _run_cmd(cmd, timeout_s + 0.5) == 0


async def _check_port(ip: str, port: int, timeout_s: float = 2.5) -> bool:
    """Try opening a TCP connection to a port."""
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(ip, port), timeout=timeout_s
        )
        writer.close()
        with contextlib.suppress(Exception):
            await writer.wait_closed()
        return True
    except Exception:
        return False


async def _rdns(ip: str, timeout_s: float = 1.5) -> Optional[str]:
    """Reverse DNS lookup with timeout."""
    async def _lookup():
        try:
            return socket.gethostbyaddr(ip)[0]
        except Exception:
            return None

    try:
        return await asyncio.wait_for(asyncio.to_thread(_lookup), timeout=timeout_s)
    except asyncio.TimeoutError:
        return None


async def _netbios_name(ip: str, timeout_s: float = 2.0) -> Optional[str]:
    """Retrieve NetBIOS name via nmblookup, parse workstation name (0x00)."""
    nmb = shutil.which("nmblookup")
    if not nmb:
        return None

    try:
        proc = await asyncio.create_subprocess_exec(
            nmb, "-A", ip,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout_s)
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


async def _get_sysdescr(ip: str, community: str = "public", timeout: float = 2.0) -> Optional[str]:
    """SNMP sysDescr retrieval (blocking call in dedicated executor)."""

    def snmp_query():
        try:
            s = Session(
                hostname=ip,
                community=community,
                version=2,
                timeout=int(timeout),
                retries=1,
            )
            item = s.get("1.3.6.1.2.1.1.1.0")
            return item.value if item and item.value else None
        except Exception as e:
            logger.debug(f"SNMP failure {ip}: {e}")
            return None

    try:
        return await asyncio.get_running_loop().run_in_executor(
            SNMP_EXECUTOR, snmp_query
        )
    except Exception as e:
        logger.warning(f"SNMP executor error for {ip}: {e}")
        return None


# --------------------------------------------------------------------------------------
# Host Scanning
# --------------------------------------------------------------------------------------

async def _scan_host(ip: str, ports: List[int], sem: asyncio.Semaphore) -> HostResult:
    res = HostResult(ip=ip)

    try:
        # ---------------- Ping ----------------
        async with sem:
            res.alive = await _ping_host(ip)

        # ---------------- DNS + NetBIOS ----------------
        dns_task = asyncio.create_task(_rdns(ip))
        nb_task = asyncio.create_task(_netbios_name(ip))

        # ---------------- Port scanning ----------------
        async def probe(port: int) -> Optional[int]:
            async with sem:
                if await _check_port(ip, port):
                    return port
            return None

        port_tasks = {port: asyncio.create_task(probe(port)) for port in ports}

        # consume RDNS + NetBIOS while ports are scanning
        for coro in asyncio.as_completed(list(port_tasks.values()) + [dns_task, nb_task]):
            res_val = await coro

            # Port result
            if isinstance(res_val, int):
                res.open_ports.append(res_val)

            # Hostname result
            elif isinstance(res_val, str) and res_val:
                if not res.hostname:
                    res.hostname = res_val

        if not res.alive and res.open_ports:
            res.alive = True

        # ---------------- Banner grabbing ----------------
        banner_tasks = {}

        if 22 in res.open_ports:
            banner_tasks[22] = asyncio.create_task(grab_ssh_banner(ip, 22))

        if 80 in res.open_ports:
            banner_tasks[80] = asyncio.create_task(grab_http_banner(ip, 80, use_ssl=False))

        if 443 in res.open_ports:
            banner_tasks[443] = asyncio.create_task(grab_http_banner(ip, 443, use_ssl=True))

        if 445 in res.open_ports:
            banner_tasks[445] = asyncio.create_task(grab_smb_banner_from_name(res.hostname))

        for port, task in banner_tasks.items():
            try:
                banner = await task
                if banner:
                    res.banners[port] = banner
            except Exception:
                pass

        # ---------------- SNMP sysDescr ----------------
        res.sysdescr = await _get_sysdescr(ip)

        # ---------------- Device fingerprinting ----------------
        inventory = guess_device_type(
            open_ports=res.open_ports,
            hostname=res.hostname,
            ssh_banner=res.banners.get(22),
            http_banner=res.banners.get(80) or res.banners.get(443),
            netbios_name=res.hostname,
            sysdescr=res.sysdescr,
        )

        res.os = inventory["device_type"]
        res.device_type = inventory["device_type"]
        res.vendor = inventory["vendor"]
        res.model = inventory["model"]

    except Exception as e:
        logger.error(f"Error scanning host {ip}: {e}", exc_info=True)

    return res


# --------------------------------------------------------------------------------------
# Scan Controller
# --------------------------------------------------------------------------------------

async def start_scan(
    cidr: str,
    ports: List[int],
    concurrency: int = DEFAULT_CONCURRENCY,
    host_delay: float = DEFAULT_HOST_DELAY,
) -> ScanState:

    try:
        net = ipaddress.ip_network(cidr, strict=False)
    except Exception as e:
        raise ValueError(f"Invalid CIDR {cidr}: {e}")

    hosts = [str(h) for h in net.hosts()]
    scan_id = str(uuid.uuid4())

    state = ScanState(
        id=scan_id,
        cidr=cidr,
        ports=sorted(set(ports)),
        total=len(hosts),
        status="running",
    )

    SCANS[scan_id] = state

    asyncio.create_task(_run_scan(state, hosts, concurrency, host_delay))

    logger.info(
        f"Started scan {scan_id}: {cidr} ({len(hosts)} hosts) concurrency={concurrency} delay={host_delay}"
    )

    return state


async def _run_scan(state: ScanState, hosts: List[str], concurrency: int, host_delay: float):
    sem = asyncio.Semaphore(concurrency)

    try:
        for ip in hosts:
            res = await _scan_host(ip, state.ports, sem)
            state.results[ip] = res
            state.completed += 1      # SAFE increment

            if host_delay > 0:
                await asyncio.sleep(host_delay)

        state.status = "finished"
        logger.info(f"Scan {state.id} completed successfully.")

    except Exception as e:
        state.status = "error"
        state.error = str(e)
        logger.error(f"Scan error {state.id}: {e}", exc_info=True)


def get_scan(scan_id: str) -> Optional[ScanState]:
    return SCANS.get(scan_id)