# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

# Collect dependencies required by backend & stream sub-services
fastapi_datas, fastapi_binaries, fastapi_hiddenimports = collect_all('fastapi')
starlette_datas, starlette_binaries, starlette_hiddenimports = collect_all('starlette')
uvicorn_datas, uvicorn_binaries, uvicorn_hiddenimports = collect_all('uvicorn')
aiohttp_datas, aiohttp_binaries, aiohttp_hiddenimports = collect_all('aiohttp')
zeroconf_datas, zeroconf_binaries, zeroconf_hiddenimports = collect_all('zeroconf')
pydantic_datas, pydantic_binaries, pydantic_hiddenimports = collect_all('pydantic')
websockets_datas, websockets_binaries, websockets_hiddenimports = collect_all('websockets')
wsproto_datas, wsproto_binaries, wsproto_hiddenimports = collect_all('wsproto')

all_datas = [
    ('Screen-Stream-Server', 'Screen-Stream-Server'),
    ('Vedi-PocketPC-Backend', 'Vedi-PocketPC-Backend'),
    ('Vedi-PocketPC-Mobile', 'Vedi-PocketPC-Mobile'),
    ('Packages', 'Packages'),
] + fastapi_datas + starlette_datas + uvicorn_datas + aiohttp_datas + zeroconf_datas + pydantic_datas + websockets_datas + wsproto_datas

all_binaries = fastapi_binaries + starlette_binaries + uvicorn_binaries + aiohttp_binaries + zeroconf_binaries + pydantic_binaries + websockets_binaries + wsproto_binaries

all_hiddenimports = list(set([
    'mss',
    'pyautogui',
    'pycaw',
    'comtypes',
    'qrcode',
    'psutil',
    'agent_core',
    'pystray',
    'bottle',
    'webview',
    'PIL',
] + fastapi_hiddenimports + starlette_hiddenimports + uvicorn_hiddenimports + aiohttp_hiddenimports + zeroconf_hiddenimports + pydantic_hiddenimports + websockets_hiddenimports + wsproto_hiddenimports))

a = Analysis(
    ['Controller/app.py'],
    pathex=[
        'Packages/agent-core',
        'Vedi-PocketPC-Backend',
        'Screen-Stream-Server',
    ],
    binaries=all_binaries,
    datas=all_datas,
    hiddenimports=all_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Vedi Pocket PC',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['Vedi-PocketPC-Mobile/assets/images/icon.png'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Vedi Pocket PC',
)

