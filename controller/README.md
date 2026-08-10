# VediPocketPC — Electron Controller

The desktop controller that bundles the screen-stream server, the
FastAPI backend, and the Expo dev server into a single tray-friendly
window.

## Layout

```
controller/
├── main.js                 wiring (~90 lines)
├── preload.js              contextBridge — renderer sees only `window.electronAPI`
├── services/
│   ├── network.js          LAN IP discovery + spawn env
│   ├── binaries.js         find Node / Python on the host
│   ├── process-manager.js  Expo / stream / backend lifecycle
│   ├── window.js           BrowserWindow factory
│   └── qr.js               QR code generation
└── ipc/
    └── handlers.js         ipcMain handlers
```

## Run

```bash
pnpm install
pnpm start
```

The Electron `main` entry point lives here at `controller/main.js`.
Update `package.json` (and `electron-builder`'s `files` list) to
point at the new location.

## What changed vs. the previous monolithic main.js

- The single 590-line file is now broken into 6 small modules.
- `network.js` and `binaries.js` are pure utilities — easy to unit-test.
- `process-manager.js` is the only place that calls `child_process.spawn`,
  and it exposes a small event-based API.
- IPC handlers live in one file so the renderer contract is auditable
  in a single place.

The IPC contract exposed to the renderer is unchanged
(`getServerInfo`, `startServers`, `stopServers`, `restartServers`,
`generateQR`, `openExternal`, `onPythonLog`, `onExpoLog`,
`onStatusUpdate`).
