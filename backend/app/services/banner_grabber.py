# backend/app/services/banner_grabber.py
import asyncio
import ssl
import re
from typing import Optional

async def _read_with_timeout(reader: asyncio.StreamReader, n: int = 4096, timeout: float = 1.8) -> bytes:
    try:
        return await asyncio.wait_for(reader.read(n), timeout=timeout)
    except Exception:
        return b""

async def grab_ssh_banner(ip: str, port: int = 22, timeout: float = 2.5) -> Optional[str]:
    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(ip, port), timeout)
        # SSH server usually sends its banner immediately
        data = await _read_with_timeout(reader, 256, timeout=1.2)
        writer.close()
        with asyncio.CancelledError:
            pass
        banner = data.decode("utf-8", errors="ignore").strip()
        return banner.splitlines()[0] if banner else None
    except Exception:
        return None

async def grab_http_banner(ip: str, port: int, timeout: float = 2.5, use_ssl: bool = False) -> Optional[str]:
    try:
        ssl_ctx = ssl.create_default_context() if use_ssl else None
        reader, writer = await asyncio.wait_for(asyncio.open_connection(ip, port, ssl=ssl_ctx), timeout)
        req = b"GET / HTTP/1.0\r\nHost: %b\r\nUser-Agent: IT-Admin-Dashboard\r\n\r\n" % ip.encode()
        writer.write(req)
        await writer.drain()
        data = await _read_with_timeout(reader, 4096, timeout=1.6)
        writer.close()
        with asyncio.CancelledError:
            pass

        text = data.decode("utf-8", errors="ignore")
        # Try Server header
        m_server = re.search(r"(?im)^Server:\s*(.+)$", text)
        server = m_server.group(1).strip() if m_server else None
        # Try <title>
        m_title = re.search(r"(?is)<\s*title[^>]*>(.*?)</\s*title\s*>", text)
        title = m_title.group(1).strip() if m_title else None

        parts = []
        if server:
            parts.append(server)
        if title:
            parts.append(f"Title: {title}")
        return " | ".join(parts) if parts else ("HTTP response" if text else None)
    except Exception:
        return None

async def grab_smb_banner_from_name(netbios_name: Optional[str]) -> Optional[str]:
    # For now we surface the NetBIOS name as the SMB banner if present
    return netbios_name or None