# 📱 PC Remote — Mobile Application (Expo / React Native)

[![React Native](https://img.shields.io/badge/React_Native-0.81.5-61DAFB?style=flat-square&logo=react&logoColor=black)](https://reactnative.dev)
[![Expo](https://img.shields.io/badge/Expo-~54.0.35-000000?style=flat-square&logo=expo&logoColor=white)](https://expo.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.9+-3178C6?style=flat-square&logo=typescript&logoColor=white)](https://typescriptlang.org)

The official mobile client for **PC Remote**, built with **Expo**, **React Native**, and **Expo Router**.

> 📌 **Main Documentation**: For full system documentation, architecture diagrams, and Python agent setup, refer to the [Root README](../README.md).

---

## 🎨 App Features

- **📷 QR Code Pairing**: Auto-scans QR code from camera with fallback mDNS scanner & PIN input.
- **🖱️ Trackpad Mode**: Gesture surface for 1-finger click, 2-finger scroll, right click, and drag.
- **⌨️ Keyboard Mode**: Soft keyboard forwarding with quick shortcut bar (Ctrl+C, Ctrl+V, Alt+Tab, Win, Esc, Task Manager).
- **🔊 Controls & Media**: Tactile volume slider, media transport controls, system power management (Lock, Sleep, Shutdown).
- **📊 Status Dashboard**: Active host information, latency ping, battery & memory stats.

---

## 🚀 Getting Started

### 1. Install Dependencies

```bash
npm install
```

### 2. Start Expo Development Server

```bash
npx expo start
```

### 3. Run on Mobile Device

- Install **Expo Go** on your Android/iOS smartphone.
- Scan the QR code shown in the terminal window to open the app.
- Make sure your phone is connected to the same Wi-Fi network as the laptop running `agent/main.py`.

---

## 📁 Project Structure

```
mobile-new/
├── app/
│   ├── (tabs)/
│   │   ├── index.tsx          # Dashboard screen
│   │   ├── trackpad.tsx       # Touchpad gesture area
│   │   ├── keyboard.tsx       # Remote keyboard & hotkeys
│   │   └── controls.tsx       # Media & power controls
│   ├── pairing.tsx            # Scanner & manual IP setup
│   └── _layout.tsx            # App navigation wrapper
├── components/                # Reusable UI elements
├── hooks/                     # Custom hooks (WebSockets, device stats)
├── assets/                    # Icons and imagery
└── package.json
```
