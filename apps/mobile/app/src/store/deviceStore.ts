import { create } from 'zustand';
import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';

export interface PairedDevice {
  ip: string;
  port: number;
  token: string;
  hostname: string;
}

interface DeviceState {
  pairedDevices: PairedDevice[];
  activeDevice: PairedDevice | null;
  connectionStatus: 'disconnected' | 'connecting' | 'connected';
  
  // Actions
  loadDevices: () => Promise<void>;
  addDevice: (device: PairedDevice) => Promise<void>;
  removeDevice: (ip: string) => Promise<void>;
  setActiveDevice: (device: PairedDevice | null) => Promise<void>;
  setConnectionStatus: (status: 'disconnected' | 'connecting' | 'connected') => void;
}

const SECURE_STORE_KEY = 'pc_remote_devices';
const ACTIVE_DEVICE_KEY = 'pc_remote_active_device';

export const useDeviceStore = create<DeviceState>((set, get) => ({
  pairedDevices: [],
  activeDevice: null,
  connectionStatus: 'disconnected',

  loadDevices: async () => {
    try {
      let devicesStr = null;
      let activeStr = null;

      if (Platform.OS !== 'web') {
        devicesStr = await SecureStore.getItemAsync(SECURE_STORE_KEY);
        activeStr = await SecureStore.getItemAsync(ACTIVE_DEVICE_KEY);
      } else {
        devicesStr = localStorage.getItem(SECURE_STORE_KEY);
        activeStr = localStorage.getItem(ACTIVE_DEVICE_KEY);
      }

      const pairedDevices = devicesStr ? JSON.parse(devicesStr) : [];
      const activeDevice = activeStr ? JSON.parse(activeStr) : null;

      set({ pairedDevices, activeDevice });

      // Automatically trigger connection if an active device exists
      if (activeDevice) {
        const { wsClient } = require('../ws/client');
        wsClient.connect(activeDevice);
      }
    } catch (e) {
      console.warn("Failed to load paired devices from secure store:", e);
    }
  },

  addDevice: async (device) => {
    try {
      const { pairedDevices } = get();
      
      const filtered = pairedDevices.filter(d => d.ip !== device.ip);
      const updated = [...filtered, device];

      set({ pairedDevices: updated, activeDevice: device });

      if (Platform.OS !== 'web') {
        await SecureStore.setItemAsync(SECURE_STORE_KEY, JSON.stringify(updated));
        await SecureStore.setItemAsync(ACTIVE_DEVICE_KEY, JSON.stringify(device));
      } else {
        localStorage.setItem(SECURE_STORE_KEY, JSON.stringify(updated));
        localStorage.setItem(ACTIVE_DEVICE_KEY, JSON.stringify(device));
      }

      // Auto-connect to newly paired device
      const { wsClient } = require('../ws/client');
      wsClient.connect(device);
    } catch (e) {
      console.warn("Failed to save added device to secure store:", e);
    }
  },

  removeDevice: async (ip) => {
    try {
      const { pairedDevices, activeDevice } = get();
      const updated = pairedDevices.filter(d => d.ip !== ip);

      let nextActive = activeDevice;
      if (activeDevice && activeDevice.ip === ip) {
        // Pick the first remaining device rather than the last so the choice
        // is reproducible — the last device in the array is always the most
        // recently added (see addDevice), and switching to it after deleting
        // an unrelated active device surprised users. First-of-list is also
        // the order shown at the top of the Devices tab.
        nextActive = updated.length > 0 ? updated[0] : null;
      }

      set({ pairedDevices: updated, activeDevice: nextActive });

      if (Platform.OS !== 'web') {
        await SecureStore.setItemAsync(SECURE_STORE_KEY, JSON.stringify(updated));
        if (nextActive) {
          await SecureStore.setItemAsync(ACTIVE_DEVICE_KEY, JSON.stringify(nextActive));
        } else {
          await SecureStore.deleteItemAsync(ACTIVE_DEVICE_KEY);
        }
      } else {
        localStorage.setItem(SECURE_STORE_KEY, JSON.stringify(updated));
        if (nextActive) {
          localStorage.setItem(ACTIVE_DEVICE_KEY, JSON.stringify(nextActive));
        } else {
          localStorage.removeItem(ACTIVE_DEVICE_KEY);
        }
      }

      const { wsClient } = require('../ws/client');
      if (nextActive) {
        wsClient.connect(nextActive);
      } else {
        wsClient.disconnect();
      }
    } catch (e) {
      console.warn("Failed to remove device from secure store:", e);
    }
  },

  setActiveDevice: async (device) => {
    try {
      set({ activeDevice: device });
      if (Platform.OS !== 'web') {
        if (device) {
          await SecureStore.setItemAsync(ACTIVE_DEVICE_KEY, JSON.stringify(device));
        } else {
          await SecureStore.deleteItemAsync(ACTIVE_DEVICE_KEY);
        }
      } else {
        if (device) {
          localStorage.setItem(ACTIVE_DEVICE_KEY, JSON.stringify(device));
        } else {
          localStorage.removeItem(ACTIVE_DEVICE_KEY);
        }
      }

      const { wsClient } = require('../ws/client');
      if (device) {
        wsClient.connect(device);
      } else {
        wsClient.disconnect();
      }
    } catch (e) {
      console.warn("Failed to set active device in secure store:", e);
    }
  },

  setConnectionStatus: (status) => set({ connectionStatus: status }),
}));
