#!/usr/bin/env python3
"""
Generate complete, publication-grade PDF documentation for Vedi Pocket PC.
Uses modern HTML/CSS with print stylesheet, rendered via headless Chrome / Edge.
"""

import base64
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_HTML = REPO_ROOT / "Vedi_Pocket_PC_Documentation.html"
OUTPUT_PDF = REPO_ROOT / "Vedi_Pocket_PC_Documentation.pdf"
LOGO_PATH = REPO_ROOT / "apps" / "desktop" / "controller" / "logo.jpeg"

def get_logo_base64() -> str:
    if LOGO_PATH.is_file():
        data = LOGO_PATH.read_bytes()
        return f"data:image/jpeg;base64,{base64.b64encode(data).decode('ascii')}"
    return ""

def get_html_content(logo_data_uri: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Vedi Pocket PC — Technical Documentation</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

  @page {{
    size: A4;
    margin: 16mm 14mm 16mm 14mm;
    @bottom-right {{
      content: counter(page);
    }}
  }}

  @page :first {{
    margin: 0;
  }}

  * {{
    box-sizing: border-box;
    -webkit-print-color-adjust: exact !important;
    print-color-adjust: exact !important;
  }}

  body {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    color: #1e293b;
    background-color: #ffffff;
    line-height: 1.6;
    font-size: 13.5px;
    margin: 0;
    padding: 0;
  }}

  /* Cover Page */
  .cover-page {{
    height: 100vh;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    padding: 50px 45px 45px 45px;
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 60%, #0369a1 100%);
    color: #ffffff;
    page-break-after: always;
  }}

  .cover-header {{
    display: flex;
    align-items: center;
    gap: 20px;
  }}

  .cover-logo {{
    width: 100px;
    height: 100px;
    border-radius: 22px;
    box-shadow: 0 12px 30px rgba(0,0,0,0.5);
    border: 2px solid rgba(255,255,255,0.2);
  }}

  .cover-brand-title {{
    font-size: 28px;
    font-weight: 800;
    letter-spacing: -0.5px;
    color: #f8fafc;
  }}

  .cover-brand-sub {{
    font-size: 14px;
    color: #94a3b8;
    font-weight: 500;
  }}

  .cover-body {{
    margin: auto 0;
  }}

  .cover-title {{
    font-size: 42px;
    font-weight: 800;
    line-height: 1.15;
    letter-spacing: -1px;
    color: #ffffff;
    margin: 0 0 15px 0;
  }}

  .cover-title span {{
    color: #38bdf8;
  }}

  .cover-subtitle {{
    font-size: 17px;
    color: #cbd5e1;
    max-width: 650px;
    line-height: 1.5;
    margin-bottom: 25px;
  }}

  .cover-badges {{
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
  }}

  .badge {{
    display: inline-block;
    padding: 5px 12px;
    border-radius: 6px;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }}

  .badge-primary {{ background: rgba(56, 189, 248, 0.2); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.4); }}
  .badge-success {{ background: rgba(34, 197, 94, 0.2); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.4); }}
  .badge-dark {{ background: rgba(255, 255, 255, 0.1); color: #f1f5f9; border: 1px solid rgba(255, 255, 255, 0.15); }}

  .cover-footer {{
    display: flex;
    justify-content: space-between;
    border-top: 1px solid rgba(255,255,255,0.15);
    padding-top: 20px;
    font-size: 12px;
    color: #94a3b8;
  }}

  /* Content Styling */
  .content-container {{
    padding: 10px 10px;
  }}

  h1, h2, h3, h4 {{
    color: #0f172a;
    font-weight: 700;
    line-height: 1.3;
  }}

  h1 {{
    font-size: 24px;
    border-bottom: 2px solid #0284c7;
    padding-bottom: 6px;
    margin-top: 30px;
    margin-bottom: 14px;
    page-break-after: avoid;
  }}

  h2 {{
    font-size: 18px;
    border-bottom: 1px solid #e2e8f0;
    padding-bottom: 4px;
    margin-top: 22px;
    margin-bottom: 10px;
    color: #1e293b;
    page-break-after: avoid;
  }}

  h3 {{
    font-size: 15px;
    margin-top: 16px;
    margin-bottom: 6px;
    color: #0369a1;
    page-break-after: avoid;
  }}

  p, li {{
    color: #334155;
    margin-bottom: 8px;
  }}

  ul, ol {{
    padding-left: 20px;
    margin-top: 4px;
    margin-bottom: 10px;
  }}

  li {{
    margin-bottom: 4px;
  }}

  /* Code & Blocks */
  code {{
    font-family: 'JetBrains Mono', Consolas, Monaco, monospace;
    font-size: 11.5px;
    background-color: #f1f5f9;
    color: #0f172a;
    padding: 2px 5px;
    border-radius: 4px;
    border: 1px solid #e2e8f0;
  }}

  pre {{
    font-family: 'JetBrains Mono', Consolas, Monaco, monospace;
    font-size: 11px;
    background-color: #0f172a;
    color: #f8fafc;
    padding: 12px 14px;
    border-radius: 8px;
    overflow-x: auto;
    line-height: 1.45;
    margin: 10px 0;
    page-break-inside: avoid;
  }}

  pre code {{
    background: transparent;
    color: inherit;
    padding: 0;
    border: none;
  }}

  /* Tables */
  table {{
    width: 100%;
    border-collapse: collapse;
    margin: 12px 0;
    font-size: 12px;
    page-break-inside: avoid;
  }}

  th, td {{
    padding: 8px 10px;
    text-align: left;
    border-bottom: 1px solid #e2e8f0;
  }}

  th {{
    background-color: #f8fafc;
    color: #0f172a;
    font-weight: 600;
    border-top: 1px solid #cbd5e1;
    border-bottom: 2px solid #cbd5e1;
  }}

  tr:nth-child(even) td {{
    background-color: #f8fafc;
  }}

  /* Callout Boxes */
  .callout {{
    padding: 12px 16px;
    border-radius: 8px;
    margin: 12px 0;
    font-size: 12.5px;
    page-break-inside: avoid;
  }}

  .callout-info {{
    background-color: #f0f9ff;
    border-left: 4px solid #0284c7;
    color: #0369a1;
  }}

  .callout-success {{
    background-color: #f0fdf4;
    border-left: 4px solid #16a34a;
    color: #15803d;
  }}

  .callout-warning {{
    background-color: #fffbeb;
    border-left: 4px solid #f59e0b;
    color: #b45309;
  }}

  .callout-title {{
    font-weight: 700;
    margin-bottom: 3px;
    display: flex;
    align-items: center;
    gap: 6px;
  }}

  /* Architecture Box / Diagrams */
  .diagram-box {{
    background: #f8fafc;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    padding: 12px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 10.5px;
    line-height: 1.35;
    color: #0f172a;
    margin: 12px 0;
    page-break-inside: avoid;
    white-space: pre;
  }}

  .toc {{
    background-color: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 16px 20px;
    margin-bottom: 25px;
    page-break-after: always;
  }}

  .toc-title {{
    font-size: 16px;
    font-weight: 700;
    color: #0f172a;
    margin-bottom: 12px;
    border-bottom: 1px solid #cbd5e1;
    padding-bottom: 6px;
  }}

  .toc-list {{
    list-style-type: none;
    padding-left: 0;
    margin: 0;
    columns: 2;
    column-gap: 24px;
  }}

  .toc-list li {{
    margin-bottom: 6px;
    font-size: 12px;
  }}

  .toc-list a {{
    color: #0284c7;
    text-decoration: none;
    font-weight: 500;
  }}

  .page-break {{
    page-break-before: always;
  }}

  .avoid-break {{
    page-break-inside: avoid;
  }}

  .footer-note {{
    margin-top: 30px;
    padding-top: 10px;
    border-top: 1px solid #e2e8f0;
    font-size: 11px;
    color: #94a3b8;
    text-align: center;
  }}
</style>
</head>
<body>

<!-- COVER PAGE -->
<div class="cover-page">
  <div class="cover-header">
    <img src="{logo_data_uri}" class="cover-logo" alt="Logo">
    <div>
      <div class="cover-brand-title">Vedi Pocket PC</div>
      <div class="cover-brand-sub">Offline Zero-Latency PC Control & Mirror Suite</div>
    </div>
  </div>

  <div class="cover-body">
    <div class="cover-title">Full System Architecture & <span>Technical Reference</span></div>
    <div class="cover-subtitle">
      A comprehensive deep-dive into the protocols, binary streaming engine, Clean Architecture core, CustomTkinter desktop manager, and React Native mobile client.
    </div>

    <div class="cover-badges">
      <span class="badge badge-primary">FastAPI & Python 3.10+</span>
      <span class="badge badge-primary">React Native Expo</span>
      <span class="badge badge-success">100% Offline LAN</span>
      <span class="badge badge-dark">DXGI High-FPS Screen Stream</span>
      <span class="badge badge-dark">Zero-Trust PIN Pairing</span>
      <span class="badge badge-dark">Windows 10 / 11</span>
    </div>
  </div>

  <div class="cover-footer">
    <div>Author: Ajay Saagar & Vedi Engineering</div>
    <div>License: MIT Open Source</div>
    <div>Date: August 2026 • Version 1.0.0</div>
  </div>
</div>

<!-- CONTENT -->
<div class="content-container">

  <!-- TABLE OF CONTENTS -->
  <div class="toc">
    <div class="toc-title">Table of Contents</div>
    <ul class="toc-list">
      <li><strong>1.</strong> <a href="#sec-1">Executive Summary & Overview</a></li>
      <li><strong>2.</strong> <a href="#sec-2">System Topology & Architecture</a></li>
      <li><strong>3.</strong> <a href="#sec-3">Network Ports & Protocol Matrix</a></li>
      <li><strong>4.</strong> <a href="#sec-4">Authentication & Easy-Connect Flow</a></li>
      <li><strong>5.</strong> <a href="#sec-5">DXGI Screen Stream Engine & Framing</a></li>
      <li><strong>6.</strong> <a href="#sec-6">Input Event Dispatch & Wire Schemas</a></li>
      <li><strong>7.</strong> <a href="#sec-7">Complete REST API Specification</a></li>
      <li><strong>8.</strong> <a href="#sec-8">Desktop Controller & Process Manager</a></li>
      <li><strong>9.</strong> <a href="#sec-9">Mobile Client Application Engine</a></li>
      <li><strong>10.</strong> <a href="#sec-10">Repository & File Layout</a></li>
      <li><strong>11.</strong> <a href="#sec-11">Configuration (.env & config.json)</a></li>
      <li><strong>12.</strong> <a href="#sec-12">Build, Packaging & Distribution</a></li>
      <li><strong>13.</strong> <a href="#sec-13">Diagnostics & Troubleshooting</a></li>
      <li><strong>14.</strong> <a href="#sec-14">Test Suite & Quality Verification</a></li>
    </ul>
  </div>

  <!-- SECTION 1 -->
  <h1 id="sec-1">1. Executive Summary & Overview</h1>
  <p>
    <strong>Vedi Pocket PC</strong> is an ultra-fast, offline PC remote control and display mirroring application suite designed for Windows 10 and 11. It transforms any Android or iOS smartphone into an interactive wireless trackpad, physical keyboard simulator, multimedia controller, and live screen mirror over local Wi-Fi.
  </p>

  <div class="callout callout-info">
    <div class="callout-title">Key Architectural Differentiators</div>
    <ul>
      <li><strong>Zero Cloud Relays:</strong> 100% peer-to-peer over local network. No external server, internet access, or third-party telemetry.</li>
      <li><strong>Sub-50ms Input & Frame Latency:</strong> Direct binary WebSocket streaming with DXGI desktop scraping and latest-wins frame queue dropping.</li>
      <li><strong>Zero-Trust Dynamic Pairing:</strong> Secure 4-digit PIN generated per session, encoded into an instant camera QR code.</li>
      <li><strong>Clean Architecture Foundation:</strong> Domain core decoupled into strict Entities, Ports, Adapters, and Use Cases inside <code>agent_core</code>.</li>
    </ul>
  </div>

  <!-- SECTION 2 -->
  <h1 id="sec-2">2. System Topology & Architecture</h1>
  <p>
    The desktop suite operates as a single executable hosting three core subsystems via multi-threading and an embedded <code>aiohttp</code>/<code>FastAPI</code> runtime managed by <code>ProcessManager</code>:
  </p>

  <div class="diagram-box">┌────────────────────────────────────────────── Windows PC ──────────────────────────────────────────────┐
│  Vedi Pocket PC Desktop Controller (Python 3.10+)                                                     │
│  ┌──────────────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │ ProcessManager (Single-Instance Socket Lock on 127.0.0.1)                                        │  │
│  │   ├── CustomTkinter GUI & Controller Server (aiohttp) ──────► http://127.0.0.1:8090              │  │
│  │   ├── Screen Stream Server (aiohttp WS)               ──────► ws://0.0.0.0:8080/ws (JPEG Stream) │  │
│  │   └── Pairing & Remote Control Agent (FastAPI)        ──────► http://0.0.0.0:8000 (REST & Touch) │  │
│  └──────────────────────────────────┬───────────────────────────────────────────────────────────────┘  │
│                                     │ Shared Domain Layer (packages/core/agent_core)                    │
│                                     ▼                                                                  │
│            ┌─────────────────────────────────────────────────────────────────┐                         │
│            │ • PyAutoGUIInputDriver       • PyCawAudioDriver (Core Audio)   │                         │
│            │ • Win32PowerDriver           • MemoryTokenStore (Disk Token)   │                         │
│            └─────────────────────────────────────────────────────────────────┘                         │
└─────────────────────────────────────────────▲──────────────────────────────────────────────────────────┘
                                              │ Local Wi-Fi (LAN)
                                              ▼
┌──────────────────────────────────────── Mobile Application ───────────────────────────────────────────┐
│  React Native / Expo Client (Android Release APK / iOS)                                                │
│  ├── QR Scanner & Pairing UI    ──► Discovers IP, Port, and PIN; mints session tokens                 │
│  ├── Interactive Trackpad       ──► Multitouch 60FPS pan, tap, double-click, 2-finger scroll           │
│  ├── Screen Mirror Viewport     ──► Unpacks STRM binary JPEG stream; touch-to-coordinate mapping       │
│  └── Remote Keyboard & Controls ──► Modifiers (Ctrl/Alt/Shift), volume slider, power actions           │
└────────────────────────────────────────────────────────────────────────────────────────────────────────┘</div>

  <!-- SECTION 3 -->
  <h1 id="sec-3">3. Network Ports & Protocol Matrix</h1>
  <table>
    <thead>
      <tr>
        <th>Port</th>
        <th>Protocol</th>
        <th>Component</th>
        <th>Primary Responsibility</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td><strong>8090</strong></td>
        <td>HTTP / WS</td>
        <td>Desktop Controller</td>
        <td>CustomTkinter backend, management web dashboard, live log fan-out.</td>
      </tr>
      <tr>
        <td><strong>8080</strong></td>
        <td>WebSocket / HTTP</td>
        <td>Screen Streamer</td>
        <td>DXGI binary JPEG frame streaming, interactive viewport touch dispatch.</td>
      </tr>
      <tr>
        <td><strong>8000</strong></td>
        <td>HTTP REST / WS</td>
        <td>FastAPI Agent</td>
        <td>Zero-trust PIN pairing, system audio, power states, trackpad WebSocket.</td>
      </tr>
      <tr>
        <td><strong>8088</strong></td>
        <td>HTTP / WS</td>
        <td>Metro Dev Server</td>
        <td>Expo mobile bundle reloader (developer mode only).</td>
      </tr>
      <tr>
        <td><strong>5353</strong></td>
        <td>UDP (mDNS)</td>
        <td>ZeroConf Advertiser</td>
        <td>Broadcasts <code>_vedi-pocketpc._tcp.local.</code> for automatic LAN discovery.</td>
      </tr>
    </tbody>
  </table>

  <!-- SECTION 4 -->
  <div class="page-break"></div>
  <h1 id="sec-4">4. Authentication & Easy-Connect Flow</h1>
  <p>
    The pairing mechanism enforces local network security without passwords or cloud logins:
  </p>
  <ol>
    <li><strong>PIN Generation:</strong> On startup, the control agent generates a random 4-digit PIN (<code>0000..9999</code>).</li>
    <li><strong>QR Code Presentation:</strong> The desktop UI renders a QR code encoding <code>&lt;LAN_IP&gt;:&lt;PORT&gt;:&lt;PIN&gt;</code> (e.g. <code>192.168.1.100:8000:4821</code>).</li>
    <li><strong>Exchange (<code>POST /pair</code>):</strong> The mobile client sends <code>{{"pin": "4821"}}</code>. If accepted, the agent mints an ephemeral session token plus a persistent <code>common_token</code>.</li>
    <li><strong>Persistent Reconnect ("Easy-Connect"):</strong> The agent persists <code>common_token</code> to <code>%LOCALAPPDATA%\\PCRemoteAgent\\common_token.txt</code>. The mobile app stores this token in <code>AsyncStorage</code> and reconnects automatically without re-entering the PIN.</li>
  </ol>

  <!-- SECTION 5 -->
  <h1 id="sec-5">5. DXGI Screen Stream Engine & Framing</h1>
  <p>
    Screen streaming runs over <code>ws://&lt;IP&gt;:8080/ws</code> using an optimized binary frame protocol.
  </p>

  <h3>Binary Framing Format</h3>
  <div class="diagram-box">┌─────────────────────────┬─────────────────────────┬─────────────────────────┐
│ Magic Bytes (4 bytes)   │ Payload Length (4 bytes)│ Raw JPEG Image Bytes    │
│ "STRM" (0x53 54 52 4D)  │ uint32 Big-Endian       │ Variable Size (bytes)   │
└─────────────────────────┴─────────────────────────┴─────────────────────────┘</div>

  <p>
    <strong>Zero-Latency Queueing:</strong> The server writer uses a bounded queue of size 1 with a "latest-wins" discard policy. If the network interface cannot flush a frame in time, the stale frame is dropped immediately so the mobile screen never lags.
  </p>

  <!-- SECTION 6 -->
  <h1 id="sec-6">6. Input Event Dispatch & Wire Schemas</h1>
  <p>
    All user gestures received over WebSockets (ports 8000 and 8080) are parsed by <code>dispatch_table.py</code> and executed via <code>ControlInput</code>:
  </p>

  <table>
    <thead>
      <tr>
        <th>Event Type</th>
        <th>Payload Parameters</th>
        <th>Action Executed on Windows PC</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td><code>mouse_move</code></td>
        <td><code>dx, dy, sensitivity</code></td>
        <td>Relative cursor move (PyAutoGUI <code>moveRel</code>)</td>
      </tr>
      <tr>
        <td><code>mouse_move_to</code></td>
        <td><code>x, y, duration</code></td>
        <td>Absolute cursor placement (PyAutoGUI <code>moveTo</code>)</td>
      </tr>
      <tr>
        <td><code>mouse_click</code></td>
        <td><code>button, clicks, x?, y?</code></td>
        <td>Left / right / middle click simulation</td>
      </tr>
      <tr>
        <td><code>mouse_down</code> / <code>up</code></td>
        <td><code>button, x?, y?</code></td>
        <td>Physical mouse button hold / release (click-and-drag)</td>
      </tr>
      <tr>
        <td><code>scroll</code></td>
        <td><code>dy, dx?</code></td>
        <td>Mouse wheel vertical and horizontal scroll</td>
      </tr>
      <tr>
        <td><code>keyboard_type</code></td>
        <td><code>text</code></td>
        <td>Types a string sequence into active window</td>
      </tr>
      <tr>
        <td><code>key_press</code></td>
        <td><code>key</code> (e.g. <code>"enter"</code>, <code>"backspace"</code>)</td>
        <td>Single key stroke press</td>
      </tr>
      <tr>
        <td><code>hotkey</code></td>
        <td><code>keys: ["ctrl", "alt", "del"]</code></td>
        <td>Simultaneous key combo execution</td>
      </tr>
      <tr>
        <td><code>ping</code></td>
        <td><code>t?: number</code></td>
        <td>Round-trip latency probe (replies with <code>pong</code>)</td>
      </tr>
    </tbody>
  </table>

  <!-- SECTION 7 -->
  <div class="page-break"></div>
  <h1 id="sec-7">7. Complete REST API Specification</h1>
  <p>All authenticated endpoints require header: <code>Authorization: Bearer &lt;token&gt;</code>.</p>

  <h3>Pairing & System Endpoints</h3>
  <ul>
    <li><strong><code>GET /health</code></strong> (Public) &rarr; <code>{{ "status": "ok", "agent_version": "1.0.0", "hostname": "VEDI-PC", "uptime_seconds": 3600 }}</code></li>
    <li><strong><code>POST /pair</code></strong> (Public) &rarr; Body: <code>{{ "pin": "1234" }}</code> &rarr; <code>{{ "status": "success", "token": "...", "common_token": "..." }}</code></li>
    <li><strong><code>GET /status</code></strong> (Auth) &rarr; <code>{{ "os": "Windows", "os_release": "11", "volume": 65, "battery": {{ "percent": 98, "plugged": true }} }}</code></li>
    <li><strong><code>POST /system/lock</code></strong> (Auth) &rarr; Locks Windows workstation.</li>
    <li><strong><code>POST /system/sleep</code></strong> (Auth) &rarr; Puts Windows into low-power sleep.</li>
    <li><strong><code>POST /system/shutdown</code></strong> (Auth) &rarr; Initiates timed Windows shutdown.</li>
  </ul>

  <h3>Audio & Media Control Endpoints (<code>/media/*</code>)</h3>
  <ul>
    <li><strong><code>POST /media/volume</code></strong> &rarr; Body: <code>{{ "level": 75 }}</code> &rarr; Direct Core Audio <code>IAudioEndpointVolume</code> adjustment.</li>
    <li><strong><code>POST /media/volume/up</code></strong> & <strong><code>/media/volume/down</code></strong> &rarr; Step volume adjustment.</li>
    <li><strong><code>POST /media/volume/mute</code></strong> &rarr; Toggle master mute.</li>
    <li><strong><code>POST /media/playpause</code></strong>, <strong><code>/next</code></strong>, <strong><code>/prev</code></strong> &rarr; Global Windows media keys.</li>
    <li><strong><code>POST /media/type</code></strong> &rarr; Body: <code>{{ "text": "sample" }}</code> &rarr; Types text into focused window.</li>
  </ul>

  <!-- SECTION 8 -->
  <h1 id="sec-8">8. Desktop Controller & Process Manager</h1>
  <p>
    Located in <code>apps/desktop/controller/</code>, the desktop controller is built with CustomTkinter and Python:
  </p>
  <ul>
    <li><strong>CustomTkinter GUI (<code>app.py</code>):</strong> Dark-themed native window displaying pairing QR codes, live IP/port stats, Metro server status, and real-time diagnostic log stream.</li>
    <li><strong>In-Process Thread Architecture:</strong> Eliminates sub-processes by running the FastAPI agent and Screen Streamer on background daemon threads managed by <code>process_manager.py</code>.</li>
    <li><strong>Single-Instance Enforcement:</strong> Binds a loopback socket on <code>127.0.0.1</code> to prevent duplicate instances.</li>
    <li><strong>Network Adapter Filter (<code>network.py</code>):</strong> Automatically filters out virtual adapters (Docker, WSL, VMware, Hyper-V) and prioritizes active physical Wi-Fi/Ethernet adapters.</li>
    <li><strong>Path Matrix (<code>paths.py</code>):</strong> Seamlessly handles development source trees, PyInstaller <code>onedir</code> bundles, and PyInstaller <code>onefile</code> extraction environments.</li>
  </ul>

  <!-- SECTION 9 -->
  <h1 id="sec-9">9. Mobile Client Application Engine</h1>
  <p>
    Located in <code>apps/mobile/app/</code>, the mobile client is built on React Native and Expo:
  </p>
  <ul>
    <li><strong>Multitouch Trackpad (<code>trackpad.tsx</code>):</strong> Uses <code>react-native-gesture-handler</code> and <code>react-native-reanimated</code> for 60FPS fluid cursor motion, 1-finger left click, 2-finger right click, double-click, and 2-finger scroll.</li>
    <li><strong>Screen Viewport (<code>DesktopViewport.tsx</code>):</strong> Unpacks binary <code>STRM</code> WebSocket frames into memory and renders with <code>expo-image</code>. Supports touch coordinate translation for direct desktop screen interaction, live latency meter, and screenshot capture.</li>
    <li><strong>Remote Keyboard (<code>keyboard.tsx</code>):</strong> Full on-screen keyboard with modifier toggles (<code>Ctrl</code>, <code>Alt</code>, <code>Shift</code>, <code>Win</code>) and common hotkey macros.</li>
    <li><strong>Persistent State (<code>deviceStore.ts</code>):</strong> Zustand store backed by <code>AsyncStorage</code> for cached connection tokens and paired device history.</li>
  </ul>

  <!-- SECTION 10 -->
  <div class="page-break"></div>
  <h1 id="sec-10">10. Repository & File Layout</h1>
  <pre><code>Vedi-Pocket-PC/
├── .env                                 # Local development environment configuration
├── requirements.txt                     # Master Python dependencies list
│
├── apps/
│   ├── desktop/controller/              # CustomTkinter Desktop GUI & Process Manager
│   │   ├── app.py                       # Primary execution entry point
│   │   ├── process_manager.py           # Thread-based in-process runner & socket lock
│   │   ├── config.py / paths.py         # Config loader & multi-tier path resolver
│   │   ├── network.py / logging_setup.py# NIC discovery & rotating file logs
│   │   └── installer.iss / *.spec       # Inno Setup and PyInstaller build specs
│   │
│   ├── agent/server/                    # FastAPI Remote Control & Pairing Agent
│   │   └── main.py                      # FastAPI composition root & ZeroConf advertiser
│   │
│   ├── streamer/server/                 # High-Speed Screen Streamer Engine
│   │   ├── main.py                      # aiohttp streaming composition root
│   │   ├── domain/capture.py            # DXGI frame capture via mss & PIL
│   │   └── presentation/ws_router.py    # Binary frame broadcaster & touch handler
│   │
│   └── mobile/app/                      # React Native / Expo Mobile Client
│       ├── app/(tabs)/                  # trackpad.tsx, screen.tsx, keyboard.tsx, controls.tsx
│       ├── components/DesktopViewport.tsx# Binary frame unpacker & touch coordinate mapper
│       └── src/ws/                      # client.ts (WS client) & pairing.ts (API client)
│
├── packages/
│   ├── core/agent_core/                 # Shared domain logic, entities, ports, adapters
│   └── protocol/                        # Shared HTTP routers & WS dispatch table
│
├── infrastructure/                      # Centralized logging & mDNS network tools
├── scripts/                             # setup.bat, start.bat, build.bat, Uninstall.bat
└── tests/                               # Unit test suite for pairing, input, and controllers</code></pre>

  <!-- SECTION 11 -->
  <h1 id="sec-11">11. Configuration (.env & config.json)</h1>
  <table>
    <thead>
      <tr>
        <th>Variable</th>
        <th>Default</th>
        <th>Description</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td><code>STREAM_HOST</code></td>
        <td><code>0.0.0.0</code></td>
        <td>Bind interface for screen streamer WebSocket.</td>
      </tr>
      <tr>
        <td><code>STREAM_PORT</code></td>
        <td><code>8080</code></td>
        <td>TCP port for high-speed screen streaming.</td>
      </tr>
      <tr>
        <td><code>STREAM_FPS</code></td>
        <td><code>30</code></td>
        <td>Target screen capture frame rate (10–60 FPS).</td>
      </tr>
      <tr>
        <td><code>STREAM_JPEG_QUALITY</code></td>
        <td><code>50</code></td>
        <td>JPEG image compression factor (10–100).</td>
      </tr>
      <tr>
        <td><code>STREAM_MAX_WIDTH</code></td>
        <td><code>1280</code></td>
        <td>Maximum streamed frame width in pixels.</td>
      </tr>
      <tr>
        <td><code>STREAM_MAX_HEIGHT</code></td>
        <td><code>720</code></td>
        <td>Maximum streamed frame height in pixels.</td>
      </tr>
      <tr>
        <td><code>BACKEND_PORT</code></td>
        <td><code>8000</code></td>
        <td>FastAPI pairing and control agent REST port.</td>
      </tr>
      <tr>
        <td><code>CONTROLLER_PORT</code></td>
        <td><code>8090</code></td>
        <td>Desktop management HTTP server port.</td>
      </tr>
      <tr>
        <td><code>EXPO_ENABLED</code></td>
        <td><code>1</code></td>
        <td>1 = Launch Metro dev server, 0 = Standalone mode.</td>
      </tr>
    </tbody>
  </table>

  <!-- SECTION 12 -->
  <h1 id="sec-12">12. Build, Packaging & Distribution</h1>
  <div class="callout callout-success">
    <div class="callout-title">Master Build Commands</div>
    <ul>
      <li><strong>Developer Setup:</strong> Run <code>.\\scripts\\setup.bat</code> to install Python wheels and npm dependencies.</li>
      <li><strong>Run from Source:</strong> Run <code>.\\scripts\\start.bat</code> to boot the CustomTkinter GUI and all services.</li>
      <li><strong>Build Windows Standalone EXE:</strong> Run <code>.\\scripts\\build.bat exe</code> (compiles via PyInstaller & Inno Setup).</li>
      <li><strong>Build Android APK:</strong> Run <code>npm run build:apk</code> in <code>apps/mobile/app/</code> or use EAS Build.</li>
    </ul>
  </div>

  <!-- SECTION 13 & 14 -->
  <div class="page-break"></div>
  <h1 id="sec-13">13. Diagnostics & Troubleshooting</h1>
  <table>
    <thead>
      <tr>
        <th>Observed Issue</th>
        <th>Root Cause</th>
        <th>Recommended Resolution</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td>Mobile app cannot reach PC</td>
        <td>Windows Defender Firewall blocking ports 8000/8080/8090</td>
        <td>Run <code>scripts/start.bat</code> once as Administrator to register inbound firewall rules.</td>
      </tr>
      <tr>
        <td>QR Code shows 172.x / 127.0.0.1</td>
        <td>Virtual NIC (Docker / WSL / Hyper-V) prioritised</td>
        <td>Disable unused virtual adapters in Windows Network Connections, or set <code>BACKEND_HOST</code>.</td>
      </tr>
      <tr>
        <td>Screen stream is black</td>
        <td>Frame buffer truncation or display DPI scaling mismatch</td>
        <td>Update graphics drivers; adjust <code>STREAM_MAX_WIDTH</code> & <code>STREAM_MAX_HEIGHT</code> in <code>.env</code>.</td>
      </tr>
      <tr>
        <td>Port in use conflict</td>
        <td>Stale python process holding port</td>
        <td>Kill lingering processes with <code>taskkill /F /IM python.exe</code>.</td>
      </tr>
    </tbody>
  </table>

  <h1 id="sec-14">14. Test Suite & Quality Verification</h1>
  <p>
    The repository includes a pytest unit test suite covering domain entities, pairing logic, and mock input drivers:
  </p>
  <pre><code># Execute all unit tests
pytest tests/unit/

# Target specific modules
pytest tests/unit/core/test_pairing.py
pytest tests/unit/core/test_control_input.py
pytest tests/unit/core/test_controller.py</code></pre>

  <div class="footer-note">
    Vedi Pocket PC Documentation • Generated for Ajay Saagar • Confidential & Proprietary Open Source Suite
  </div>

</div>

</body>
</html>
"""

def generate_pdf():
    print(f"[1/3] Generating documentation HTML...")
    logo_data_uri = get_logo_base64()
    html_content = get_html_content(logo_data_uri)
    OUTPUT_HTML.write_text(html_content, encoding="utf-8")
    print(f"      [OK] HTML written to: {OUTPUT_HTML}")

    print(f"[2/3] Locating Headless Browser (Chrome / Edge)...")
    browser_candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    browser_exe = next((p for p in browser_candidates if os.path.exists(p)), None)
    if not browser_exe:
        print("[ERROR] Neither Chrome nor Edge could be found on this system.")
        sys.exit(1)
    print(f"      [OK] Using browser: {browser_exe}")

    print(f"[3/3] Compiling PDF via Headless Print...")
    cmd = [
        browser_exe,
        "--headless",
        "--disable-gpu",
        "--no-pdf-header-footer",
        "--run-all-compositor-stages-before-draw",
        f"--print-to-pdf={OUTPUT_PDF}",
        str(OUTPUT_HTML),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"[ERROR] Browser headless print failed with code {res.returncode}:")
        print(res.stderr)
        sys.exit(res.returncode)

    if OUTPUT_PDF.is_file():
        size_kb = OUTPUT_PDF.stat().st_size / 1024
        print(f"============================================================")
        print(f" [SUCCESS] PDF Generated Successfully!")
        print(f" Path: {OUTPUT_PDF}")
        print(f" Size: {size_kb:.1f} KB")
        print(f"============================================================")
    else:
        print("[ERROR] PDF was not generated.")
        sys.exit(1)

if __name__ == "__main__":
    generate_pdf()
