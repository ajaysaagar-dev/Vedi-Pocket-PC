import React from 'react';
import { View, Text, Image, StyleSheet } from 'react-native';
import { Tabs } from 'expo-router';
import { Sliders, Wifi, Tv, MousePointer, Keyboard } from 'lucide-react-native';
import { palette, Typography, Spacing } from '../../constants/theme-m3';
import { AppLogo } from '../../constants/assets';

function HeaderTitleWithLogo({ title }: { title: string }) {
  return (
    <View style={styles.headerBrandContainer}>
      <View style={styles.logoBadge}>
        <Image source={AppLogo} style={styles.logoImage} resizeMode="cover" />
      </View>
      <Text style={styles.headerTitleText}>{title}</Text>
    </View>
  );
}

export default function TabsLayout() {
  return (
    <Tabs
      screenOptions={{
        freezeOnBlur: true,
        tabBarStyle: {
          backgroundColor: palette.surfaceContainer,
          borderTopWidth: 0,
          height: 70,
          paddingBottom: Spacing.xs,
          paddingTop: Spacing.xs,
        },
        tabBarActiveTintColor: palette.primary,
        tabBarInactiveTintColor: palette.onSurfaceVariant,
        tabBarLabelStyle: {
          fontSize: Typography.labelMedium.fontSize,
          fontWeight: '600',
          letterSpacing: 0.5,
        },
        headerStyle: {
          backgroundColor: palette.surface,
          borderBottomWidth: 0,
          shadowOpacity: 0,
          elevation: 0,
        },
        headerTintColor: palette.onSurface,
        sceneStyle: {
          backgroundColor: palette.background,
        },
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          headerTitle: () => <HeaderTitleWithLogo title="Vedi Pocket PC" />,
          tabBarLabel: 'Devices',
          tabBarIcon: ({ color, size }) => <Wifi color={color} size={size} />,
        }}
      />
      <Tabs.Screen
        name="screen"
        options={{
          headerTitle: () => <HeaderTitleWithLogo title="Remote Control" />,
          tabBarLabel: 'Remote',
          tabBarIcon: ({ color, size }) => <Tv color={color} size={size} />,
        }}
      />
      <Tabs.Screen
        name="controls"
        options={{
          headerTitle: () => <HeaderTitleWithLogo title="System Controls" />,
          tabBarLabel: 'Controls',
          tabBarIcon: ({ color, size }) => <Sliders color={color} size={size} />,
        }}
      />

      {/* Repurposed redundant tab entries - hidden from tab bar to maintain routing compatibility */}
      <Tabs.Screen
        name="trackpad"
        options={{
          href: null,
        }}
      />
      <Tabs.Screen
        name="keyboard"
        options={{
          href: null,
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

const styles = StyleSheet.create({
  headerBrandContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  logoBadge: {
    width: 32,
    height: 32,
    borderRadius: 9,
    overflow: 'hidden',
    borderWidth: 1.5,
    borderColor: 'rgba(255, 255, 255, 0.2)',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 3.84,
    elevation: 3,
  },
  logoImage: {
    width: '100%',
    height: '100%',
  },
  headerTitleText: {
    fontSize: Typography.titleLarge.fontSize,
    fontWeight: '600',
    color: palette.onSurface,
    letterSpacing: 0.2,
  },
});
