import React, { useState } from 'react';
import { StyleSheet, Text, View, TouchableOpacity, ScrollView, TextInput } from 'react-native';
import { GestureDetector, Gesture } from 'react-native-gesture-handler';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withSpring,
  ReduceMotion,
} from 'react-native-reanimated';
import { 
  MousePointer, 
  CircleHelp, 
  MousePointerClick, 
  Tv,
  Keyboard as KeyboardIcon,
  Send,
  CornerDownLeft,
  Delete,
  Space,
  Command,
} from 'lucide-react-native';
import DesktopViewport from '../../components/DesktopViewport';
import { useDeviceStore } from '../../src/store/deviceStore';
import wsClient from '../../src/ws/client';
import { palette, Spacing, Radius, Typography, Elevation } from '../../constants/theme-m3';

const SENSITIVITY_LEVELS = [1.0, 2.5, 5.0, 10.0, 15.0, 20.0];

export default function TrackpadScreen() {
  const connectionStatus = useDeviceStore(state => state.connectionStatus);
  const activeDevice = useDeviceStore(state => state.activeDevice);

  const [sensitivity, setSensitivity] = useState(1.5);
  const [showHelp, setShowHelp] = useState(false);
  const [showScreenViewport, setShowScreenViewport] = useState(true);

  const [inputText, setInputText] = useState('');
  const [showKeyboardInput, setShowKeyboardInput] = useState(false);

  const handleSendText = () => {
    if (!inputText) return;
    wsClient.send({ type: 'text_input', text: inputText });
    setInputText('');
  };

  const handleKeyPress = (key: string) => {
    wsClient.send({ type: 'key_press', key });
  };

  const handleKeyCombo = (keys: string[]) => {
    wsClient.send({ type: 'key_combo', keys });
  };

  const isPressing = useSharedValue(0);
  const touchX = useSharedValue(0);
  const touchY = useSharedValue(0);
  const lastTranslationX = useSharedValue(0);
  const lastTranslationY = useSharedValue(0);
  const lastScrollY = useSharedValue(0);

  const panGesture = Gesture.Pan()
    .minPointers(1)
    .maxPointers(1)
    .runOnJS(true)
    .onStart(event => {
      isPressing.value = withSpring(1, { reduceMotion: ReduceMotion.Never });
      touchX.value = event.x;
      touchY.value = event.y;
      lastTranslationX.value = event.translationX;
      lastTranslationY.value = event.translationY;
    })
    .onUpdate(event => {
      touchX.value = event.x;
      touchY.value = event.y;

      const dx = (event.translationX - lastTranslationX.value) * sensitivity;
      const dy = (event.translationY - lastTranslationY.value) * sensitivity;

      lastTranslationX.value = event.translationX;
      lastTranslationY.value = event.translationY;

      if (Math.abs(dx) > 0.01 || Math.abs(dy) > 0.01) {
        wsClient.send({
          type: 'mouse_move',
          dx,
          dy,
        });
      }
    })
    .onEnd(() => {
      isPressing.value = withSpring(0, { reduceMotion: ReduceMotion.Never });
      lastTranslationX.value = 0;
      lastTranslationY.value = 0;
    });

  const scrollGesture = Gesture.Pan()
    .minPointers(2)
    .maxPointers(2)
    .runOnJS(true)
    .onStart(event => {
      lastScrollY.value = event.translationY;
    })
    .onUpdate(event => {
      const dy = event.translationY - lastScrollY.value;
      lastScrollY.value = event.translationY;

      if (Math.abs(dy) > 0.01) {
        wsClient.send({ type: 'scroll', dy: -dy / 3 });
      }
    })
    .onEnd(() => {
      lastScrollY.value = 0;
    });

  const leftClickTap = Gesture.Tap()
    .numberOfTaps(1)
    .maxDuration(250)
    .runOnJS(true)
    .onEnd(() => {
      wsClient.send({ type: 'mouse_click', button: 'left', clicks: 1 });
    });

  const doubleClickTap = Gesture.Tap()
    .numberOfTaps(2)
    .runOnJS(true)
    .onEnd(() => {
      wsClient.send({ type: 'mouse_click', button: 'left', clicks: 2 });
    });

  const rightClickTap = Gesture.Tap()
    .numberOfTaps(1)
    .minPointers(2)
    .runOnJS(true)
    .onEnd(() => {
      wsClient.send({ type: 'mouse_click', button: 'right', clicks: 1 });
    });

  const composed = Gesture.Race(
    scrollGesture,
    Gesture.Exclusive(doubleClickTap, rightClickTap, leftClickTap),
    panGesture
  );

  const indicatorStyle = useAnimatedStyle(() => ({
    left: touchX.value - 24,
    top: touchY.value - 24,
    opacity: isPressing.value,
    transform: [{ scale: isPressing.value }],
  }));

  const handleManualClick = (button: 'left' | 'right') => {
    wsClient.send({ type: 'mouse_click', button, clicks: 1 });
  };

  const isConnected = connectionStatus === 'connected';

  return (
    <ScrollView style={styles.screen} contentContainerStyle={{ paddingBottom: Spacing.xl }}>
      {/* Top status row */}
      <View style={styles.statusRow}>
        <View style={styles.statusBadge}>
          <View
            style={[
              styles.dot,
              { backgroundColor: isConnected ? '#2E7D32' : palette.outline },
            ]}
          />
          <Text style={styles.statusText}>
            {isConnected ? activeDevice?.hostname : 'Not connected'}
          </Text>
        </View>

        <TouchableOpacity
          style={[
            styles.iconBtn,
            showScreenViewport && { backgroundColor: palette.primaryContainer },
            { marginRight: Spacing.xs },
          ]}
          onPress={() => setShowScreenViewport(!showScreenViewport)}
        >
          <Tv
            color={showScreenViewport ? palette.primary : palette.onSurfaceVariant}
            size={20}
          />
        </TouchableOpacity>

        <TouchableOpacity style={styles.iconBtn} onPress={() => setShowHelp(!showHelp)}>
          <CircleHelp color={palette.onSurfaceVariant} size={20} />
        </TouchableOpacity>
      </View>

      {/* Embedded Desktop Viewport (if toggled) */}
      {showScreenViewport && (
        <DesktopViewport streamPort={8080} interactive={true} />
      )}

      {/* Help card */}
      {showHelp && (
        <View style={styles.helpCard}>
          <Text style={styles.helpTitle}>Gestures</Text>
          {[
            ['Drag 1 finger', 'Move cursor'],
            ['1-finger tap', 'Left click'],
            ['2-finger tap', 'Right click'],
            ['Double tap', 'Double click'],
            ['Drag 2 fingers', 'Scroll'],
          ].map(([k, v]) => (
            <View key={k} style={styles.helpRow}>
              <Text style={styles.helpKey}>{k}</Text>
              <Text style={styles.helpVal}>{v}</Text>
            </View>
          ))}
        </View>
      )}

      {/* Trackpad surface */}
      <GestureDetector gesture={composed}>
        <View style={[styles.trackpad, !isConnected && styles.trackpadOff]}>
          {!isConnected && (
            <View style={styles.disabledOverlay}>
              <MousePointer color={palette.outline} size={56} />
              <Text style={styles.disabledTitle}>Trackpad inactive</Text>
              <Text style={styles.disabledSub}>Connect a device first.</Text>
            </View>
          )}
          <Animated.View style={[styles.touchDot, indicatorStyle]} />
        </View>
      </GestureDetector>

      {/* Sensitivity segmented control */}
      <View style={styles.surface}>
        <View style={styles.surfaceHeader}>
          <Text style={styles.surfaceTitle}>Sensitivity</Text>
          <Text style={styles.surfaceValue}>{sensitivity.toFixed(1)}×</Text>
        </View>
        <View style={styles.segmented}>
          {SENSITIVITY_LEVELS.map(s => {
            const active = sensitivity === s;
            return (
              <TouchableOpacity
                key={s}
                style={[styles.segment, active && styles.segmentActive]}
                onPress={() => setSensitivity(s)}
              >
                <Text style={[styles.segmentText, active && styles.segmentTextActive]}>
                  {s}×
                </Text>
              </TouchableOpacity>
            );
          })}
        </View>
      </View>

      {/* Click buttons */}
      <View style={styles.clickRow}>
        <TouchableOpacity
          style={[styles.clickBtn, !isConnected && styles.clickBtnOff]}
          disabled={!isConnected}
          onPress={() => handleManualClick('left')}
        >
          <MousePointerClick
            color={isConnected ? palette.onPrimary : palette.outline}
            size={18}
            style={{ marginRight: 8 }}
          />
          <Text style={[styles.clickText, !isConnected && styles.clickTextOff]}>Left click</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.clickBtn, styles.clickBtnTonal, !isConnected && styles.clickBtnOff]}
          disabled={!isConnected}
          onPress={() => handleManualClick('right')}
        >
          <MousePointerClick
            color={isConnected ? palette.onSecondaryContainer : palette.outline}
            size={18}
            style={{ marginRight: 8 }}
          />
          <Text
            style={[
              styles.clickText,
              { color: isConnected ? palette.onSecondaryContainer : palette.outline },
            ]}
          >
            Right click
          </Text>
        </TouchableOpacity>
      </View>

      {/* Remote Keyboard Section */}
      <View style={[styles.surface, { marginTop: Spacing.sm }]}>
        <View style={styles.surfaceHeader}>
          <Text style={styles.surfaceTitle}>Remote Keyboard</Text>
          <TouchableOpacity
            style={styles.kbToggleBtn}
            onPress={() => setShowKeyboardInput(!showKeyboardInput)}
          >
            <KeyboardIcon size={16} color={palette.primary} style={{ marginRight: 4 }} />
            <Text style={styles.kbToggleText}>
              {showKeyboardInput ? 'Hide Input' : 'Type Text'}
            </Text>
          </TouchableOpacity>
        </View>

        {showKeyboardInput && (
          <View style={styles.inputRow}>
            <TextInput
              style={styles.textInput}
              placeholder="Type message to PC..."
              placeholderTextColor={palette.outline}
              value={inputText}
              onChangeText={setInputText}
              onSubmitEditing={handleSendText}
            />
            <TouchableOpacity style={styles.sendBtn} onPress={handleSendText}>
              <Send size={16} color={palette.onPrimary} />
            </TouchableOpacity>
          </View>
        )}

        <View style={styles.keyGrid}>
          <TouchableOpacity style={styles.keyBtn} onPress={() => handleKeyPress('enter')}>
            <CornerDownLeft size={14} color={palette.onSurface} style={{ marginRight: 4 }} />
            <Text style={styles.keyBtnText}>Enter</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.keyBtn} onPress={() => handleKeyPress('backspace')}>
            <Delete size={14} color={palette.onSurface} style={{ marginRight: 4 }} />
            <Text style={styles.keyBtnText}>Backspace</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.keyBtn} onPress={() => handleKeyPress('space')}>
            <Space size={14} color={palette.onSurface} style={{ marginRight: 4 }} />
            <Text style={styles.keyBtnText}>Space</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.keyBtn} onPress={() => handleKeyPress('tab')}>
            <Text style={styles.keyBtnText}>Tab</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.keyBtn} onPress={() => handleKeyPress('escape')}>
            <Text style={styles.keyBtnText}>Esc</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.keyBtn} onPress={() => handleKeyCombo(['ctrl', 'c'])}>
            <Text style={styles.keyBtnText}>Ctrl+C</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.keyBtn} onPress={() => handleKeyCombo(['ctrl', 'v'])}>
            <Text style={styles.keyBtnText}>Ctrl+V</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.keyBtn} onPress={() => handleKeyPress('win')}>
            <Command size={14} color={palette.onSurface} style={{ marginRight: 4 }} />
            <Text style={styles.keyBtnText}>Win</Text>
          </TouchableOpacity>
        </View>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: palette.background,
    padding: Spacing.md,
  },

  statusRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: Spacing.sm,
  },
  statusBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: palette.surfaceContainer,
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.xs,
    borderRadius: Radius.full,
    flex: 1,
    marginRight: Spacing.xs,
  },
  dot: { width: 8, height: 8, borderRadius: 4, marginRight: Spacing.xs },
  statusText: {
    ...Typography.labelLarge,
    color: palette.onSurface,
  },
  iconBtn: {
    width: 40,
    height: 40,
    borderRadius: Radius.full,
    backgroundColor: palette.surfaceContainer,
    alignItems: 'center',
    justifyContent: 'center',
  },

  helpCard: {
    backgroundColor: palette.surfaceContainer,
    borderRadius: Radius.lg,
    padding: Spacing.md,
    marginBottom: Spacing.sm,
    ...Elevation.level1,
  },
  helpTitle: {
    ...Typography.titleSmall,
    color: palette.onSurface,
    marginBottom: Spacing.xs,
  },
  helpRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 4,
  },
  helpKey: { ...Typography.bodySmall, color: palette.primary },
  helpVal: { ...Typography.bodySmall, color: palette.onSurfaceVariant },

  trackpad: {
    width: '100%',
    aspectRatio: 4 / 3,
    backgroundColor: palette.surfaceContainerLow,
    borderWidth: 1,
    borderColor: palette.outlineVariant,
    borderRadius: Radius.xl,
    overflow: 'hidden',
    position: 'relative',
    marginVertical: Spacing.sm,
  },
  trackpadOff: {
    backgroundColor: palette.surfaceContainerLowest,
    borderColor: palette.outlineVariant,
  },
  disabledOverlay: {
    ...StyleSheet.absoluteFill,
    alignItems: 'center',
    justifyContent: 'center',
  },
  disabledTitle: {
    ...Typography.titleMedium,
    color: palette.onSurfaceVariant,
    marginTop: Spacing.sm,
  },
  disabledSub: {
    ...Typography.bodySmall,
    color: palette.outline,
  },
  touchDot: {
    position: 'absolute',
    width: 48,
    height: 48,
    borderRadius: Radius.full,
    backgroundColor: palette.primaryContainer,
    borderWidth: 2,
    borderColor: palette.primary,
  },

  surface: {
    backgroundColor: palette.surfaceContainer,
    borderRadius: Radius.lg,
    padding: Spacing.md,
    marginBottom: Spacing.sm,
    ...Elevation.level1,
  },
  surfaceHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: Spacing.sm,
  },
  surfaceTitle: { ...Typography.titleSmall, color: palette.onSurface },
  surfaceValue: { ...Typography.titleSmall, color: palette.primary },

  segmented: {
    flexDirection: 'row',
    backgroundColor: palette.surfaceContainerHighest,
    borderRadius: Radius.full,
    padding: 4,
    gap: 4,
  },
  segment: {
    flex: 1,
    paddingVertical: Spacing.xs,
    alignItems: 'center',
    borderRadius: Radius.full,
  },
  segmentActive: {
    backgroundColor: palette.primary,
  },
  segmentText: { ...Typography.labelMedium, color: palette.onSurfaceVariant },
  segmentTextActive: { color: palette.onPrimary },

  clickRow: {
    flexDirection: 'row',
    gap: Spacing.sm,
    marginBottom: Spacing.xs,
  },
  clickBtn: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: palette.primary,
    paddingVertical: 14,
    borderRadius: Radius.full,
  },
  clickBtnTonal: { backgroundColor: palette.secondaryContainer },
  clickBtnOff: { backgroundColor: palette.surfaceContainerHighest },
  clickText: { ...Typography.labelLarge, color: palette.onPrimary },
  clickTextOff: { color: palette.outline },

  kbToggleBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: palette.surfaceContainerHighest,
    paddingHorizontal: Spacing.md,
    paddingVertical: 6,
    borderRadius: Radius.full,
  },
  kbToggleText: { ...Typography.labelMedium, color: palette.primary },

  inputRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.xs,
    marginBottom: Spacing.sm,
  },
  textInput: {
    flex: 1,
    backgroundColor: palette.surfaceContainerHighest,
    borderRadius: Radius.full,
    paddingHorizontal: Spacing.md,
    paddingVertical: 8,
    color: palette.onSurface,
    ...Typography.bodyMedium,
  },
  sendBtn: {
    width: 38,
    height: 38,
    borderRadius: 19,
    backgroundColor: palette.primary,
    alignItems: 'center',
    justifyContent: 'center',
  },

  keyGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
  },
  keyBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: palette.surfaceContainerHighest,
    paddingHorizontal: 10,
    paddingVertical: 8,
    borderRadius: Radius.sm,
  },
  keyBtnText: { ...Typography.labelMedium, color: palette.onSurface },
});
