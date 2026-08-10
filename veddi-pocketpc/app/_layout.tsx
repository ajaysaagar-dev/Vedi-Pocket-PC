// Reanimated prints a dev-only warning when the OS-level "Reduce Motion"
// accessibility setting is on. We don't gate animations on it, so silence
// the noise. Must run BEFORE `react-native-gesture-handler` is required,
// since that's what pulls reanimated in and triggers the module-load
// reduced-motion check. Using `require` (not `import`) ensures this call
// is not hoisted past the gesture-handler import below.
require('react-native').LogBox.ignoreLogs([
  '[Reanimated] Reduced motion setting is enabled on this device.',
]);

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
      <StatusBar style="dark" backgroundColor={palette.background} />
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
