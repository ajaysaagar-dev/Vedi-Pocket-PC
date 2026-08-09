import React from 'react';
import { StyleSheet, Text, View, TouchableOpacity, Alert, ScrollView } from 'react-native';
import {
  Volume2,
  VolumeX,
  Volume1,
  Play,
  SkipForward,
  SkipBack,
  Lock,
  Moon,
  Power,
} from 'lucide-react-native';
import { useDeviceStore } from '../../src/store/deviceStore';
import DesktopViewport from '../../components/DesktopViewport';
import { palette, Spacing, Radius, Typography, Elevation } from '../../constants/theme-m3';

import wsClient from '../../src/data/ws/client';

export default function ControlsScreen() {
  const connectionStatus = useDeviceStore(state => state.connectionStatus);
  const activeDevice = useDeviceStore(state => state.activeDevice);

  const isConnected = connectionStatus === 'connected';

  const sendCommand = async (
    endpoint: string,
    method: string = 'POST',
    body: object | null = null
  ) => {
    if (!isConnected || !activeDevice) {
      Alert.alert('Not connected', 'Please connect to a device first.');
      return;
    }

    let httpSuccess = false;
    try {
      const serverUrl = `http://${activeDevice.ip}:${activeDevice.port || 8000}`;
      const response = await fetch(`${serverUrl}${endpoint}`, {
        method,
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${activeDevice.token}`,
        },
        body: body ? JSON.stringify(body) : null,
      });
      if (response.ok) {
        httpSuccess = true;
      }
    } catch (err) {
      console.warn(`HTTP endpoint ${endpoint} unreachable, attempting WebSocket fallback:`, err);
    }

    // Dual-dispatch / Fallback over active WebSocket connection
    const wsMap: Record<string, string> = {
      '/media/playpause': 'media_playpause',
      '/media/next': 'media_next',
      '/media/prev': 'media_prev',
      '/media/volume/up': 'volume_up',
      '/media/volume/down': 'volume_down',
      '/media/volume/mute': 'volume_mute',
      '/system/lock': 'system_lock',
      '/system/sleep': 'system_sleep',
      '/system/shutdown': 'system_shutdown',
    };

    const wsType = wsMap[endpoint];
    if (wsType) {
      wsClient.send({ type: wsType });
      httpSuccess = true;
    }

    if (!httpSuccess) {
      Alert.alert('Connection error', 'Failed to reach the PC. Ensure the agent is running.');
    }
  };

  const confirm = (action: 'lock' | 'sleep' | 'shutdown') => {
    const map = {
      lock: ['Lock PC', 'Lock the workstation? You can unlock normally.', '/system/lock', false],
      sleep: ['Sleep PC', 'Put the computer to sleep?', '/system/sleep', false],
      shutdown: [
        'Shutdown PC',
        'Shut down now? Unsaved work will be lost.',
        '/system/shutdown',
        true,
      ],
    } as const;
    const [title, msg, endpoint, destructive] = map[action];
    Alert.alert(title, msg, [
      { text: 'Cancel', style: 'cancel' },
      {
        text: title,
        style: destructive ? 'destructive' : 'default',
        onPress: () => sendCommand(endpoint),
      },
    ]);
  };

  return (
    <ScrollView style={styles.screen} contentContainerStyle={styles.scrollContent}>
      {/* Real-time Desktop Viewport Scene */}
      <DesktopViewport streamPort={8000} interactive={false} />

      {!isConnected && (
        <View style={styles.warningBanner}>
          <Text style={styles.warningText}>Not connected. Pair a PC to use controls.</Text>
        </View>
      )}

      {/* Media */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Media playback</Text>
        <View style={styles.mediaRow}>
          <IconButton
            icon={<SkipBack color={isConnected ? palette.onSurface : palette.outline} size={22} />}
            onPress={() => sendCommand('/media/prev')}
            disabled={!isConnected}
          />
          <IconButton
            icon={<Play color={palette.onPrimary} size={28} fill={palette.onPrimary} />}
            onPress={() => sendCommand('/media/playpause')}
            disabled={!isConnected}
            primary
            big
          />
          <IconButton
            icon={<SkipForward color={isConnected ? palette.onSurface : palette.outline} size={22} />}
            onPress={() => sendCommand('/media/next')}
            disabled={!isConnected}
          />
        </View>
      </View>

      {/* Volume */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Volume</Text>
        <View style={styles.volumeRow}>
          <VolumeButton
            icon={<Volume1 color={isConnected ? palette.onSurface : palette.outline} size={20} />}
            label="Down"
            onPress={() => sendCommand('/media/volume/down')}
            disabled={!isConnected}
          />
          <VolumeButton
            icon={<VolumeX color={isConnected ? palette.error : palette.outline} size={20} />}
            label="Mute"
            onPress={() => sendCommand('/media/volume/mute')}
            disabled={!isConnected}
            error
          />
          <VolumeButton
            icon={<Volume2 color={isConnected ? palette.onSurface : palette.outline} size={20} />}
            label="Up"
            onPress={() => sendCommand('/media/volume/up')}
            disabled={!isConnected}
          />
        </View>
      </View>

      {/* System */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>System actions</Text>
        <View style={styles.systemGrid}>
          <SystemButton
            icon={<Lock color={isConnected ? palette.onSurface : palette.outline} size={22} />}
            label="Lock"
            onPress={() => confirm('lock')}
            disabled={!isConnected}
          />
          <SystemButton
            icon={<Moon color={isConnected ? palette.onSurface : palette.outline} size={22} />}
            label="Sleep"
            onPress={() => confirm('sleep')}
            disabled={!isConnected}
          />
        </View>
        <TouchableOpacity
          style={[styles.destructiveBtn, !isConnected && styles.btnOff]}
          disabled={!isConnected}
          onPress={() => confirm('shutdown')}
          activeOpacity={0.85}
        >
          <Power color={palette.onError} size={20} style={{ marginRight: Spacing.xs }} />
          <Text style={[styles.destructiveBtnText, !isConnected && styles.textOff]}>
            Shutdown computer
          </Text>
        </TouchableOpacity>
      </View>
    </ScrollView>
  );
}

/* --- Reusable controls --- */
function IconButton({
  icon,
  onPress,
  disabled,
  primary,
  big,
}: {
  icon: React.ReactNode;
  onPress: () => void;
  disabled?: boolean;
  primary?: boolean;
  big?: boolean;
}) {
  return (
    <TouchableOpacity
      style={[
        styles.iconBtn,
        big && styles.iconBtnBig,
        primary && styles.iconBtnPrimary,
        disabled && styles.btnOff,
      ]}
      onPress={onPress}
      disabled={disabled}
      activeOpacity={0.85}
    >
      {icon}
    </TouchableOpacity>
  );
}

function VolumeButton({
  icon,
  label,
  onPress,
  disabled,
  error,
}: {
  icon: React.ReactNode;
  label: string;
  onPress: () => void;
  disabled?: boolean;
  error?: boolean;
}) {
  return (
    <TouchableOpacity
      style={[styles.volumeBtn, error && styles.volumeBtnError, disabled && styles.btnOff]}
      onPress={onPress}
      disabled={disabled}
      activeOpacity={0.85}
    >
      {icon}
      <Text style={[styles.volumeBtnText, error && { color: palette.error }, disabled && styles.textOff]}>
        {label}
      </Text>
    </TouchableOpacity>
  );
}

function SystemButton({
  icon,
  label,
  onPress,
  disabled,
}: {
  icon: React.ReactNode;
  label: string;
  onPress: () => void;
  disabled?: boolean;
}) {
  return (
    <TouchableOpacity
      style={[styles.systemBtn, disabled && styles.btnOff]}
      onPress={onPress}
      disabled={disabled}
      activeOpacity={0.85}
    >
      {icon}
      <Text style={[styles.systemBtnText, disabled && styles.textOff]}>{label}</Text>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: palette.background,
  },
  scrollContent: {
    padding: Spacing.md,
    gap: Spacing.md,
    paddingBottom: Spacing.xl,
  },

  warningBanner: {
    backgroundColor: palette.errorContainer,
    borderRadius: Radius.md,
    padding: Spacing.sm,
  },
  warningText: {
    ...Typography.bodyMedium,
    color: palette.onErrorContainer,
    textAlign: 'center',
  },

  card: {
    backgroundColor: palette.surfaceContainer,
    borderRadius: Radius.lg,
    padding: Spacing.md,
    ...Elevation.level1,
  },
  cardTitle: {
    ...Typography.labelMedium,
    color: palette.onSurfaceVariant,
    textTransform: 'uppercase',
    letterSpacing: 0.8,
    marginBottom: Spacing.md,
  },

  // --- Media row ---
  mediaRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: Spacing.lg,
  },
  iconBtn: {
    width: 56,
    height: 56,
    borderRadius: Radius.full,
    backgroundColor: palette.surfaceContainerHigh,
    alignItems: 'center',
    justifyContent: 'center',
  },
  iconBtnBig: {
    width: 72,
    height: 72,
    borderRadius: Radius.full,
    ...Elevation.level2,
  },
  iconBtnPrimary: {
    backgroundColor: palette.primary,
  },

  // --- Volume row ---
  volumeRow: {
    flexDirection: 'row',
    gap: Spacing.xs,
  },
  volumeBtn: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: Spacing.xs,
    height: 56,
    borderRadius: Radius.lg,
    backgroundColor: palette.surfaceContainerHigh,
  },
  volumeBtnError: {
    backgroundColor: palette.errorContainer,
  },
  volumeBtnText: {
    ...Typography.labelLarge,
    color: palette.onSurface,
  },

  // --- System grid ---
  systemGrid: {
    flexDirection: 'row',
    gap: Spacing.sm,
    marginBottom: Spacing.md,
  },
  systemBtn: {
    flex: 1,
    height: 92,
    borderRadius: Radius.lg,
    backgroundColor: palette.surfaceContainerHigh,
    alignItems: 'center',
    justifyContent: 'center',
    gap: Spacing.xs,
  },
  systemBtnText: {
    ...Typography.labelLarge,
    color: palette.onSurface,
  },

  // --- Destructive shutdown button ---
  destructiveBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: palette.error,
    paddingVertical: 14,
    borderRadius: Radius.full,
    ...Elevation.level1,
  },
  destructiveBtnText: {
    ...Typography.labelLarge,
    color: palette.onError,
  },

  // --- Disabled states ---
  btnOff: { backgroundColor: palette.surfaceContainerLowest },
  textOff: { color: palette.outline },
});
