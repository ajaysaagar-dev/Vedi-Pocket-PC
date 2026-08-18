# agent_core

Shared hexagonal-architecture domain package used by **both**
`vedi-pocketpc-backend` and `screen-stream-server`.

Layout:

```
agent_core/
├── entities/      input_command, pairing, system_status
├── ports/         input_driver, audio_driver, power_driver, token_store
├── use_cases/     control_input, control_system, pairing
└── adapters/      pyautogui_input_driver, pycaw_audio_driver,
                   win32_power_driver, win32_desktop_access,
                   memory_token_store
```

The previous design had **two near-identical servers** (the FastAPI
control agent and the screen-stream aiohttp server) each with its own
mouse / keyboard / volume / power code. Centralising that code here
means:

- One place to fix a bug or add a feature.
- The screen-stream WebSocket now requires a verified token from the
  same `TokenStore` the control agent issues, closing the previous
  auth gap.
- Domain code (`use_cases`) is testable without pyautogui / pycaw
  installed — see `tests/test_control_input.py`.

Install in editable mode during development:

```bash
pip install -e packages/agent-core
```

Run tests:

```bash
pytest packages/agent-core/tests
```

## Public surface

- `ControlInput(driver).execute(command: InputCommand) -> InputResult`
- `ControlSystem(audio, power, …).snapshot() / .set_volume() / .lock() …`
- `PairDevice(configured_pin, tokens).pair(supplied_pin) -> PairResult`
- `MemoryTokenStore()` — the default `TokenStore` implementation.
- `PyAutoGUIInputDriver()` — the default `InputDriver` (Windows).
- `PyCawAudioDriver()` — the default `AudioDriver` (Windows).
- `Win32PowerDriver()` — the default `PowerDriver` (Windows).
