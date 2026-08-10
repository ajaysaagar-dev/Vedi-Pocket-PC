/**
 * Suppress Reanimated's "[Reanimated] Reduced motion setting is enabled on
 * this device" dev-mode warning.
 *
 * Reanimated's `animation/util.ts:80` checks `ReducedMotionManager.jsValue`
 * at module evaluation time and fires `logger.warn(...)` if it's truthy.
 * That manager is initialized from `global._REANIMATED_IS_REDUCED_MOTION`
 * in `ReducedMotion.ts:13`. Setting it to `false` here — BEFORE the
 * gesture-handler / reanimated modules are loaded — stops the warning at
 * its source.
 *
 * Why a side-effect module? `import` statements are hoisted to the top of
 * the file by Babel's CommonJS transform in the order they appear. So
 * putting this as the FIRST import in `_layout.tsx` guarantees it runs
 * before `import { GestureHandlerRootView } from 'react-native-gesture-handler'`,
 * which is what triggers reanimated's module-load check.
 *
 * We intentionally don't gate animations on the reduced-motion setting —
 * the trackpad and screen-viewport gestures need to feel instant even when
 * the OS-level accessibility setting is on.
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
(globalThis as any)._REANIMATED_IS_REDUCED_MOTION = false;

export {};
