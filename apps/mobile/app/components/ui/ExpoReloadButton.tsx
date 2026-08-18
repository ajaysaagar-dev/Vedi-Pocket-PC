import React, { useState, useRef } from 'react';
import {
  StyleSheet,
  Text,
  TouchableOpacity,
  Platform,
  DevSettings,
  Animated,
  Easing,
  Alert,
  StyleProp,
  ViewStyle,
  TextStyle,
} from 'react-native';
import * as Haptics from 'expo-haptics';
import { RefreshCw } from 'lucide-react-native';
import { palette, Spacing, Radius, Typography, Elevation } from '../../constants/theme-m3';

export interface ExpoReloadButtonProps {
  variant?: 'icon' | 'filled' | 'outlined' | 'pill';
  label?: string;
  iconSize?: number;
  style?: StyleProp<ViewStyle>;
  textStyle?: StyleProp<TextStyle>;
  color?: string;
  onBeforeReload?: () => void;
}

export const ExpoReloadButton: React.FC<ExpoReloadButtonProps> = ({
  variant = 'icon',
  label,
  iconSize,
  style,
  textStyle,
  color,
  onBeforeReload,
}) => {
  const [isReloading, setIsReloading] = useState(false);
  const spinValue = useRef(new Animated.Value(0)).current;

  const startSpinAnimation = () => {
    spinValue.setValue(0);
    Animated.timing(spinValue, {
      toValue: 1,
      duration: 800,
      easing: Easing.linear,
      useNativeDriver: true,
    }).start();
  };

  const handleReload = async () => {
    if (isReloading) return;
    setIsReloading(true);
    startSpinAnimation();

    try {
      await Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium).catch(() => {});
    } catch {
      // Ignore
    }

    if (onBeforeReload) {
      onBeforeReload();
    }

    setTimeout(() => {
      if (Platform.OS === 'web') {
        if (typeof window !== 'undefined' && window.location) {
          window.location.reload();
        }
      } else {
        if (DevSettings && typeof DevSettings.reload === 'function') {
          DevSettings.reload();
        } else {
          Alert.alert(
            'Reload Expo',
            'DevSettings.reload() is active in Expo Go and development builds.',
            [{ text: 'OK', onPress: () => setIsReloading(false) }]
          );
        }
      }
    }, 250);
  };

  const spin = spinValue.interpolate({
    inputRange: [0, 1],
    outputRange: ['0deg', '360deg'],
  });

  const effectiveIconSize = iconSize ?? (variant === 'icon' || variant === 'pill' ? 18 : 20);
  const effectiveColor =
    color ??
    (variant === 'filled'
      ? palette.onPrimaryContainer
      : variant === 'outlined'
      ? palette.primary
      : variant === 'pill'
      ? palette.primary
      : palette.onSurfaceVariant);

  if (variant === 'icon') {
    return (
      <TouchableOpacity
        style={[styles.iconButton, style]}
        onPress={handleReload}
        activeOpacity={0.7}
        accessibilityLabel="Reload Expo App"
        accessibilityRole="button"
        hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
      >
        <Animated.View style={{ transform: [{ rotate: spin }] }}>
          <RefreshCw size={effectiveIconSize} color={effectiveColor} />
        </Animated.View>
      </TouchableOpacity>
    );
  }

  if (variant === 'pill') {
    return (
      <TouchableOpacity
        style={[styles.pillButton, style]}
        onPress={handleReload}
        activeOpacity={0.75}
        accessibilityLabel="Reload Expo App"
        accessibilityRole="button"
      >
        <Animated.View style={{ transform: [{ rotate: spin }] }}>
          <RefreshCw size={effectiveIconSize} color={effectiveColor} />
        </Animated.View>
        <Text style={[styles.pillText, { color: effectiveColor }, textStyle]}>
          {label || 'Reload'}
        </Text>
      </TouchableOpacity>
    );
  }

  if (variant === 'outlined') {
    return (
      <TouchableOpacity
        style={[styles.outlinedButton, style]}
        onPress={handleReload}
        activeOpacity={0.8}
        accessibilityLabel="Reload Expo App"
        accessibilityRole="button"
      >
        <Animated.View style={{ transform: [{ rotate: spin }] }}>
          <RefreshCw size={effectiveIconSize} color={effectiveColor} />
        </Animated.View>
        <Text style={[styles.outlinedText, { color: effectiveColor }, textStyle]}>
          {label || 'Reload Expo'}
        </Text>
      </TouchableOpacity>
    );
  }

  return (
    <TouchableOpacity
      style={[styles.filledButton, style]}
      onPress={handleReload}
      activeOpacity={0.85}
      accessibilityLabel="Reload Expo App"
      accessibilityRole="button"
    >
      <Animated.View style={{ transform: [{ rotate: spin }] }}>
        <RefreshCw size={effectiveIconSize} color={effectiveColor} />
      </Animated.View>
      <Text style={[styles.filledText, { color: effectiveColor }, textStyle]}>
        {label || 'Reload Expo App'}
      </Text>
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  iconButton: {
    width: 40,
    height: 40,
    borderRadius: Radius.full,
    backgroundColor: palette.surfaceContainerHigh,
    alignItems: 'center',
    justifyContent: 'center',
  },
  pillButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.xs,
    paddingHorizontal: Spacing.sm,
    paddingVertical: Spacing.xxs + 2,
    borderRadius: Radius.full,
    backgroundColor: palette.primaryContainer,
  },
  pillText: {
    fontSize: Typography.labelMedium.fontSize,
    fontWeight: '600',
  },
  outlinedButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: Spacing.xs,
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.sm,
    borderRadius: Radius.md,
    borderWidth: 1,
    borderColor: palette.outlineVariant,
    backgroundColor: palette.surface,
  },
  outlinedText: {
    fontSize: Typography.labelLarge.fontSize,
    fontWeight: '500',
  },
  filledButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: Spacing.xs,
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.sm,
    borderRadius: Radius.md,
    backgroundColor: palette.primaryContainer,
    ...Elevation.level1,
  },
  filledText: {
    fontSize: Typography.labelLarge.fontSize,
    fontWeight: '600',
  },
});

export default ExpoReloadButton;
