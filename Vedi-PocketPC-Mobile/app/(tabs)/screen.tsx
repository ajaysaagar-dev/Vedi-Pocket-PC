import React from 'react';
import { StyleSheet, View, ScrollView, Text } from 'react-native';
import DesktopViewport from '../../components/DesktopViewport';
import { palette, Spacing, Typography } from '../../constants/theme-m3';
import { useDeviceStore } from '../../src/store/deviceStore';

export default function ScreenTabScreen() {
  const activeDevice = useDeviceStore(state => state.activeDevice);
  const connectionStatus = useDeviceStore(state => state.connectionStatus);

  return (
    <View style={styles.screen}>
      <ScrollView contentContainerStyle={styles.scroll}>
        <View style={styles.header}>
          <Text style={styles.title}>PC Desktop Screen</Text>
          <Text style={styles.subtitle}>
            {activeDevice
              ? `Streaming from ${activeDevice.hostname} (${activeDevice.ip})`
              : 'Connect to a PC in Devices tab to view real-time desktop screen.'}
          </Text>
        </View>

        {/* Real-time Desktop Viewport Component */}
        <DesktopViewport streamPort={8080} interactive={true} />

        <View style={styles.infoCard}>
          <Text style={styles.infoTitle}>Viewport Controls &amp; Gestures</Text>
          <Text style={styles.infoBody}>
            • <Text style={styles.bold}>Tap Screen:</Text> Sends a left mouse click at exact tap coordinates on your PC desktop.
            {'\n'}• <Text style={styles.bold}>Start/Stop:</Text> Toggle real-time WebSocket binary frame streaming.
            {'\n'}• <Text style={styles.bold}>Settings (⚙):</Text> Configure custom screen stream server IP &amp; port (default 8080).
            {'\n'}• <Text style={styles.bold}>Fullscreen (⤢):</Text> Expand desktop viewport to fill full mobile screen.
          </Text>
        </View>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: palette.background,
  },
  scroll: {
    padding: Spacing.md,
    paddingBottom: Spacing.xxxl,
  },
  header: {
    marginBottom: Spacing.md,
  },
  title: {
    ...Typography.headlineSmall,
    color: palette.onSurface,
  },
  subtitle: {
    ...Typography.bodyMedium,
    color: palette.onSurfaceVariant,
    marginTop: 4,
  },
  infoCard: {
    backgroundColor: palette.surfaceContainer,
    borderRadius: Spacing.md,
    padding: Spacing.md,
    marginTop: Spacing.sm,
  },
  infoTitle: {
    ...Typography.titleSmall,
    color: palette.onSurface,
    marginBottom: 6,
  },
  infoBody: {
    ...Typography.bodySmall,
    color: palette.onSurfaceVariant,
    lineHeight: 20,
  },
  bold: {
    fontWeight: '600',
    color: palette.onSurface,
  },
});
