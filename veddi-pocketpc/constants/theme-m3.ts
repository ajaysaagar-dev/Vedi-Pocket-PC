/**
 * Material Design 3 (Material You) tokens for PC Remote.
 * Reference: https://m3.material.io/styles/color/system
 *
 * Light scheme only — keeps the UI clean and readable like Google apps
 * (Gmail, Drive, Calendar). All colors here come from the official M3 baseline.
 */

export const Colors = {
  light: {
    // Primary — soft purple, used for FAB, primary buttons, focused states
    primary: '#6750A4',
    onPrimary: '#FFFFFF',
    primaryContainer: '#EADDFF',
    onPrimaryContainer: '#21005D',

    // Secondary — muted neutral purple, for less prominent actions
    secondary: '#625B71',
    onSecondary: '#FFFFFF',
    secondaryContainer: '#E8DEF8',
    onSecondaryContainer: '#1D192B',

    // Tertiary — warm pink, used for highlights / status accents
    tertiary: '#7D5260',
    onTertiary: '#FFFFFF',
    tertiaryContainer: '#FFD8E4',
    onTertiaryContainer: '#31111D',

    // Error — for destructive actions (shutdown) and warnings
    error: '#B3261E',
    onError: '#FFFFFF',
    errorContainer: '#F9DEDC',
    onErrorContainer: '#410E0B',

    // Background / Surface
    background: '#FEF7FF',
    onBackground: '#1D1B20',
    surface: '#FEF7FF',
    onSurface: '#1D1B20',
    surfaceVariant: '#E7E0EC',
    onSurfaceVariant: '#49454F',

    // Surfaces with elevation
    surfaceContainerLowest: '#FFFFFF',
    surfaceContainerLow: '#F7F2FA',
    surfaceContainer: '#F3EDF7',
    surfaceContainerHigh: '#ECE6F0',
    surfaceContainerHighest: '#E6E0E9',

    // Outline — borders, dividers
    outline: '#79747E',
    outlineVariant: '#CAC4D0',

    // Inverse — snackbars
    inverseSurface: '#322F35',
    inverseOnSurface: '#F5EFF7',
    inversePrimary: '#D0BCFF',

    // Misc
    shadow: '#000000',
    scrim: '#000000',
  },
} as const;

/** 4 / 8dp spacing grid */
export const Spacing = {
  xxs: 4,
  xs: 8,
  sm: 12,
  md: 16,
  lg: 20,
  xl: 24,
  xxl: 32,
  xxxl: 48,
} as const;

/** Material 3 shape scale (corner radii) */
export const Radius = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 28,
  full: 9999,
} as const;

/**
 * Material 3 type scale (subset).
 * Sizes in sp on Android — RN uses fontSize which is dp-equivalent.
 * https://m3.material.io/styles/typography/type-scale-tokens
 */
export const Typography = {
  displayLarge: { fontSize: 57, lineHeight: 64, fontWeight: '400' as const, letterSpacing: -0.25 },
  displayMedium: { fontSize: 45, lineHeight: 52, fontWeight: '400' as const },
  displaySmall: { fontSize: 36, lineHeight: 44, fontWeight: '400' as const },

  headlineLarge: { fontSize: 32, lineHeight: 40, fontWeight: '400' as const },
  headlineMedium: { fontSize: 28, lineHeight: 36, fontWeight: '400' as const },
  headlineSmall: { fontSize: 24, lineHeight: 32, fontWeight: '400' as const },

  titleLarge: { fontSize: 22, lineHeight: 28, fontWeight: '500' as const },
  titleMedium: { fontSize: 16, lineHeight: 24, fontWeight: '500' as const, letterSpacing: 0.15 },
  titleSmall: { fontSize: 14, lineHeight: 20, fontWeight: '500' as const, letterSpacing: 0.1 },

  bodyLarge: { fontSize: 16, lineHeight: 24, fontWeight: '400' as const, letterSpacing: 0.5 },
  bodyMedium: { fontSize: 14, lineHeight: 20, fontWeight: '400' as const, letterSpacing: 0.25 },
  bodySmall: { fontSize: 12, lineHeight: 16, fontWeight: '400' as const, letterSpacing: 0.4 },

  labelLarge: { fontSize: 14, lineHeight: 20, fontWeight: '500' as const, letterSpacing: 0.1 },
  labelMedium: { fontSize: 12, lineHeight: 16, fontWeight: '500' as const, letterSpacing: 0.5 },
  labelSmall: { fontSize: 11, lineHeight: 16, fontWeight: '500' as const, letterSpacing: 0.5 },
} as const;

/** M3 elevation levels (tonal overlay + shadow) */
export const Elevation = {
  level0: { elevation: 0 },
  level1: {
    elevation: 1,
    shadowColor: Colors.light.shadow,
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.15,
    shadowRadius: 2,
  },
  level2: {
    elevation: 3,
    shadowColor: Colors.light.shadow,
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.18,
    shadowRadius: 3,
  },
  level3: {
    elevation: 6,
    shadowColor: Colors.light.shadow,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.22,
    shadowRadius: 4,
  },
} as const;

/** Active palette for the app — light theme only for now. */
export const palette = Colors.light;

export type Palette = typeof palette;
