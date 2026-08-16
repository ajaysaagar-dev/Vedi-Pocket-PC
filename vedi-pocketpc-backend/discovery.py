import socket
import sys
import time
from zeroconf import IPVersion, ServiceInfo, Zeroconf
from state import state

# Adapter name fragments that identify a virtual interface (WSL, Docker, VMs, etc.)
_VIRTUAL_IFACE_HINTS = (
    'vethernet', 'vbox', 'virtual', 'docker', 'wsl', 'loopback',
    'hyper-v', 'vmnet', 'vmware', 'tunnel', 'npcap', 'tap-', 'tailscale',
)

# Adapter name fragments that identify the kind of physical NIC we prefer.
# Order = priority: Wi-Fi first, then Ethernet, then anything else.
_PHYSICAL_IFACE_HINTS = (
    ('wi-fi', 'wlan', 'wireless'),  # priority 0
    ('ethernet', 'eth', 'lan'),     # priority 1
)


def is_virtual_ip(ip: str, iface_name: str) -> bool:
    """
    Returns True if an IP address or interface belongs to WSL, Docker, Hyper-V, or VirtualBox.
    """
    lower = iface_name.lower()
    if any(v in lower for v in _VIRTUAL_IFACE_HINTS):
        return True
    # Standard WSL2 subnet range (172.16.0.0 - 172.31.255.255)
    parts = ip.split('.')
    if len(parts) == 4 and parts[0] == '172':
        try:
            second_octet = int(parts[1])
            if 16 <= second_octet <= 31:
                return True
        except ValueError:
            pass
    return False


def _iface_priority(iface_name: str) -> int:
    """Lower = better. 99 = unknown physical NIC."""
    lower = iface_name.lower()
    for prio, group in enumerate(_PHYSICAL_IFACE_HINTS):
        if any(g in lower for g in group):
            return prio
    return 99


def _is_private_lan(ip: str) -> bool:
    """RFC1918 private ranges — IPs that other devices on a home/office LAN will actually have."""
    parts = ip.split('.')
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


def get_all_local_ips() -> list:
    """
    Returns a list of all active IPv4 addresses on this machine,
    ordered best-first:
      1. RFC1918 private IPs on physical adapters
      2. Sorted Wi-Fi > Ethernet > other
      3. Any other physical IPs
      4. Virtual adapter IPs (last resort)
      5. UDP routing fallback
    """
    lan_ips: list[tuple[int, str]] = []   # (priority, ip)
    virtual_ips: list[str] = []

    try:
        import psutil
        addrs = psutil.net_if_addrs()
        for iface_name, iface_addrs in addrs.items():
            for addr in iface_addrs:
                if addr.family != socket.AF_INET:
                    continue
                ip = addr.address
                if ip.startswith('127.'):
                    continue
                if is_virtual_ip(ip, iface_name):
                    virtual_ips.append(ip)
                    continue
                prio = _iface_priority(iface_name)
                lan_ips.append((prio, ip))
    except Exception:
        pass

    # Sort physical IPs: private-LAN + Wi-Fi > private-LAN + Ethernet > other.
    lan_ips.sort(key=lambda item: (
        0 if _is_private_lan(item[1]) else 1,
        item[0],
        item[1],
    ))

    # UDP routing fallback if psutil found nothing physical
    if not lan_ips:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
            if ip != '127.0.0.1' and not is_virtual_ip(ip, ''):
                lan_ips.append((99, ip))
        except Exception:
            pass
        finally:
            s.close()

    ordered = [ip for _, ip in lan_ips] + virtual_ips
    if not ordered:
        ordered = ['127.0.0.1']
    return ordered


def get_local_ip() -> str:
    """
    Returns the best physical LAN IP address — private RFC1918 on a Wi-Fi
    or Ethernet adapter, falling back to virtual adapters only if nothing
    physical was found.
    """
    ips = get_all_local_ips()
    return ips[0]


class ServiceAdvertiser:
    def __init__(self, port: int):
        self.port = port
        self.zeroconf = None
        self.info = None

    def start(self):
        """
        Starts advertising the FastAPI service on the local network via mDNS.
        """
        local_ip = get_local_ip()
        hostname = socket.gethostname()
        
        # Save to global state
        state.local_ip = local_ip
        state.hostname = hostname
        state.port = self.port

        desc = {
            'hostname': hostname,
            'os': sys.platform,
            'path': '/pair'
        }

        service_type = "_pcremote._tcp.local."
        service_name = f"{hostname} PC Remote.{service_type}"

        print(f"[DISCOVERY] Advertising mDNS service: {service_name} at {local_ip}:{self.port}")

        try:
            self.zeroconf = Zeroconf(ip_version=IPVersion.V4Only)
            self.info = ServiceInfo(
                service_type,
                service_name,
                addresses=[socket.inet_aton(local_ip)],
                port=self.port,
                properties=desc
            )
            self.zeroconf.register_service(self.info)
        except Exception as e:
            print(f"[DISCOVERY] Failed to start Zeroconf advertising: {e}")

    def stop(self):
        """
        Unregisters the advertised service.
        """
        if self.zeroconf and self.info:
            print("[DISCOVERY] Stopping mDNS advertising...")
            try:
                self.zeroconf.unregister_service(self.info)
                self.zeroconf.close()
            except Exception as e:
                print(f"[DISCOVERY] Error closing Zeroconf: {e}")
            self.zeroconf = None
            self.info = None
