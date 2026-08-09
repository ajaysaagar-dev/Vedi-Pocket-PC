import React, { useState, useEffect } from 'react';
import { StyleSheet, Text, View, TouchableOpacity, ActivityIndicator, Alert } from 'react-native';
import { useRouter } from 'expo-router';
import { CameraView, useCameraPermissions } from 'expo-camera';
import { StatusBar } from 'expo-status-bar';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { X, Camera, RefreshCcw } from 'lucide-react-native';
import { useDeviceStore } from '../src/store/deviceStore';
import { pairWithHost, describePairError } from '../src/data/ws/pairing';
import { palette, Spacing, Radius, Typography, Elevation } from '../constants/theme-m3';

export default function PairingScreen() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const [permission, requestPermission] = useCameraPermissions();
  const [scanned, setScanned] = useState(false);
  const [pairingInProgress, setPairingInProgress] = useState(false);
  const addDevice = useDeviceStore(state => state.addDevice);

  useEffect(() => {
    if (!permission) requestPermission();
  }, [permission]);

  if (!permission) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color={palette.primary} />
      </View>
    );
  }

  if (!permission.granted) {
    return (
      <View style={styles.center}>
        <StatusBar style="dark" />
        <View style={styles.permissionCard}>
          <View style={styles.permissionIcon}>
            <Camera color={palette.error} size={28} />
          </View>
          <Text style={styles.permissionTitle}>Camera permission needed</Text>
          <Text style={styles.permissionBody}>
            We use your camera to scan the pairing QR code printed in the PC agent terminal.
          </Text>
          <TouchableOpacity style={styles.filledBtn} onPress={requestPermission}>
            <Text style={styles.filledBtnText}>Grant permission</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.textBtn} onPress={() => router.back()}>
            <Text style={styles.textBtnText}>Cancel</Text>
          </TouchableOpacity>
        </View>
      </View>
    );
  }

  const handleBarcodeScanned = async ({ data }: { type: string; data: string }) => {
    if (scanned || pairingInProgress) return;
    setScanned(true);
    setPairingInProgress(true);

    const str = (data || '').trim();
    let ip = '';
    let port = '8000';
    let pin = '';

    // Handle Format A: ip:port:pin
    const colonParts = str.split(':');
    if (colonParts.length === 3 && !str.includes('://')) {
      ip = colonParts[0];
      port = colonParts[1];
      pin = colonParts[2];
    } else {
      // Handle Format B: http://10.242.210.183:8080 or ws://10.242.210.183:8080/ws
      const ipMatch = str.match(/\b(?:\d{1,3}\.){3}\d{1,3}\b/);
      if (ipMatch) {
        ip = ipMatch[0];
        const portMatch = str.match(/:(\d{2,5})/);
        if (portMatch) {
          port = portMatch[1];
        }
      }
    }

    if (!ip) {
      Alert.alert(
        'Invalid QR code',
        'Could not parse PC IP address from QR code. Please scan the server QR code.',
        [{ text: 'Try again', onPress: () => setScanned(false) }]
      );
      setPairingInProgress(false);
      return;
    }

    try {
      const result = await pairWithHost(ip, port, pin);

      if (result.kind === 'ok') {
        await addDevice(result.device);
        router.back();
      } else {
        // If probing failed on backend port, fallback to adding direct device for screen streaming
        if (result.kind === 'unreachable') {
          const directDevice = {
            ip,
            port: parseInt(port, 10) || 8080,
            token: pin || 'direct',
            hostname: `PC (${ip})`,
          };
          await addDevice(directDevice);
          router.back();
          return;
        }

        const { title, body } = describePairError(result);
        Alert.alert(title, body, [{ text: 'Try again', onPress: () => setScanned(false) }]);
      }
    } catch (err) {
      console.error(err);
      Alert.alert(
        'Unexpected error',
        String((err as Error)?.message ?? err),
        [{ text: 'Try again', onPress: () => setScanned(false) }]
      );
    } finally {
      setPairingInProgress(false);
    }
  };

  return (
    <View style={styles.cameraRoot}>
      <StatusBar style="light" translucent backgroundColor="transparent" />
      <CameraView
        style={StyleSheet.absoluteFillObject}
        onBarcodeScanned={scanned ? undefined : handleBarcodeScanned}
        barcodeScannerSettings={{ barcodeTypes: ['qr'] }}
      />

      {/* Overlay UI */}
      <View style={StyleSheet.absoluteFillObject} pointerEvents="box-none">
        <View style={styles.scrim} pointerEvents="none" />

        {/* Top bar — close */}
        <View style={[styles.topBar, { paddingTop: Math.max(insets.top, 16) + Spacing.xs }]}>
          <TouchableOpacity style={styles.iconBtn} onPress={() => router.back()} activeOpacity={0.7}>
            <X color={palette.onSurface} size={22} />
          </TouchableOpacity>
        </View>

        {/* Center reticle */}
        <View style={styles.center} pointerEvents="none">
          <View style={styles.reticle}>
            <View style={[styles.corner, styles.tl]} />
            <View style={[styles.corner, styles.tr]} />
            <View style={[styles.corner, styles.bl]} />
            <View style={[styles.corner, styles.br]} />
          </View>
          <View style={styles.reticleHint}>
            <Text style={styles.hintText}>Center the agent’s QR code</Text>
          </View>
        </View>

        {/* Bottom status pill */}
        <View style={[styles.bottomBar, { paddingBottom: Math.max(insets.bottom, 20) + Spacing.md }]}>
          {pairingInProgress ? (
            <View style={styles.statusPill}>
              <ActivityIndicator size="small" color={palette.primary} />
              <Text style={styles.statusText}>Connecting…</Text>
            </View>
          ) : scanned ? (
            <TouchableOpacity
              style={styles.statusPill}
              onPress={() => setScanned(false)}
            >
              <RefreshCcw color={palette.primary} size={16} />
              <Text style={styles.statusText}>Tap to scan again</Text>
            </TouchableOpacity>
          ) : (
            <View style={styles.helpCard}>
              <Text style={styles.helpText}>
                The agent prints a QR code with IP, port, and PIN when it starts.
              </Text>
            </View>
          )}
        </View>
      </View>
    </View>
  );
}

