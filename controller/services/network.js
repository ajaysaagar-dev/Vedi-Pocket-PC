/**
 * LAN IP discovery.
 *
 * Pure utility — given a list of OS network interfaces, picks the best
 * physical NIC address. Mirrors the heuristic the backend uses (Wi-Fi
 * first, then Ethernet, with virtual adapters demoted to last resort).
 */

const os = require('os');
const path = require('path');

const VIRTUAL_KEYWORDS = [
  'vethernet', 'vbox', 'vmware', 'docker', 'wsl', 'virtual', 'zerotier',
  'tailscale', 'vpn', 'tap', 'tun', 'pseudo', 'bluetooth', 'hyper-v',
  'npcap', 'default switch', 'host-only',
];

const PHYSICAL_KEYWORDS = [
  'wi-fi', 'wifi', 'ethernet', 'wlan', 'lan',
];

function isVirtual(name) {
  const lower = name.toLowerCase();
  return VIRTUAL_KEYWORDS.some((keyword) => lower.includes(keyword));
}

function isPhysical(name) {
  const lower = name.toLowerCase();
  return (
    PHYSICAL_KEYWORDS.some((keyword) => lower.includes(keyword)) ||
    lower.startsWith('eth') ||
    lower.startsWith('en')
  );
}

/**
 * Returns the best LAN IPv4 address. Same precedence as the backend:
 *   1. Known physical adapter (Wi-Fi / Ethernet)
 *   2. Any non-virtual IPv4
 *   3. Virtual adapter IPv4
 *   4. 127.0.0.1
 */
function getLanIp() {
  const interfaces = os.networkInterfaces();
  let candidatePhysicalIp = null;
  let fallbackIp = null;

  for (const name of Object.keys(interfaces)) {
    const isVirt = isVirtual(name);
    for (const net of interfaces[name]) {
      if (net.family !== 'IPv4' || net.internal) continue;

      if (!isVirt) {
        if (isPhysical(name)) return net.address;
        if (!candidatePhysicalIp) candidatePhysicalIp = net.address;
      } else if (!fallbackIp) {
        fallbackIp = net.address;
      }
    }
  }
  return candidatePhysicalIp || fallbackIp || '127.0.0.1';
}

/**
 * Build the env object we pass to every spawned child process.
 * Adds SystemRoot / ComSpec so that .cmd batch files on Windows
 * resolve correctly, and pins REACT_NATIVE_PACKAGER_HOSTNAME so
 * Expo's Metro bundler advertises the same LAN IP we do.
 */
function getSpawnEnv() {
  const sysRoot = process.env.SystemRoot || process.env.SYSTEMROOT || 'C:\\Windows';
  const comSpec = process.env.ComSpec || process.env.COMSPEC || path.join(sysRoot, 'System32', 'cmd.exe');
  const system32 = path.join(sysRoot, 'System32');

  const currentPath = process.env.PATH || process.env.Path || '';
  const extendedPath = `${system32};${sysRoot};${currentPath}`;
  const lanIp = getLanIp();

  return {
    env: {
      ...process.env,
      SystemRoot: sysRoot,
      ComSpec: comSpec,
      PATH: extendedPath,
      Path: extendedPath,
      PYTHONUNBUFFERED: '1',
      REACT_NATIVE_PACKAGER_HOSTNAME: lanIp,
    },
    comSpec,
  };
}

module.exports = { getLanIp, getSpawnEnv };
