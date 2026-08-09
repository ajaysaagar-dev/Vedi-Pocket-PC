/**
 * Binary resolution — finds Node and Python executables on the host.
 *
 * Tries `where node` / `which node` first, then falls back to
 * well-known install locations on Windows. Pure / synchronous so it
 * can run at startup without complicating the boot sequence.
 */
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

function getNodePath() {
  const isWin = process.platform === 'win32';
  try {
    const cmd = isWin ? 'where node' : 'which node';
    const output = execSync(cmd, { encoding: 'utf8' }).trim();
    const firstLine = output.split(/[\r\n]+/)[0];
    if (firstLine && fs.existsSync(firstLine)) {
      return firstLine;
    }
  } catch (e) { /* fall through */ }

  if (isWin) {
    const pfNode = path.join(process.env['ProgramFiles'] || 'C:\\Program Files', 'nodejs', 'node.exe');
    if (fs.existsSync(pfNode)) return pfNode;
    const pf86Node = path.join(process.env['ProgramFiles(x86)'] || 'C:\\Program Files (x86)', 'nodejs', 'node.exe');
    if (fs.existsSync(pf86Node)) return pf86Node;
  }
  return 'node';
}

function getPythonPath() {
  const isWin = process.platform === 'win32';
  try {
    const cmd = isWin ? 'where python' : 'which python3';
    const output = execSync(cmd, { encoding: 'utf8' }).trim();
    const firstLine = output.split(/[\r\n]+/)[0];
    if (firstLine && fs.existsSync(firstLine) && !firstLine.includes('WindowsApps')) {
      return firstLine;
    }
  } catch (e) { /* fall through */ }

  if (isWin) {
    const localAppData = process.env.LOCALAPPDATA || '';
    if (localAppData) {
      const pyDir = path.join(localAppData, 'Programs', 'Python');
      if (fs.existsSync(pyDir)) {
        const subdirs = fs.readdirSync(pyDir);
        for (const dir of subdirs) {
          const exe = path.join(pyDir, dir, 'python.exe');
          if (fs.existsSync(exe)) return exe;
        }
      }
    }
    return 'python';
  }
  return 'python3';
}

function findBinaries() {
  return {
    node: getNodePath(),
    python: getPythonPath(),
  };
}

module.exports = { findBinaries, getNodePath, getPythonPath };
