import React, { useRef, useState } from 'react';
import {
  StyleSheet,
  Text,
  View,
  TextInput,
  TouchableOpacity,
  ScrollView,
  NativeSyntheticEvent,
  TextInputKeyPressEventData,
} from 'react-native';
import {
  ChevronUp,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Delete,
  CornerDownLeft,
  Keyboard as KeyboardIcon,
  Copy,
  ClipboardPaste,
  Undo2,
  Check,
  Send,
} from 'lucide-react-native';
import { useDeviceStore } from '../../src/store/deviceStore';
import wsClient from '../../src/ws/client';
import DesktopViewport from '../../components/DesktopViewport';
import { palette, Spacing, Radius, Typography, Elevation } from '../../constants/theme-m3';

export default function KeyboardScreen() {
  const connectionStatus = useDeviceStore(state => state.connectionStatus);
  const isConnected = connectionStatus === 'connected';

  const inputRef = useRef<TextInput>(null);
  const [inputValue, setInputValue] = useState(' ');
  const [quickText, setQuickText] = useState('');
  const [keyboardOpen, setKeyboardOpen] = useState(false);

  const focusInput = () => {
    if (isConnected && inputRef.current) {
      inputRef.current.focus();
      setKeyboardOpen(true);
    }
  };

  const handleTextChange = (text: string) => {
    // If text is empty or shorter than the dummy space, backspace was pressed
    if (text === '' || text.length < inputValue.length) {
      wsClient.send({ type: 'key_press', key: 'backspace' });
      setInputValue(' ');
      return;
    }

    // Extract newly typed characters
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
    if (quickText.length > 0) {
      wsClient.send({ type: 'keyboard_type', text: quickText });
      setQuickText('');
    }
  };

  const pressKey = (key: string) => wsClient.send({ type: 'key_press', key });

  const sendShortcut = (combo: string) => {
    const map: Record<string, string[]> = {
      copy: ['ctrl', 'c'],
      paste: ['ctrl', 'v'],
      undo: ['ctrl', 'z'],
      selectall: ['ctrl', 'a'],
    };
    wsClient.send({ type: 'hotkey', keys: map[combo] ?? [] });
  };

  return (
    <View style={styles.screen}>
      {/* Real-time Desktop Viewport Scene */}
      <DesktopViewport streamPort={8080} interactive={false} />

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

      <ScrollView contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>
        {/* Connection warning — M3 error container */}
        {!isConnected && (
          <View style={styles.warningBanner}>
            <Text style={styles.warningText}>Not connected. Pair a PC to use the keyboard.</Text>
          </View>
        )}

        {/* Keyboard trigger surface */}
        <TouchableOpacity
          style={[styles.trigger, !isConnected && styles.triggerOff]}
          disabled={!isConnected}
          onPress={focusInput}
        >
          <KeyboardIcon
            color={isConnected ? palette.primary : palette.outline}
            size={40}
            style={{ marginBottom: Spacing.xs }}
          />
          <Text style={[styles.triggerText, !isConnected && styles.triggerTextOff]}>
            {keyboardOpen ? 'Mobile keyboard active — type anywhere' : 'Tap to open phone keyboard'}
          </Text>
        </TouchableOpacity>

        {/* Quick Text Input Box */}
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>Quick text &amp; URL sender</Text>
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

        {/* System keys */}
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>System keys</Text>
          <View style={styles.row}>
            {[
              { label: 'ESC', icon: null, action: () => pressKey('esc') },
              { label: 'TAB', icon: null, action: () => pressKey('tab') },
              { label: null, icon: <Delete color={palette.onSurface} size={18} />, action: () => pressKey('backspace') },
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
              { label: 'Copy', icon: <Copy color={palette.primary} size={16} />, action: () => sendShortcut('copy') },
              { label: 'Paste', icon: <ClipboardPaste color={palette.primary} size={16} />, action: () => sendShortcut('paste') },
              { label: 'Undo', icon: <Undo2 color={palette.primary} size={16} />, action: () => sendShortcut('undo') },
              { label: 'All', icon: <Check color={palette.primary} size={16} />, action: () => sendShortcut('selectall') },
            ].map((k, i) => (
              <KeyButton key={i} label={k.label} icon={k.icon} onPress={k.action} disabled={!isConnected} tonal />
            ))}
          </View>
        </View>

        {/* D-pad */}
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>Navigation</Text>
          <View style={styles.dpadCol}>
            <DPadButton icon={<ChevronUp color={palette.onSurface} size={26} />} onPress={() => pressKey('up')} disabled={!isConnected} />
            <View style={styles.dpadMid}>
              <DPadButton icon={<ChevronLeft color={palette.onSurface} size={26} />} onPress={() => pressKey('left')} disabled={!isConnected} />
              <View style={styles.dpadSpacer} />
              <DPadButton icon={<ChevronRight color={palette.onSurface} size={26} />} onPress={() => pressKey('right')} disabled={!isConnected} />
            </View>
            <DPadButton icon={<ChevronDown color={palette.onSurface} size={26} />} onPress={() => pressKey('down')} disabled={!isConnected} />
          </View>
        </View>
      </ScrollView>
    </View>
  );
}

/* --- Small reusable key button --- */
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
  scrollContent: {
    padding: Spacing.md,
    paddingBottom: Spacing.xxl,
  },
  hiddenInput: {
    position: 'absolute',
    top: -100,
    left: -100,
    width: 10,
    height: 10,
    opacity: 0.01,
  },

  warningBanner: {
    backgroundColor: palette.errorContainer,
    borderRadius: Radius.md,
    padding: Spacing.sm,
    marginBottom: Spacing.md,
  },
  warningText: {
    ...Typography.bodyMedium,
    color: palette.onErrorContainer,
    textAlign: 'center',
  },

  trigger: {
    backgroundColor: palette.surfaceContainer,
    borderRadius: Radius.lg,
    paddingVertical: Spacing.lg,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: Spacing.md,
    ...Elevation.level1,
  },
  triggerOff: {
    backgroundColor: palette.surfaceContainerLow,
  },
  triggerText: {
    ...Typography.titleMedium,
    color: palette.onSurface,
  },
  triggerTextOff: {
    color: palette.outline,
  },

  section: { marginBottom: Spacing.md },
  sectionLabel: {
    ...Typography.labelMedium,
    color: palette.onSurfaceVariant,
    textTransform: 'uppercase',
    letterSpacing: 0.8,
    marginBottom: Spacing.xs,
  },

  quickTextRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.xs,
  },
  quickTextInput: {
    flex: 1,
    height: 48,
    backgroundColor: palette.surfaceContainerHigh,
    borderRadius: Radius.md,
    paddingHorizontal: Spacing.md,
    color: palette.onSurface,
    ...Typography.bodyMedium,
  },
  sendBtn: {
    width: 48,
    height: 48,
    borderRadius: Radius.md,
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
    height: 52,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: palette.surfaceContainerHigh,
    borderRadius: Radius.md,
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
    ...Typography.labelLarge,
    color: palette.onSurface,
  },

  dpadCol: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  dpadMid: { flexDirection: 'row' },
  dpadSpacer: { width: 8 },
  dpadBtn: {
    width: 68,
    height: 56,
    borderRadius: Radius.lg,
    backgroundColor: palette.surfaceContainerHigh,
    alignItems: 'center',
    justifyContent: 'center',
    marginVertical: 4,
    marginHorizontal: 4,
  },
});
