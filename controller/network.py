"""LAN IP discovery and port utilities for Vedi Pocket PC Controller.

Identifies the best physical network adapter address (Wi-Fi / Ethernet)
and handles port availability checking.
"""

from __future__ import annotations

import os
import socket
import sys
from typing import List, Optional

VIRTUAL_KEYWORDS = [
    "vethernet",
    "vbox",
    "vmware",
    "docker",
    "wsl",
    "virtual",
    "zerotier",
    "tailscale",
    "vpn",
    "tap",
    "tun",
    "pseudo",
    "bluetooth",
    "hyper-v",
    "npcap",
    "default switch",
    "host-only",
]

PHYSICAL_KEYWORDS = [
    "wi-fi",
    "wifi",
    "ethernet",
    "wlan",
    "lan",
    "eth",
    "en",
]


def is_virtual_adapter(name: str) -> bool:
    lower = name.lower()
    return any(keyword in lower for keyword in VIRTUAL_KEYWORDS)


def is_physical_adapter(name: str) -> bool:
    lower = name.lower()
    return any(keyword in lower for keyword in PHYSICAL_KEYWORDS)


def get_lan_ip() -> str:
    """Returns the best LAN IPv4 address.
    Precedence:
      1. Physical active NIC (Wi-Fi / Ethernet via psutil if available)
      2. Non-virtual, non-link-local IPv4
      3. Socket UDP probe to 8.8.8.8
      4. 127.0.0.1
    """
    try:
        import psutil

        interfaces = psutil.net_if_addrs()
        stats = psutil.net_if_stats()
        candidate_physical: Optional[str] = None
        candidate_fallback: Optional[str] = None

        for name, addrs in interfaces.items():
            is_virt = is_virtual_adapter(name)
            is_phys = is_physical_adapter(name)
            is_up = stats.get(name).isup if name in stats else True

            for addr in addrs:
                if addr.family == socket.AF_INET:
                    ip = addr.address
                    if ip.startswith("127.") or ip.startswith("169.254."):
                        continue
                    if is_up:
                        if not is_virt and is_phys:
                            return ip
                        if not is_virt and not candidate_physical:
                            candidate_physical = ip
                    elif not candidate_fallback:
                        candidate_fallback = ip

        if candidate_physical:
            return candidate_physical
        if candidate_fallback:
            return candidate_fallback
    except Exception:
        pass

    # Socket connection fallback
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



def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """Check if a TCP port is currently occupied."""
    # Method 1: Connection probe (detects active listening servers)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        if s.connect_ex(("127.0.0.1", port)) == 0:
            return True
        if host not in ("127.0.0.1", "localhost", "0.0.0.0"):
            try:
                if s.connect_ex((host, port)) == 0:
                    return True
            except Exception:
                pass

    # Method 2: Exclusive bind check (detects ports reserved by other processes)
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if sys.platform == "win32":
                s.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            s.bind(("0.0.0.0", port))
            return False
    except OSError:
        return True


def find_free_port(preferred_port: int, host: str = "127.0.0.1", max_attempts: int = 50) -> int:
    """Find the first available TCP port starting from preferred_port."""
    for p in range(preferred_port, preferred_port + max_attempts):
        if not is_port_in_use(p, host):
            return p
    return preferred_port

