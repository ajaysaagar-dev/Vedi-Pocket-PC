"""mDNS discovery.

Port target: wraps the existing logic from the old `discovery.py` so
nothing in the composition root needs to import `zeroconf` directly.
We deliberately keep the public function names (`get_local_ip`,
`get_all_local_ips`, `ServiceAdvertiser`) identical to the old module
so any callers (and tests) keep working.
"""

from __future__ import annotations

import socket
import sys
import time
from typing import List

# Adapter name fragments that identify a virtual interface (WSL, Docker, VMs).
_VIRTUAL_IFACE_HINTS = (
    "vethernet", "vbox", "virtual", "docker", "wsl", "loopback",
    "hyper-v", "vmnet", "vmware", "tunnel", "npcap", "tap-", "tailscale",
)
_PHYSICAL_IFACE_HINTS = (
    ("wi-fi", "wlan", "wireless"),
    ("ethernet", "eth", "lan"),
)


def is_virtual_ip(ip: str, iface_name: str) -> bool:
    lower = iface_name.lower()
    if any(v in lower for v in _VIRTUAL_IFACE_HINTS):
        return True
    parts = ip.split(".")
    if len(parts) == 4 and parts[0] == "172":
        try:
            second_octet = int(parts[1])
            if 16 <= second_octet <= 31:
                return True
        except ValueError:
            pass
    return False


def _iface_priority(iface_name: str) -> int:
    lower = iface_name.lower()
    for prio, group in enumerate(_PHYSICAL_IFACE_HINTS):
        if any(g in lower for g in group):
            return prio
    return 99


def _is_private_lan(ip: str) -> bool:
    parts = ip.split(".")
    if len(parts) != 4:
        return False
    try:
        a, b = int(parts[0]), int(parts[1])
    except ValueError:
        return False
    if a == 10:
        return True
    if a == 172 and 16 <= b <= 31:
        return True
    if a == 192 and b == 168:
        return True
    return False


def get_all_local_ips() -> List[str]:
    lan_ips: list[tuple[int, str]] = []
    virtual_ips: list[str] = []
    try:
        import psutil

        addrs = psutil.net_if_addrs()
        stats = psutil.net_if_stats()
        for iface_name, iface_addrs in addrs.items():
            is_up = stats.get(iface_name).isup if iface_name in stats else True
            for addr in iface_addrs:
                if addr.family != socket.AF_INET:
                    continue
                ip = addr.address
                if ip.startswith("127.") or ip.startswith("169.254."):
                    continue
                if is_virtual_ip(ip, iface_name):
                    virtual_ips.append(ip)
                    continue
                prio = _iface_priority(iface_name)
                # Boost active interfaces
                if not is_up:
                    prio += 50
                lan_ips.append((prio, ip))
    except Exception:
        pass

    lan_ips.sort(key=lambda item: (
        0 if _is_private_lan(item[1]) else 1,
        item[0],
        item[1],
    ))


    if not lan_ips:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            if ip != "127.0.0.1" and not is_virtual_ip(ip, ""):
                lan_ips.append((99, ip))
        except Exception:
            pass
        finally:
            s.close()

    ordered = [ip for _, ip in lan_ips] + virtual_ips
    if not ordered:
        ordered = ["127.0.0.1"]
    return ordered


def get_local_ip() -> str:
    ips = get_all_local_ips()
    return ips[0]


class ServiceAdvertiser:
    """mDNS advertiser. Pure port — does not depend on anything else."""

    def __init__(self, port: int) -> None:
        self.port = port
        self.zeroconf = None
        self.info = None

    def start(self) -> None:
        local_ip = get_local_ip()
        hostname = socket.gethostname()

        desc = {
            "hostname": hostname,
            "os": sys.platform,
            "path": "/pair",
        }

        service_type = "_pcremote._tcp.local."
        service_name = f"{hostname} PC Remote.{service_type}"

        print(f"[DISCOVERY] Advertising mDNS service: {service_name} at {local_ip}:{self.port}")

        try:
            from zeroconf import IPVersion, ServiceInfo, Zeroconf

            self.zeroconf = Zeroconf(ip_version=IPVersion.V4Only)
            self.info = ServiceInfo(
                service_type,
                service_name,
                addresses=[socket.inet_aton(local_ip)],
                port=self.port,
                properties=desc,
            )
            self.zeroconf.register_service(self.info)
        except Exception as e:
            print(f"[DISCOVERY] Failed to start Zeroconf advertising: {e}")

    def stop(self) -> None:
        if self.zeroconf and self.info:
            print("[DISCOVERY] Stopping mDNS advertising...")
            try:
                self.zeroconf.unregister_service(self.info)
                self.zeroconf.close()
            except Exception as e:
                print(f"[DISCOVERY] Error closing Zeroconf: {e}")
            self.zeroconf = None
            self.info = None
