import asyncio
import contextlib
import shlex
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.device import Device

_PING_CONCURRENCY = 64
_PING_TIMEOUT_SEC = 1.2
_INTERVAL_SEC = 30  # adjust as needed

async def _ping(ip: str, timeout: float = _PING_TIMEOUT_SEC) -> tuple[bool, int | None]:
    """
    Return (alive, latency_ms). Uses system 'ping' (no root).
    On failure or timeout → (False, None).
    """
    try:
        cmd = f"ping -c 1 -W {int(timeout)} {ip}"
        started = asyncio.get_event_loop().time()
        proc = await asyncio.create_subprocess_exec(
            *shlex.split(cmd),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        try:
            out, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout + 0.5)
        except asyncio.TimeoutError:
            with contextlib.suppress(ProcessLookupError):
                proc.kill()
            return False, None

        alive = proc.returncode == 0
        latency_ms = None
        if alive and out:
            # Try to parse 'time=XX ms' quickly; robustness over exactness
            s = out.decode("utf-8", errors="ignore")
            marker = "time="
            idx = s.find(marker)
            if idx != -1:
                frag = s[idx + len(marker):].split(" ", 1)[0]  # until next space
                try:
                    latency_ms = int(float(frag))
                except Exception:
                    latency_ms = None
        # As an approximation fallback, compute elapsed
        if alive and latency_ms is None:
            elapsed = (asyncio.get_event_loop().time() - started) * 1000
            latency_ms = int(elapsed)
        return alive, latency_ms
    except Exception:
        return False, None

async def _monitor_once(db: AsyncSession):
    # Ping all non-archived devices concurrently, then update statuses
    rows = (await db.execute(select(Device).where(Device.archived == False))).scalars().all()  # noqa: E712
    if not rows:
        return

    sem = asyncio.Semaphore(_PING_CONCURRENCY)
    async def worker(dev: Device):
        async with sem:
            alive, latency = await _ping(dev.ip)
            dev.latency_ms = latency
            if alive:
                dev.status = "Healthy" if (dev.status not in ("Warning", "Critical")) else dev.status
                dev.last_seen = datetime.now(timezone.utc)
            else:
                dev.status = "Down"
            return dev

    tasks = [asyncio.create_task(worker(d)) for d in rows]
    for t in asyncio.as_completed(tasks):
        await t

    await db.commit()

async def device_monitor_loop():
    # Background loop; safe to cancel on shutdown
    try:
        while True:
            async with AsyncSessionLocal() as db:
                await _monitor_once(db)
            await asyncio.sleep(_interval())
    except asyncio.CancelledError:
        return

def _interval() -> int:
    return _INTERVAL_SEC

def start(app):
    # Attach task to app.state to allow cleanup on shutdown
    app.state.device_monitor_task = asyncio.create_task(device_monitor_loop())

async def stop(app):
    task = getattr(app.state, "device_monitor_task", None)
    if task:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task