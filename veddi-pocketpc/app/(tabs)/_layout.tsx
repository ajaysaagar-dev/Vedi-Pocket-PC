import { Tabs } from 'expo-router';
import { MousePointer, Keyboard, Sliders, Wifi, Tv } from 'lucide-react-native';
import { palette, Typography } from '../../constants/theme-m3';

export default function TabsLayout() {
  return (
    <Tabs
      screenOptions={{
        tabBarStyle: {
          backgroundColor: palette.surfaceContainer,
          borderTopWidth: 0,
          height: 72,
          paddingBottom: SpacingY(),
          paddingTop: 12,
        },
        tabBarActiveTintColor: palette.primary,
        tabBarInactiveTintColor: palette.onSurfaceVariant,
        tabBarLabelStyle: {
          fontSize: Typography.labelMedium.fontSize,
          fontWeight: '500',
          letterSpacing: 0.5,
        },
        headerStyle: {
          backgroundColor: palette.surface,
          borderBottomWidth: 0,
          shadowOpacity: 0,
          elevation: 0,
        },
        headerTintColor: palette.onSurface,
        headerTitleStyle: {
          fontSize: Typography.titleLarge.fontSize,
          fontWeight: '500',
        },
        sceneStyle: {
          backgroundColor: palette.background,
        },
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: 'Connections',
          tabBarLabel: 'Devices',
          tabBarIcon: ({ color, size }) => <Wifi color={color} size={size} />,
        }}
      />
      <Tabs.Screen
        name="screen"
        options={{
          href: null,
        }}
      />
      <Tabs.Screen
        name="trackpad"
        options={{
          title: 'Trackpad',
          tabBarLabel: 'Trackpad',
          tabBarIcon: ({ color, size }) => <MousePointer color={color} size={size} />,
        }}
      />
      <Tabs.Screen
        name="keyboard"
        options={{
          title: 'Keyboard',
          tabBarLabel: 'Keyboard',
          tabBarIcon: ({ color, size }) => <Keyboard color={color} size={size} />,
        }}
      />
      <Tabs.Screen
        name="controls"
        options={{
          title: 'Controls',
          tabBarLabel: 'Controls',
          tabBarIcon: ({ color, size }) => <Sliders color={color} size={size} />,
        }}
      />
      <Tabs.Screen
        name="explore"
        options={{
          href: null,
        }}
      />
    </Tabs>
  );
}

/** Local helper — avoids importing the whole Spacing object just for one value. */
function SpacingY() {
  // 8dp above safe area for breathing room
  return 8;
}
