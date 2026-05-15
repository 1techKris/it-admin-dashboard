import asyncio
import contextlib
import ipaddress
import shlex
import socket
import shutil
import uuid
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from easysnmp import Session

from app.db.session import AsyncSessionLocal
from app.models.scan_history import ScanHistory

from .banner_grabber import grab_http_banner, grab_ssh_banner, grab_smb_banner_from_name
from .fingerprint_engine import classify_device  # NEW
from .os_fingerprint import guess_device_type  # still used for legacy detection where applicable

logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------
# Global defaults / executors
# ----------------------------------------------------------------------

SNMP_EXECUTOR = ThreadPoolExecutor(max_workers=20, thread_name_prefix="snmp_worker")

SCAN_CANCEL_FLAGS: Dict[str, bool] = {}

DEFAULT_CONCURRENCY = 16
DEFAULT_HOST_DELAY = 0.05


def _cancelled(scan_id: str) -> bool:
    return SCAN_CANCEL_FLAGS.get(scan_id, False)


# ----------------------------------------------------------------------
# Data classes
# ----------------------------------------------------------------------

@dataclass
class HostResult:
    ip: str
    alive: bool = False
    hostname: Optional[str] = None
    open_ports: List[int] = field(default_factory=list)
    banners: Dict[int, str] = field(default_factory=dict)
    os: Optional[str] = None
    device_class: Optional[str] = None  # NEW
    vendor: Optional[str] = None
    model: Optional[str] = None
    sysdescr: Optional[str] = None
    updated_at: Optional[float] = None


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

    concurrency: int = DEFAULT_CONCURRENCY
    host_delay: float = DEFAULT_HOST_DELAY
    timeouts: Dict[str, float] = field(default_factory=dict)

    started_at: float = field(default_factory=lambda: datetime.utcnow().timestamp())
    finished_at: Optional[float] = None


SCANS: Dict[str, ScanState] = {}


# ----------------------------------------------------------------------
# Utils
# ----------------------------------------------------------------------