const RETICLE_SIZE = 260;

const styles = StyleSheet.create({
  cameraRoot: { flex: 1, backgroundColor: '#000' },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center' },

  scrim: {
    ...StyleSheet.absoluteFill,
    backgroundColor: 'rgba(0,0,0,0.55)',
  },

  topBar: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    paddingTop: Spacing.xl,
    paddingHorizontal: Spacing.md,
  },
  iconBtn: {
    width: 44,
    height: 44,
    borderRadius: Radius.full,
    backgroundColor: palette.surface,
    alignItems: 'center',
    justifyContent: 'center',
    ...Elevation.level2,
  },

  reticle: {
    width: RETICLE_SIZE,
    height: RETICLE_SIZE,
    position: 'relative',
  },
  corner: {
    position: 'absolute',
    width: 28,
    height: 28,
    borderColor: palette.primary,
  },
  tl: { top: 0, left: 0, borderTopWidth: 4, borderLeftWidth: 4, borderTopLeftRadius: 4 },
  tr: { top: 0, right: 0, borderTopWidth: 4, borderRightWidth: 4, borderTopRightRadius: 4 },
  bl: { bottom: 0, left: 0, borderBottomWidth: 4, borderLeftWidth: 4, borderBottomLeftRadius: 4 },
  br: { bottom: 0, right: 0, borderBottomWidth: 4, borderRightWidth: 4, borderBottomRightRadius: 4 },

  reticleHint: {
    marginTop: Spacing.lg,
    backgroundColor: 'rgba(254, 247, 255, 0.9)',
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.xs,
    borderRadius: Radius.full,
  },
  hintText: {
    ...Typography.labelLarge,
    color: palette.onSurface,
  },

  bottomBar: {
    paddingBottom: Spacing.xxl,
    paddingHorizontal: Spacing.md,
    alignItems: 'center',
  },
  statusPill: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: palette.surface,
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.sm,
    borderRadius: Radius.full,
    gap: Spacing.xs,
    ...Elevation.level2,
  },
  statusText: {
    ...Typography.labelLarge,
    color: palette.onSurface,
  },
  helpCard: {
    backgroundColor: palette.surface,
    borderRadius: Radius.lg,
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.sm,
    ...Elevation.level1,
  },
  helpText: {
    ...Typography.bodySmall,
    color: palette.onSurfaceVariant,
    textAlign: 'center',
    lineHeight: 18,
  },

  // Permission state
  permissionCard: {
    backgroundColor: palette.surface,
    borderRadius: Radius.lg,
    padding: Spacing.xl,
    marginHorizontal: Spacing.lg,
    alignItems: 'center',
    ...Elevation.level2,
  },
  permissionIcon: {
    width: 56,
    height: 56,
    borderRadius: Radius.full,
    backgroundColor: palette.errorContainer,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: Spacing.md,
  },
  permissionTitle: {
    ...Typography.titleLarge,
    color: palette.onSurface,
    marginBottom: Spacing.xs,
    textAlign: 'center',
  },
  permissionBody: {
    ...Typography.bodyMedium,
    color: palette.onSurfaceVariant,
    textAlign: 'center',
    lineHeight: 20,
    marginBottom: Spacing.lg,
  },
  filledBtn: {
    backgroundColor: palette.primary,
    paddingVertical: 12,
    paddingHorizontal: Spacing.xl,
    borderRadius: Radius.full,
    width: '100%',
    alignItems: 'center',
    marginBottom: Spacing.xs,
  },
  filledBtnText: {
    ...Typography.labelLarge,
    color: palette.onPrimary,
  },
  textBtn: {
    paddingVertical: Spacing.xs,
    paddingHorizontal: Spacing.md,
  },
  textBtnText: {
    ...Typography.labelLarge,
    color: palette.primary,
  },
});
