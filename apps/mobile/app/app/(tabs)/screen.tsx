import React, { useState, useRef } from 'react';
import {
  StyleSheet,
  Text,
  View,
  TouchableOpacity,
  ScrollView,
  TextInput,
  Modal,
  NativeSyntheticEvent,
  TextInputKeyPressEventData,
} from 'react-native';
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
  Keyboard as KeyboardIcon,
  Send,
  CornerDownLeft,
  Delete,
  Copy,
  ClipboardPaste,
  Undo2,
  Check,
  ChevronUp,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  X,
  Tv,
} from 'lucide-react-native';
import DesktopViewport from '../../components/DesktopViewport';
import { useDeviceStore } from '../../src/store/deviceStore';
import wsClient from '../../src/ws/client';
import { palette, Spacing, Radius, Typography, Elevation } from '../../constants/theme-m3';

const SENSITIVITY_LEVELS = [1.0, 1.5, 2.5, 5.0, 10.0, 15.0];

export default function ConsolidatedRemoteScreen() {
  const connectionStatus = useDeviceStore(state => state.connectionStatus);
  const activeDevice = useDeviceStore(state => state.activeDevice);
  const isConnected = connectionStatus === 'connected';

  // UI state
  const [sensitivity, setSensitivity] = useState(1.5);
  const [showHelp, setShowHelp] = useState(false);
  const [showKeyboardModal, setShowKeyboardModal] = useState(false);

  // Keyboard state
  const inputRef = useRef<TextInput>(null);
  const [inputValue, setInputValue] = useState(' ');
  const [quickText, setQuickText] = useState('');
  const [keyboardOpen, setKeyboardOpen] = useState(false);

  // ---------------------------------------------------------------------------
  // Keyboard actions
  // ---------------------------------------------------------------------------
  const focusInput = () => {
    if (isConnected && inputRef.current) {
      inputRef.current.focus();
      setKeyboardOpen(true);
    }
  };

  const handleTextChange = (text: string) => {
    if (text === '' || text.length < inputValue.length) {
      wsClient.send({ type: 'key_press', key: 'backspace' });
      setInputValue(' ');
      return;
    }
    const typed = text.startsWith(' ') ? text.slice(1) : text;
    if (typed.length > 0) {
      wsClient.send({ type: 'keyboard_type', text: typed });
    }
    setInputValue(' ');
  };

  const handleKeyPress = (e: NativeSyntheticEvent<TextInputKeyPressEventData>) => {
    const key = e.nativeEvent.key;
    if (key === 'Backspace') {
      wsClient.send({ type: 'key_press', key: 'backspace' });
      setInputValue(' ');
    } else if (key === 'Enter') {
      wsClient.send({ type: 'key_press', key: 'enter' });
      setInputValue(' ');
    } else if (key === 'Tab') {
      wsClient.send({ type: 'key_press', key: 'tab' });
      setInputValue(' ');
    }
  };

  const handleSendQuickText = () => {
    if (!quickText) return;
    wsClient.send({ type: 'keyboard_type', text: quickText });
    setQuickText('');
  };

  const pressKey = (key: string) => {
    wsClient.send({ type: 'key_press', key });
  };

  const sendShortcut = (combo: string) => {
    const map: Record<string, string[]> = {
      copy: ['ctrl', 'c'],
      paste: ['ctrl', 'v'],
      undo: ['ctrl', 'z'],
      selectall: ['ctrl', 'a'],
      desktop: ['win', 'd'],
      taskmgr: ['ctrl', 'shift', 'esc'],
      switch: ['alt', 'tab'],
      lock: ['win', 'l'],
    };
    wsClient.send({ type: 'hotkey', keys: map[combo] ?? [] });
  };

  const handleManualClick = (button: 'left' | 'right') => {
    wsClient.send({ type: 'mouse_click', button, clicks: 1 });
  };

  // ---------------------------------------------------------------------------
  // Trackpad Gesture Handling
  // ---------------------------------------------------------------------------
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

  const composedGesture = Gesture.Race(
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

  return (
    <View style={styles.screen}>
      {/* Hidden input for software keyboard capture */}
      <TextInput
        ref={inputRef}
        style={styles.hiddenInput}
        value={inputValue}
        onChangeText={handleTextChange}
        onKeyPress={handleKeyPress}
        onSubmitEditing={() => pressKey('enter')}
        autoCorrect={false}
        autoCapitalize="none"
        keyboardType="default"
        blurOnSubmit={false}
        onBlur={() => setKeyboardOpen(false)}
      />

      <ScrollView
        style={styles.scroll}
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        {/* Top Status & Action Bar */}
        <View style={styles.topRow}>
          <View style={styles.statusBadge}>
            <View
              style={[
                styles.dot,
                { backgroundColor: isConnected ? '#2E7D32' : palette.outline },
              ]}
            />
            <Text style={styles.statusText} numberOfLines={1}>
              {isConnected ? activeDevice?.hostname : 'Not connected'}
            </Text>
          </View>

          {/* Quick Keyboard Drawer Toggle */}
          <TouchableOpacity
            style={[
              styles.iconBtn,
              showKeyboardModal && { backgroundColor: palette.primaryContainer },
            ]}
            onPress={() => setShowKeyboardModal(true)}
          >
            <KeyboardIcon
              color={showKeyboardModal ? palette.primary : palette.onSurfaceVariant}
              size={20}
            />
          </TouchableOpacity>

          {/* Help button */}
          <TouchableOpacity
            style={[styles.iconBtn, showHelp && { backgroundColor: palette.surfaceContainerHigh }]}
            onPress={() => setShowHelp(!showHelp)}
          >
            <CircleHelp color={palette.onSurfaceVariant} size={20} />
          </TouchableOpacity>
        </View>

        {/* Gestures Help Card (Collapsible) */}
        {showHelp && (
          <View style={styles.helpCard}>
            <Text style={styles.helpTitle}>Touch Gestures &amp; Shortcuts</Text>
            {[
              ['Tap Viewport', 'Click directly at desktop coordinates'],
              ['Drag 1 Finger (Trackpad)', 'Move cursor smoothly'],
              ['1-Finger Tap (Trackpad)', 'Left click'],
              ['2-Finger Tap (Trackpad)', 'Right click'],
              ['Double Tap (Trackpad)', 'Double click'],
              ['Drag 2 Fingers (Trackpad)', 'Scroll page up / down'],
            ].map(([k, v]) => (
              <View key={k} style={styles.helpRow}>
                <Text style={styles.helpKey}>{k}</Text>
                <Text style={styles.helpVal}>{v}</Text>
              </View>
            ))}
          </View>
        )}

        {/* 1. Live Screen Mirror (DesktopViewport) */}
        <View style={styles.viewportContainer}>
          <DesktopViewport streamPort={8080} interactive={true} />
        </View>

        {/* 2. Trackpad Header & Sensitivity Row */}
        <View style={styles.trackpadHeader}>
          <View style={styles.trackpadTitleRow}>
            <MousePointer size={16} color={palette.primary} style={{ marginRight: 6 }} />
            <Text style={styles.sectionTitle}>Trackpad</Text>
            <Text style={styles.sensitivityBadge}>{sensitivity.toFixed(1)}×</Text>
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

        {/* 3. Dedicated Trackpad Surface */}
        <GestureDetector gesture={composedGesture}>
          <View style={[styles.trackpad, !isConnected && styles.trackpadOff]}>
            {!isConnected && (
              <View style={styles.disabledOverlay}>
                <MousePointer color={palette.outline} size={44} />
                <Text style={styles.disabledTitle}>Trackpad offline</Text>
                <Text style={styles.disabledSub}>Pair PC in Devices tab to control cursor.</Text>
              </View>
            )}
            <Animated.View style={[styles.touchDot, indicatorStyle]} />
          </View>
        </GestureDetector>

        {/* 4. Physical Left & Right Click Buttons */}
        <View style={styles.clickRow}>
          <TouchableOpacity
            style={[styles.clickBtn, !isConnected && styles.clickBtnOff]}
            disabled={!isConnected}
            onPress={() => handleManualClick('left')}
            activeOpacity={0.7}
          >
            <MousePointerClick
              color={isConnected ? palette.onPrimary : palette.outline}
              size={18}
              style={{ marginRight: 8 }}
            />
            <Text style={[styles.clickText, !isConnected && styles.clickTextOff]}>Left Click</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.clickBtn, styles.clickBtnTonal, !isConnected && styles.clickBtnOff]}
            disabled={!isConnected}
            onPress={() => handleManualClick('right')}
            activeOpacity={0.7}
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
              Right Click
            </Text>
          </TouchableOpacity>
        </View>

        {/* 5. Quick Keyboard Launch Banner */}
        <TouchableOpacity
          style={[styles.kbBanner, !isConnected && styles.kbBannerOff]}
          disabled={!isConnected}
          onPress={() => setShowKeyboardModal(true)}
          activeOpacity={0.8}
        >
          <KeyboardIcon color={isConnected ? palette.primary : palette.outline} size={22} />
          <View style={{ flex: 1, marginLeft: Spacing.sm }}>
            <Text style={[styles.kbBannerTitle, !isConnected && { color: palette.outline }]}>
              Remote Keyboard &amp; Shortcuts
            </Text>
            <Text style={styles.kbBannerSub}>
              Type text, use navigation keys (ESC/TAB/Enter), or send shortcuts (Ctrl+C, Alt+Tab).
            </Text>
          </View>
        </TouchableOpacity>
      </ScrollView>

      {/* --------------------------------------------------------------------- */}
      {/* On-Screen Keyboard Drawer / Modal                                     */}
      {/* --------------------------------------------------------------------- */}
      <Modal
        visible={showKeyboardModal}
        animationType="slide"
        transparent={true}
        onRequestClose={() => setShowKeyboardModal(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            {/* Modal Header */}
            <View style={styles.modalHeader}>
              <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
                <KeyboardIcon color={palette.primary} size={22} />
                <Text style={styles.modalTitle}>Remote Keyboard</Text>
              </View>
              <TouchableOpacity
                style={styles.closeBtn}
                onPress={() => setShowKeyboardModal(false)}
              >
                <X color={palette.onSurface} size={20} />
              </TouchableOpacity>
            </View>

            <ScrollView showsVerticalScrollIndicator={false}>
              {/* Native Keyboard Trigger Button */}
              <TouchableOpacity
                style={[styles.trigger, !isConnected && styles.triggerOff]}
                disabled={!isConnected}
                onPress={focusInput}
              >
                <KeyboardIcon
                  color={isConnected ? palette.primary : palette.outline}
                  size={32}
                  style={{ marginBottom: 4 }}
                />
                <Text style={[styles.triggerText, !isConnected && styles.triggerTextOff]}>
                  {keyboardOpen ? 'Phone keyboard active — type anywhere' : 'Tap to open phone keyboard'}
                </Text>
              </TouchableOpacity>

              {/* Quick Text Sender */}
              <View style={styles.section}>
                <Text style={styles.sectionLabel}>Quick Text &amp; URL Sender</Text>
                <View style={styles.quickTextRow}>
                  <TextInput
                    style={styles.quickTextInput}
                    placeholder="Type or paste text to send to PC..."
                    placeholderTextColor={palette.outline}
                    value={quickText}
                    onChangeText={setQuickText}
                    editable={isConnected}
                    onSubmitEditing={handleSendQuickText}
                  />
                  <TouchableOpacity
                    style={[styles.sendBtn, (!isConnected || !quickText) && styles.sendBtnDisabled]}
                    onPress={handleSendQuickText}
                    disabled={!isConnected || !quickText}
                  >
                    <Send color={palette.onPrimary} size={18} />
                  </TouchableOpacity>
                </View>
              </View>

              {/* System Keys */}
              <View style={styles.section}>
                <Text style={styles.sectionLabel}>System Keys</Text>
                <View style={styles.row}>
                  {[
                    { label: 'ESC', icon: null, action: () => pressKey('esc') },
                    { label: 'TAB', icon: null, action: () => pressKey('tab') },
                    {
                      label: null,
                      icon: <Delete color={palette.onSurface} size={18} />,
                      action: () => pressKey('backspace'),
                    },
                    {
                      label: 'Enter',
                      icon: <CornerDownLeft color={palette.onPrimary} size={16} style={{ marginRight: 4 }} />,
                      action: () => pressKey('enter'),
                      primary: true,
                    },
                  ].map((k, i) => (
                    <KeyButton
                      key={i}
                      label={k.label}
                      icon={k.icon}
                      onPress={k.action}
                      disabled={!isConnected}
                      primary={k.primary}
                    />
                  ))}
                </View>
              </View>

              {/* Shortcuts */}
              <View style={styles.section}>
                <Text style={styles.sectionLabel}>Shortcuts</Text>
                <View style={styles.row}>
                  {[
                    { label: 'Copy', icon: <Copy color={palette.primary} size={15} />, action: () => sendShortcut('copy') },
                    { label: 'Paste', icon: <ClipboardPaste color={palette.primary} size={15} />, action: () => sendShortcut('paste') },
                    { label: 'Undo', icon: <Undo2 color={palette.primary} size={15} />, action: () => sendShortcut('undo') },
                    { label: 'All', icon: <Check color={palette.primary} size={15} />, action: () => sendShortcut('selectall') },
                  ].map((k, i) => (
                    <KeyButton key={i} label={k.label} icon={k.icon} onPress={k.action} disabled={!isConnected} tonal />
                  ))}
                </View>
                <View style={[styles.row, { marginTop: 6 }]}>
                  {[
                    { label: 'Desktop', icon: null, action: () => sendShortcut('desktop') },
                    { label: 'Switch', icon: null, action: () => sendShortcut('switch') },
                    { label: 'Tasks', icon: null, action: () => sendShortcut('taskmgr') },
                    { label: 'Lock', icon: null, action: () => sendShortcut('lock') },
                  ].map((k, i) => (
                    <KeyButton key={i} label={k.label} icon={k.icon} onPress={k.action} disabled={!isConnected} tonal />
                  ))}
                </View>
              </View>

              {/* Navigation D-Pad */}
              <View style={styles.section}>
                <Text style={styles.sectionLabel}>Navigation D-Pad</Text>
                <View style={styles.dpadCol}>
                  <DPadButton icon={<ChevronUp color={palette.onSurface} size={24} />} onPress={() => pressKey('up')} disabled={!isConnected} />
                  <View style={styles.dpadMid}>
                    <DPadButton icon={<ChevronLeft color={palette.onSurface} size={24} />} onPress={() => pressKey('left')} disabled={!isConnected} />
                    <View style={styles.dpadSpacer} />
                    <DPadButton icon={<ChevronRight color={palette.onSurface} size={24} />} onPress={() => pressKey('right')} disabled={!isConnected} />
                  </View>
                  <DPadButton icon={<ChevronDown color={palette.onSurface} size={24} />} onPress={() => pressKey('down')} disabled={!isConnected} />
                </View>
              </View>
            </ScrollView>
          </View>
        </View>
      </Modal>
    </View>
  );
}

/* --- Reusable Components for Keyboard Modal --- */
function KeyButton({
  label,
  icon,
  onPress,
  disabled,
  primary = false,
  tonal = false,
}: {
  label: string | null;
  icon: React.ReactNode;
  onPress: () => void;
  disabled?: boolean;
  primary?: boolean;
  tonal?: boolean;
}) {
  return (
    <TouchableOpacity
      style={[
        styles.key,
        primary && styles.keyPrimary,
        tonal && styles.keyTonal,
        disabled && styles.keyOff,
      ]}
      onPress={onPress}
      disabled={disabled}
      activeOpacity={0.7}
    >
      {icon}
      {label && (
        <Text
          style={[
            styles.keyText,
            primary && { color: palette.onPrimary },
            tonal && { color: palette.onSecondaryContainer },
            disabled && { color: palette.outline },
          ]}
        >
          {label}
        </Text>
      )}
    </TouchableOpacity>
  );
}

function DPadButton({
  icon,
  onPress,
  disabled,
}: {
  icon: React.ReactNode;
  onPress: () => void;
  disabled?: boolean;
}) {
  return (
    <TouchableOpacity
      style={[styles.dpadBtn, disabled && styles.keyOff]}
      onPress={onPress}
      disabled={disabled}
      activeOpacity={0.7}
    >
      {icon}
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: palette.background,
  },
  scroll: {
    flex: 1,
  },
  scrollContent: {
    padding: Spacing.md,
    paddingBottom: Spacing.xxxl,
  },
  hiddenInput: {
    position: 'absolute',
    top: -100,
    left: -100,
    width: 10,
    height: 10,
    opacity: 0.01,
  },

  /* Top Bar */
  topRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: Spacing.sm,
    gap: Spacing.xs,
  },
  statusBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: palette.surfaceContainer,
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.xs,
    borderRadius: Radius.full,
    flex: 1,
  },
  dot: { width: 8, height: 8, borderRadius: 4, marginRight: Spacing.xs },
  statusText: {
    ...Typography.labelLarge,
    color: palette.onSurface,
  },
  iconBtn: {
    width: 38,
    height: 38,
    borderRadius: Radius.full,
    backgroundColor: palette.surfaceContainer,
    alignItems: 'center',
    justifyContent: 'center',
  },

  /* Help Card */
  helpCard: {
    backgroundColor: palette.surfaceContainer,
    borderRadius: Radius.md,
    padding: Spacing.md,
    marginBottom: Spacing.md,
    borderLeftWidth: 4,
    borderLeftColor: palette.primary,
  },
  helpTitle: {
    ...Typography.titleSmall,
    color: palette.onSurface,
    marginBottom: Spacing.xs,
    fontWeight: '700',
  },
  helpRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 3,
  },
  helpKey: { ...Typography.bodySmall, color: palette.primary, fontWeight: '600' },
  helpVal: { ...Typography.bodySmall, color: palette.onSurfaceVariant },

  /* Viewport Container */
  viewportContainer: {
    marginBottom: Spacing.sm,
  },

  /* Trackpad */
  trackpadHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginTop: Spacing.xs,
    marginBottom: Spacing.xs,
  },
  trackpadTitleRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  sectionTitle: {
    ...Typography.titleSmall,
    color: palette.onSurface,
    fontWeight: '700',
  },
  sensitivityBadge: {
    ...Typography.labelSmall,
    backgroundColor: palette.surfaceContainerHigh,
    color: palette.primary,
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: Radius.xs,
    marginLeft: 6,
    fontWeight: '600',
  },
  segmented: {
    flexDirection: 'row',
    backgroundColor: palette.surfaceContainer,
    borderRadius: Radius.sm,
    padding: 2,
  },
  segment: {
    paddingHorizontal: 6,
    paddingVertical: 3,
    borderRadius: Radius.xs,
  },
  segmentActive: {
    backgroundColor: palette.primary,
  },
  segmentText: {
    ...Typography.labelSmall,
    color: palette.onSurfaceVariant,
    fontSize: 10,
    fontWeight: '600',
  },
  segmentTextActive: {
    color: palette.onPrimary,
  },

  trackpad: {
    height: 220,
    backgroundColor: palette.surfaceContainerLow,
    borderRadius: Radius.lg,
    overflow: 'hidden',
    position: 'relative',
    borderWidth: 1,
    borderColor: palette.outlineVariant,
    ...Elevation.level1,
  },
  trackpadOff: {
    backgroundColor: palette.surfaceContainerLowest,
  },
  touchDot: {
    position: 'absolute',
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: 'rgba(56, 189, 248, 0.35)',
    borderWidth: 2,
    borderColor: palette.primary,
  },
  disabledOverlay: {
    ...StyleSheet.absoluteFillObject,
    justifyContent: 'center',
    alignItems: 'center',
    padding: Spacing.md,
  },
  disabledTitle: {
    ...Typography.titleSmall,
    color: palette.outline,
    marginTop: Spacing.xs,
  },
  disabledSub: {
    ...Typography.bodySmall,
    color: palette.outline,
    textAlign: 'center',
    marginTop: 2,
  },

  /* Click buttons */
  clickRow: {
    flexDirection: 'row',
    gap: Spacing.sm,
    marginTop: Spacing.sm,
  },
  clickBtn: {
    flex: 1,
    height: 46,
    borderRadius: Radius.md,
    backgroundColor: palette.primary,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
  },
  clickBtnTonal: {
    backgroundColor: palette.secondaryContainer,
  },
  clickBtnOff: {
    backgroundColor: palette.surfaceContainerLowest,
  },
  clickText: {
    ...Typography.labelLarge,
    color: palette.onPrimary,
    fontWeight: '600',
  },
  clickTextOff: {
    color: palette.outline,
  },

  /* Keyboard Banner */
  kbBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: palette.surfaceContainer,
    borderRadius: Radius.md,
    padding: Spacing.md,
    marginTop: Spacing.md,
    borderWidth: 1,
    borderColor: palette.outlineVariant,
  },
  kbBannerOff: {
    backgroundColor: palette.surfaceContainerLowest,
    opacity: 0.6,
  },
  kbBannerTitle: {
    ...Typography.titleSmall,
    color: palette.onSurface,
    fontWeight: '600',
  },
  kbBannerSub: {
    ...Typography.bodySmall,
    color: palette.onSurfaceVariant,
    marginTop: 2,
  },

  /* Modal Sheet */
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.65)',
    justifyContent: 'flex-end',
  },
  modalContent: {
    backgroundColor: palette.surface,
    borderTopLeftRadius: Radius.xl,
    borderTopRightRadius: Radius.xl,
    padding: Spacing.md,
    maxHeight: '85%',
    ...Elevation.level3,
  },
  modalHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingBottom: Spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: palette.outlineVariant,
    marginBottom: Spacing.sm,
  },
  modalTitle: {
    ...Typography.titleMedium,
    color: palette.onSurface,
    fontWeight: '700',
  },
  closeBtn: {
    width: 36,
    height: 36,
    borderRadius: Radius.full,
    backgroundColor: palette.surfaceContainer,
    alignItems: 'center',
    justifyContent: 'center',
  },

  /* Trigger */
  trigger: {
    backgroundColor: palette.surfaceContainer,
    borderRadius: Radius.md,
    paddingVertical: Spacing.md,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: Spacing.sm,
  },
  triggerOff: {
    backgroundColor: palette.surfaceContainerLow,
  },
  triggerText: {
    ...Typography.bodyMedium,
    color: palette.onSurface,
    fontWeight: '500',
  },
  triggerTextOff: {
    color: palette.outline,
  },

  section: {
    marginBottom: Spacing.sm,
  },
  sectionLabel: {
    ...Typography.labelSmall,
    color: palette.onSurfaceVariant,
    textTransform: 'uppercase',
    letterSpacing: 0.8,
    marginBottom: 4,
    fontWeight: '600',
  },

  quickTextRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.xs,
  },
  quickTextInput: {
    flex: 1,
    height: 44,
    backgroundColor: palette.surfaceContainerHigh,
    borderRadius: Radius.sm,
    paddingHorizontal: Spacing.sm,
    color: palette.onSurface,
    ...Typography.bodyMedium,
  },
  sendBtn: {
    width: 44,
    height: 44,
    borderRadius: Radius.sm,
    backgroundColor: palette.primary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  sendBtnDisabled: {
    backgroundColor: palette.surfaceContainerLowest,
    opacity: 0.5,
  },

  row: {
    flexDirection: 'row',
    gap: Spacing.xs,
  },
  key: {
    flex: 1,
    height: 46,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: palette.surfaceContainerHigh,
    borderRadius: Radius.sm,
    paddingHorizontal: Spacing.xs,
  },
  keyPrimary: {
    backgroundColor: palette.primary,
  },
  keyTonal: {
    backgroundColor: palette.secondaryContainer,
  },
  keyOff: {
    backgroundColor: palette.surfaceContainerLowest,
  },
  keyText: {
    ...Typography.labelMedium,
    color: palette.onSurface,
    fontWeight: '600',
  },

  dpadCol: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  dpadMid: { flexDirection: 'row' },
  dpadSpacer: { width: 8 },
  dpadBtn: {
    width: 60,
    height: 48,
    borderRadius: Radius.md,
    backgroundColor: palette.surfaceContainerHigh,
    alignItems: 'center',
    justifyContent: 'center',
    marginVertical: 3,
    marginHorizontal: 3,
  },
});