async def _run_cmd(cmd: str, timeout: float) -> int:
    try:
        proc = await asyncio.create_subprocess_exec(
            *shlex.split(cmd),
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return proc.returncode
    except Exception:
        return 1


async def _ping_host(scan_id: str, ip: str, timeout_s: float) -> bool:
    if _cancelled(scan_id):
        return False
    cmd = f"ping -c 1 -W {int(timeout_s)} {ip}"
    return await _run_cmd(cmd, timeout_s + 0.3) == 0


async def _check_port(scan_id: str, ip: str, port: int, timeout_s: float) -> bool:
    if _cancelled(scan_id):
        return False
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


async def _rdns(scan_id: str, ip: str, timeout_s: float):
    if _cancelled(scan_id):
        return None

    async def do_lookup():
        try:
            return socket.gethostbyaddr(ip)[0]
        except Exception:
            return None

    try:
        return await asyncio.wait_for(asyncio.to_thread(do_lookup), timeout=timeout_s)
    except Exception:
        return None


async def _netbios_name(scan_id: str, ip: str, timeout_s: float):
    if _cancelled(scan_id):
        return None

    path = shutil.which("nmblookup")
    if not path:
        return None

    try:
        proc = await asyncio.create_subprocess_exec(
            path, "-A", ip,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout_s)
        text = out.decode("utf-8", errors="ignore")

        for line in text.splitlines():
            line = line.strip()
            if "<00>" in line and "<GROUP>" not in line:
                return line.split("<")[0].strip()

    except Exception:
        return None

    return None


async def _get_sysdescr(scan_id: str, ip: str, community: str, timeout: float):
    if _cancelled(scan_id):
        return None

    def do_snmp():
        try:
            sess = Session(
                hostname=ip,
                community=community,
                version=2,
                timeout=int(timeout),
                retries=1,
            )
            item = sess.get("1.3.6.1.2.1.1.1.0")
            return item.value if item else None
        except Exception:
            return None

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(SNMP_EXECUTOR, do_snmp)


# ----------------------------------------------------------------------
# Host Scanning
# ----------------------------------------------------------------------

async def _scan_host(scan_id, ip, ports, sem, t) -> HostResult:
    if _cancelled(scan_id):
        return HostResult(ip=ip)

    res = HostResult(ip=ip)
    changed = False

    # Ping
    async with sem:
        res.alive = await _ping_host(scan_id, ip, timeout_s=t["ping"])

    if _cancelled(scan_id):
        return res

    # DNS / NetBIOS
    rdns_task = asyncio.create_task(_rdns(scan_id, ip, t["rdns"]))
    nb_task = asyncio.create_task(_netbios_name(scan_id, ip, t["netbios"]))

    # Port scanning
    async def probe(port: int):
        if _cancelled(scan_id):
            return None
        async with sem:
            if await _check_port(scan_id, ip, port, timeout_s=t["port"]):
                return port
        return None

    port_tasks = {p: asyncio.create_task(probe(p)) for p in ports}

    for task in asyncio.as_completed([*port_tasks.values(), rdns_task, nb_task]):
        val = await task

        if isinstance(val, int):
            res.open_ports.append(val)
            changed = True
        elif isinstance(val, str) and not res.hostname:
            res.hostname = val
            changed = True

    if not res.alive and res.open_ports:
        res.alive = True
        changed = True

    # Banner grabbing
    banners = {}

    if 22 in res.open_ports:
        banners[22] = asyncio.create_task(grab_ssh_banner(ip, 22))
    if 80 in res.open_ports:
        banners[80] = asyncio.create_task(grab_http_banner(ip, 80, use_ssl=False))
    if 443 in res.open_ports:
        banners[443] = asyncio.create_task(grab_http_banner(ip, 443, use_ssl=True))
    if 445 in res.open_ports:
        banners[445] = asyncio.create_task(grab_smb_banner_from_name(res.hostname))

    for p, task in banners.items():
        if _cancelled(scan_id):
            return res
        try:
            banner = await asyncio.wait_for(task, timeout=t["banner"])
            if banner:
                res.banners[p] = banner
                changed = True
        except Exception:
            pass

    # SNMP sysDescr
    res.sysdescr = await _get_sysdescr(scan_id, ip, "public", timeout=t["snmp"])

    # ------------------------------------------------------------------
    # FINGERPRINT ENGINE (NEW)
    # ------------------------------------------------------------------
    classification = classify_device(
        ip=res.ip,
        open_ports=res.open_ports,
        banners=res.banners,
        hostname=res.hostname,
        sysdescr=res.sysdescr,
    )

    res.device_class = classification["class"]
    res.vendor = classification["vendor"]
    res.model = classification["model"]
    if classification["os"]:
        res.os = classification["os"]

    # If changed, update timestamp
    if changed or res.device_class or res.vendor or res.model:
        res.updated_at = datetime.utcnow().timestamp()

    return res


# ----------------------------------------------------------------------
# Scan Controller
# ----------------------------------------------------------------------

async def start_scan(cidr, ports, concurrency, host_delay, timeouts):
    net = ipaddress.ip_network(cidr, strict=False)
    hosts = [str(h) for h in net.hosts()]
    scan_id = str(uuid.uuid4())

    # Default timeouts if UI sent none
    if not timeouts:
        timeouts = {
            "ping": 0.5,
            "port": 1.0,
            "snmp": 1.5,
            "banner": 1.0,
            "rdns": 0.7,
            "netbios": 1.0,
        }

    state = ScanState(
        id=scan_id,
        cidr=cidr,
        ports=ports,
        total=len(hosts),
        concurrency=concurrency,
        host_delay=host_delay,
        timeouts=timeouts,
    )

    SCANS[scan_id] = state
    SCAN_CANCEL_FLAGS[scan_id] = False

    asyncio.create_task(_run_scan(state, hosts))
    return state


async def _run_scan(state, hosts):
    sem = asyncio.Semaphore(state.concurrency)

    try:
        for ip in hosts:
            if _cancelled(state.id):
                state.status = "cancelled"
                break

            res = await _scan_host(state.id, ip, state.ports, sem, state.timeouts)
            state.results[ip] = res
            state.completed += 1

            if state.host_delay:
                await asyncio.sleep(state.host_delay)

        if state.status != "cancelled":
            state.status = "finished"

        state.finished_at = datetime.utcnow().timestamp()

    except Exception as e:
        state.status = "error"
        state.error = str(e)
        state.finished_at = datetime.utcnow().timestamp()

    finally:
        await _write_history(state)


# ----------------------------------------------------------------------
# History Storage
# ----------------------------------------------------------------------

async def _write_history(state: ScanState):
    async with AsyncSessionLocal() as session:
        rec = ScanHistory(
            id=state.id,
            cidr=state.cidr,
            total=state.total,
            completed=state.completed,
            status=state.status,
            speed_concurrency=state.concurrency,
            speed_delay=state.host_delay,
            started_at=datetime.utcfromtimestamp(state.started_at),
            finished_at=datetime.utcfromtimestamp(state.finished_at),
        )
        session.add(rec)
        await session.commit()


# ----------------------------------------------------------------------
# Public API
# ----------------------------------------------------------------------

def cancel_scan(scan_id: str) -> bool:
    if scan_id in SCAN_CANCEL_FLAGS:
        SCAN_CANCEL_FLAGS[scan_id] = True
        return True
    return False


def get_scan(scan_id: str):
    return SCANS.get(scan_id)