import React, { useState, useEffect, useMemo } from 'react';
import {
  StyleSheet,
  Text,
  View,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
  Dimensions,
} from 'react-native';
import { useRouter } from 'expo-router';
import { CameraView, useCameraPermissions } from 'expo-camera';
import { StatusBar } from 'expo-status-bar';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import * as Haptics from 'expo-haptics';
import { X, Camera, RefreshCcw } from 'lucide-react-native';
import { useDeviceStore } from '../src/store/deviceStore';
import { pairWithHost, describePairError } from '../src/ws/pairing';
import { palette, Spacing, Radius, Typography, Elevation } from '../constants/theme-m3';

export default function PairingScreen() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const [permission, requestPermission] = useCameraPermissions();
  const [scanned, setScanned] = useState(false);
  const [pairingInProgress, setPairingInProgress] = useState(false);
  const addDevice = useDeviceStore(state => state.addDevice);

  // Compute the reticle size from the screen so it scales to phones,
  // phablets, and tablets. The previous 260px fixed size was hard to
  // align with on anything but a small phone — users had to fish
  // for the QR code. Targeting ~72% of the smaller screen dimension
  // gives the QR roughly half the viewfinder area (the OS "quiet
  // zone" needs to fit inside that half), which scans reliably
  // across all our test devices.
  const reticleSize = useMemo(() => {
    const { width, height } = Dimensions.get('window');
    const smaller = Math.min(width, height);
    const target = Math.round(smaller * 0.72);
    // Clamp so we don't get an absurdly small or giant cutout.
    return Math.max(220, Math.min(560, target));
  }, []);

  useEffect(() => {
    if (!permission) requestPermission();
  }, [permission]);

  if (!permission) {
    return (
      <View style={styles.centerContainer}>
        <ActivityIndicator size="large" color={palette.primary} />
      </View>
    );
  }

  if (!permission.granted) {
    return (
      <View style={styles.centerContainer}>
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

    // Haptic + status-bar flash so the user knows the scan succeeded
    // even before the pairing call returns. Without this, users would
    // often assume the camera wasn't aligned and move it again,
    // re-triggering the scan and racing with the in-flight request.
    try {
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success).catch(() => {});
    } catch {
      /* haptics are optional */
    }

    const str = (data || '').trim();
    let ip = '';
    let port = '8000';
    let pin = '';

    // Handle Format A: ip:port:pin (preferred — carries the PIN so the
    // mobile app can auth against the backend agent).
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
  };  return (
    <View style={styles.cameraRoot}>
      <StatusBar style="light" />
      <CameraView
        style={styles.camera}
        facing="back"
        onBarcodeScanned={scanned ? undefined : handleBarcodeScanned}
        barcodeScannerSettings={{ barcodeTypes: ['qr'] }}
      />

      {/* Viewfinder Dark Mask with Center Transparent Cutout */}
      <View style={StyleSheet.absoluteFill} pointerEvents="none">
        <View style={styles.maskRowTop} />
        <View style={[styles.maskRowCenter, { height: reticleSize }]}>
          <View style={styles.maskSide} />
          <View style={{ width: reticleSize, height: reticleSize }} />
          <View style={styles.maskSide} />
        </View>
        <View style={styles.maskRowBottom} />
      </View>

      {/* Overlay UI — Top Close Button, Perfectly Centered Reticle & Bottom Status */}
      <View style={StyleSheet.absoluteFill} pointerEvents="box-none">
        {/* Top bar — close */}
        <View style={[styles.topBar, { paddingTop: Math.max(insets.top, 16) + Spacing.xs }]}>
          <TouchableOpacity style={styles.iconBtn} onPress={() => router.back()} activeOpacity={0.7}>
            <X color={palette.onSurface} size={22} />
          </TouchableOpacity>
        </View>

        {/* Center reticle — EXACT geometric center of the screen */}
        <View style={styles.centerContainer} pointerEvents="none">
          <View
            style={[
              styles.reticle,
              { width: reticleSize, height: reticleSize },
            ]}
          >
            <View style={styles.reticleHintTop}>
              <Text style={styles.hintText}>Align QR code within frame</Text>
            </View>
            <View style={[styles.corner, styles.tl]} />
            <View style={[styles.corner, styles.tr]} />
            <View style={[styles.corner, styles.bl]} />
            <View style={[styles.corner, styles.br]} />
            <View style={styles.crossH} />
            <View style={styles.crossV} />
            <View style={styles.laserLine} />
            {pairingInProgress && <View style={styles.scanFlash} />}
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

const styles = StyleSheet.create({
  cameraRoot: { flex: 1, backgroundColor: '#000' },
  camera: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
  },

  // Viewfinder dark mask around center cutout
  maskRowTop: { flex: 1, backgroundColor: 'rgba(0, 0, 0, 0.55)' },
  maskRowCenter: { flexDirection: 'row' },
  maskSide: { flex: 1, backgroundColor: 'rgba(0, 0, 0, 0.55)' },
  maskRowBottom: { flex: 1, backgroundColor: 'rgba(0, 0, 0, 0.55)' },

  // Center container for 100% exact alignment
  centerContainer: {
    ...StyleSheet.absoluteFill,
    alignItems: 'center',
    justifyContent: 'center',
  },

  topBar: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    paddingTop: Spacing.xl,
    paddingHorizontal: Spacing.md,
    zIndex: 10,
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
    position: 'relative',
    alignItems: 'center',
    justifyContent: 'center',
  },

  reticleHintTop: {
    position: 'absolute',
    top: -48,
    backgroundColor: 'rgba(15, 23, 42, 0.88)',
    paddingHorizontal: Spacing.md,
    paddingVertical: 6,
    borderRadius: Radius.full,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.2)',
    ...Elevation.level2,
  },
  hintText: {
    ...Typography.labelLarge,
    color: '#ffffff',
    fontWeight: '600',
  },

  corner: {
    position: 'absolute',
    width: 32,
    height: 32,
    borderColor: '#38bdf8',
  },
  tl: { top: 0, left: 0, borderTopWidth: 4, borderLeftWidth: 4, borderTopLeftRadius: 14 },
  tr: { top: 0, right: 0, borderTopWidth: 4, borderRightWidth: 4, borderTopRightRadius: 14 },
  bl: { bottom: 0, left: 0, borderBottomWidth: 4, borderLeftWidth: 4, borderBottomLeftRadius: 14 },
  br: { bottom: 0, right: 0, borderBottomWidth: 4, borderRightWidth: 4, borderBottomRightRadius: 14 },

  crossH: {
    position: 'absolute',
    left: '20%',
    right: '20%',
    top: '50%',
    height: 1,
    backgroundColor: 'rgba(255, 255, 255, 0.25)',
  },
  crossV: {
    position: 'absolute',
    top: '20%',
    bottom: '20%',
    left: '50%',
    width: 1,
    backgroundColor: 'rgba(255, 255, 255, 0.25)',
  },
  laserLine: {
    position: 'absolute',
    left: 12,
    right: 12,
    top: '50%',
    height: 2,
    backgroundColor: '#38bdf8',
    borderRadius: 1,
    shadowColor: '#38bdf8',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.9,
    shadowRadius: 6,
    elevation: 4,
  },

  scanFlash: {
    ...StyleSheet.absoluteFill,
    backgroundColor: 'rgba(34, 197, 94, 0.35)',
    borderRadius: 12,
  },

  bottomBar: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
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
