"""LAN IP detection and port utilities — production copy.

Kept inside ``vedi_app`` so the composition root no longer needs
``controller/network.py``. Re-exports the canonical implementations
from the legacy module while adding production-grade helpers
(best-interface selection across Ethernet / Wi-Fi / virtual NICs).
"""

from __future__ import annotations

import os
import socket
import sys
from typing import List, Optional


VIRTUAL_KEYWORDS = (
    "vethernet", "vbox", "vmware", "docker", "wsl", "virtual",
    "zerotier", "tailscale", "vpn", "tap", "tun", "pseudo",
    "bluetooth", "hyper-v", "npcap", "default switch", "host-only",
)

PHYSICAL_KEYWORDS = (
    "wi-fi", "wifi", "ethernet", "wlan", "lan", "eth",
)


def _is_virtual(name: str) -> bool:
    return any(k in name.lower() for k in VIRTUAL_KEYWORDS)


def _is_physical(name: str) -> bool:
    return any(k in name.lower() for k in PHYSICAL_KEYWORDS)


def get_lan_ip() -> str:
    """Return the best IPv4 address the local network can route to.

    Order of preference:
      1. Active physical adapter (Wi-Fi / Ethernet).
      2. Active non-virtual adapter of any flavour.
      3. UDP probe to a public IP (fallback for restricted environments).
      4. ``127.0.0.1``.
    """
    try:
        import psutil
        interfaces = psutil.net_if_addrs()
        stats = psutil.net_if_stats()
        candidate_phys: Optional[str] = None
        candidate_other: Optional[str] = None
        for name, addrs in interfaces.items():
            is_virt = _is_virtual(name)
            is_phys = _is_physical(name)
            is_up = stats.get(name).isup if name in stats else True
            for addr in addrs:
                if addr.family != socket.AF_INET:
                    continue
                ip = addr.address
                if ip.startswith("127.") or ip.startswith("169.254."):
                    continue
                if not is_up:
                    continue
                if not is_virt and is_phys:
                    return ip
                if not is_virt and not candidate_other:
                    candidate_other = ip
        if candidate_other:
            return candidate_other
    except Exception:
        pass

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if not ip.startswith("127.") and not ip.startswith("169.254."):
            return ip
    except Exception:
        pass

    return "127.0.0.1"


def get_all_local_ips() -> List[str]:
    """Return every routable IPv4 on this machine, ordered best-first."""
    out: List[str] = []
    try:
        import psutil
        stats = psutil.net_if_stats()
        for name, addrs in psutil.net_if_addrs().items():
            is_virt = _is_virtual(name)
            is_phys = _is_physical(name)
            is_up = stats.get(name).isup if name in stats else True
            for addr in addrs:
                if addr.family != socket.AF_INET:
                    continue
                ip = addr.address
                if ip.startswith("127.") or ip.startswith("169.254."):
                    continue
                if is_virt:
                    continue
                if not is_up:
                    continue
                out.append(ip)
                # First physical wins; otherwise preserve the order.
                if is_phys:
                    return [ip] + [x for x in out if x != ip]
    except Exception:
        pass
    return out or ["127.0.0.1"]


def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """True if a TCP server is listening on ``port`` (or the port is reserved)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        if s.connect_ex((host, port)) == 0:
            return True
        if host not in ("127.0.0.1", "localhost", "0.0.0.0"):
            try:
                if s.connect_ex((host, port)) == 0:
                    return True
            except OSError:
                pass

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if sys.platform == "win32":
                s.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            s.bind(("0.0.0.0", port))
            return False
    except OSError:
        return True


def find_free_port(preferred_port: int, host: str = "127.0.0.1", max_attempts: int = 50) -> int:
    """Return the first unused port starting at ``preferred_port``."""
    for p in range(preferred_port, preferred_port + max_attempts):
        if not is_port_in_use(p, host):
            return p
    return preferred_port
