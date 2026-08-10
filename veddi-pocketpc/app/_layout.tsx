// MUST be the first import. Babel's CommonJS transform hoists every
// `import` statement to the top of the file in source order, so this side
// effect runs before `react-native-gesture-handler` (and therefore
// `react-native-reanimated`) is required. Without this, reanimated's
// module-load check in `animation/util.ts:80` fires its dev-only "Reduced
// motion is enabled" warning. We don't gate animations on that setting, so
// suppress it at the source. See patch-reanimated.ts for details.
import '../src/utils/patch-reanimated';

import { useEffect } from 'react';
import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { useDeviceStore } from '../src/store/deviceStore';
import { palette, Spacing } from '../constants/theme-m3';

export default function RootLayout() {
  const loadDevices = useDeviceStore(state => state.loadDevices);

  useEffect(() => {
    loadDevices();
  }, [loadDevices]);

  return (
    <GestureHandlerRootView style={{ flex: 1, backgroundColor: palette.background }}>
      {/* expo-status-bar doesn't accept `backgroundColor` — on Android the
          app is edge-to-edge (`edgeToEdgeEnabled: true` in app.json), so the
          content draws behind a transparent status bar and the palette color
          shows through naturally. `backgroundColor` here was a no-op. */}
      <StatusBar style="dark" />
      <Stack
        screenOptions={{
          headerStyle: { backgroundColor: palette.surface },
          headerTintColor: palette.onSurface,
          headerTitleStyle: { fontSize: 22, fontWeight: '500' },
          headerShadowVisible: false,
          contentStyle: { backgroundColor: palette.background },
        }}
      >
        <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
        <Stack.Screen
          name="pairing"
          options={{
            headerShown: false,
            presentation: 'fullScreenModal',
            animation: 'fade',
          }}
        />
      </Stack>
    </GestureHandlerRootView>
  );
}
