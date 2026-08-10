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
  };

  return (
    <View style={styles.cameraRoot}>
      <StatusBar style="light" translucent backgroundColor="transparent" />
      <CameraView
        style={styles.camera}
        facing="back"
        // Pin the camera to a 4:3 aspect so the reticle shape matches
        // the area the QR detector actually scans. Without this, the
        // sensor's native aspect ratio (often 16:9) would squish the
        // viewfinder and misalign the on-screen reticle with the area
        // the OS samples for barcodes.
        ratio="4:3"
        onBarcodeScanned={scanned ? undefined : handleBarcodeScanned}
        barcodeScannerSettings={{ barcodeTypes: ['qr'] }}
      />

      {/* Overlay UI — sit *above* the camera without darkening it.
          Previous version painted a full-screen `rgba(0,0,0,0.55)` scrim
          on top of the camera feed, which on Android turned the live
          viewfinder into a black screen. The reticle corners + hint
          pill are enough visual scaffolding; we leave the camera
          feed itself untouched. */}
      <View style={StyleSheet.absoluteFillObject} pointerEvents="box-none">
        {/* Top bar — close */}
        <View style={[styles.topBar, { paddingTop: Math.max(insets.top, 16) + Spacing.xs }]}>
          <TouchableOpacity style={styles.iconBtn} onPress={() => router.back()} activeOpacity={0.7}>
            <X color={palette.onSurface} size={22} />
          </TouchableOpacity>
        </View>

        {/* Center reticle — responsive size, hint above so it doesn't
            collide with the bottom status pill. */}
        <View style={styles.center} pointerEvents="none">
          <View style={styles.reticleHintTop}>
            <Text style={styles.hintText}>Align the QR within the frame</Text>
          </View>
          <View
            style={[
              styles.reticle,
              { width: reticleSize, height: reticleSize },
            ]}
          >
            <View style={[styles.corner, styles.tl]} />
            <View style={[styles.corner, styles.tr]} />
            <View style={[styles.corner, styles.bl]} />
            <View style={[styles.corner, styles.br]} />
            {/* Centre crosshair — subtle aid for alignment on the
                second axis. Drawn as two thin guide lines; reads as
                part of the reticle so it doesn't look like a defect. */}
            <View style={styles.crossH} />
            <View style={styles.crossV} />
            {/* Animated success flash on scan */}
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
    // Explicit flex fill instead of `absoluteFillObject` — under the
    // new architecture some Android builds were laying out the
    // CameraView with zero width/height when only positioned absolute
    // with no parent flex chain.
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
  },
  center: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingTop: Spacing.xl,
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
    // Size is set inline from `reticleSize` so it scales with the
    // screen. The previous hard-coded 260×260 was hard to align
    // with on tablets.
    position: 'relative',
    marginTop: Spacing.md,
  },
  corner: {
    position: 'absolute',
    width: 32,
    height: 32,
    borderColor: palette.primary,
  },
  tl: { top: 0, left: 0, borderTopWidth: 5, borderLeftWidth: 5, borderTopLeftRadius: 6 },
  tr: { top: 0, right: 0, borderTopWidth: 5, borderRightWidth: 5, borderTopRightRadius: 6 },
  bl: { bottom: 0, left: 0, borderBottomWidth: 5, borderLeftWidth: 5, borderBottomLeftRadius: 6 },
  br: { bottom: 0, right: 0, borderBottomWidth: 5, borderRightWidth: 5, borderBottomRightRadius: 6 },

  // Faint guide crosshair so users can tell whether the camera is
  // actually pointing at the code (not a tilted view). 0.4 opacity
  // keeps it from competing with the corner brackets.
  crossH: {
    position: 'absolute',
    left: '12%',
    right: '12%',
    top: '50%',
    height: 1,
    backgroundColor: 'rgba(255,255,255,0.35)',
  },
  crossV: {
    position: 'absolute',
    top: '12%',
    bottom: '12%',
    left: '50%',
    width: 1,
    backgroundColor: 'rgba(255,255,255,0.35)',
  },

  // Brief flash overlay drawn while the pairing request is in flight.
  // Green is universal "success" — feels good on Android too where
  // haptics are short.
  scanFlash: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(46, 125, 50, 0.25)',
    borderRadius: 8,
  },

  reticleHintTop: {
    backgroundColor: 'rgba(254, 247, 255, 0.9)',
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.xs,
    borderRadius: Radius.full,
    ...Elevation.level2,
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
