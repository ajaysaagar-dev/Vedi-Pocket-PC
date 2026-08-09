# veddi-pocketpc-src-additions

Drop-in domain folder for the Expo mobile app.

## What's inside

```
veddi-pocketpc-src-additions/
└── domain/
    ├── entities/
    │   └── deviceInput.ts       DeviceInput discriminated union + wire serializer
    └── use-cases/
        ├── sendInput.ts         sendInput.execute(...) — single entry point
        └── controlSystem.ts     power / volume / media REST client
```

## Why a separate folder?

These files depend on `PairedDevice` from
`veddi-pocketpc/src/store/deviceStore.ts`, which lives in the Expo
app. Keeping them in a sibling folder means:

- The mobile app's existing UI components don't need to be touched
  just to pick up the use case. Import them from
  `'../domain/use-cases/sendInput'` etc.
- We don't pollute `veddi-pocketpc/src/` with code that hasn't been
  wired into the UI yet — easier to review and revert.

## How to install

After copying the folder in place:

```bash
# Inside the Expo project root (veddi-pocketpc/)
mkdir -p src/domain
cp -r ../veddi-pocketpc-src-additions/domain/* src/domain/
```

Then in your store / app root, bind the dependencies once:

```ts
import { useDeviceStore } from './src/store/deviceStore';
import { wsClient } from './src/ws/client';
import { bindWebSocketClient } from './src/domain/use-cases/sendInput';
import { bindDeviceProvider } from './src/domain/use-cases/controlSystem';

bindWebSocketClient(wsClient);
bindDeviceProvider(() => useDeviceStore.getState().activeDevice);
```

After that, any component can do:

```ts
import { sendInput } from '../domain/use-cases/sendInput';
import { controlSystem } from '../domain/use-cases/controlSystem';

sendInput.click('left');                // mouse click at cursor
controlSystem.lock();                   // lock the host PC
controlSystem.setVolume(35);            // master volume 35%
```

## Login (unchanged)

The pairing flow — POST /pair, store token in SecureStore, use it
as `Authorization: Bearer <token>` on REST and `?token=<token>` on
the WebSocket — is intentionally untouched. `pairWithHost()` in
`veddi-pocketpc/src/ws/pairing.ts` still works exactly as before.

## Compatibility

| Expo SDK | React Native | Tested |
| :--- | :--- | :--- |
| 57 | 0.86 | ✅ (matches the `veddi-pocketpc/package.json` in this repo) |

## Relationship to agent_core

These files are the **mobile-side mirror** of the Python domain in
`packages/agent-core/`. The discriminated union in `deviceInput.ts`
maps 1-to-1 onto `InputCommand`; the use cases map onto
`ControlInput` and `ControlSystem`. If you add a new command on the
backend, add a corresponding `kind` here and a wire-format mapping.
