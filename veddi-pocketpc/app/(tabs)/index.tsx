import React, { useState } from 'react';
import {
  StyleSheet,
  Text,
  View,
  Image,
  TouchableOpacity,
  TextInput,
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
} from 'react-native';
import { useRouter } from 'expo-router';
import {
  Plus,
  Trash2,
  Power,
  ScanLine,
  Link,
  Monitor,
  CircleAlert,
} from 'lucide-react-native';
import { useDeviceStore, PairedDevice } from '../../src/store/deviceStore';
import wsClient from '../../src/ws/client';
import { pairWithHost, describePairError, cleanIp } from '../../src/ws/pairing';
import { palette, Spacing, Radius, Typography, Elevation } from '../../constants/theme-m3';
import { AppLogo } from '../../constants/assets';

export default function IndexScreen() {
  const router = useRouter();
  const pairedDevices = useDeviceStore(state => state.pairedDevices);
  const activeDevice = useDeviceStore(state => state.activeDevice);
  const connectionStatus = useDeviceStore(state => state.connectionStatus);
  const addDevice = useDeviceStore(state => state.addDevice);
  const removeDevice = useDeviceStore(state => state.removeDevice);
  const setActiveDevice = useDeviceStore(state => state.setActiveDevice);

  const [ip, setIp] = useState('');
  const [port, setPort] = useState('8000');
  const [pin, setPin] = useState('');
  const [loading, setLoading] = useState(false);
  const [showManualForm, setShowManualForm] = useState(false);

  const handleManualPair = async () => {
    const safeIp = cleanIp(ip);
    if (!safeIp || !port) {
      Alert.alert('Error', 'Please fill in a valid IP and Port');
      return;
    }

    setLoading(true);
    try {
      const result = await pairWithHost(safeIp, port, pin);

      if (result.kind === 'ok') {
        await addDevice(result.device);
        setPin('');
        setShowManualForm(false);
        Alert.alert('Paired', `Connected to ${result.hostname}.`);
        wsClient.connect(result.device);
      } else if (result.kind === 'unreachable') {
        const directDevice = {
          ip: safeIp,
          port: 8080,
          token: pin || 'direct',
          hostname: `PC (${safeIp})`,
        };
        await addDevice(directDevice);
        setPin('');
        setShowManualForm(false);
        Alert.alert(
          'Added Device',
          `Backend didn't respond on port ${port}. Configured direct stream at ${safeIp}:8080.`
        );
      } else {
        const { title, body } = describePairError(result);
        Alert.alert(title, body);
      }
    } catch (err) {
      console.error(err);
      Alert.alert('Unexpected error', String((err as Error)?.message ?? err));
    } finally {
      setLoading(false);
    }
  };

  const handleConnectToggle = (device: PairedDevice) => {
    if (activeDevice?.ip === device.ip && connectionStatus === 'connected') {
      wsClient.disconnect();
    } else {
      setActiveDevice(device);
    }
  };

  const handleDeleteDevice = (device: PairedDevice) => {
    Alert.alert(
      'Remove device?',
      `Forget ${device.hostname} (${device.ip})? You can pair again later.`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Remove',
          style: 'destructive',
          onPress: async () => {
            if (activeDevice?.ip === device.ip) wsClient.disconnect();
            await removeDevice(device.ip);
          },
        },
      ]
    );
  };

  const statusColor = {
    connected: '#2E7D32',
    connecting: '#B45309',
    disconnected: palette.outline,
  }[connectionStatus];

  const statusLabel = {
    connected: 'Connected',
    connecting: 'Connecting…',
    disconnected: 'Disconnected',
  }[connectionStatus];

  return (
    <KeyboardAvoidingView
      style={styles.screen}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <ScrollView contentContainerStyle={styles.scroll}>
        {/* Hero Brand Header */}
        <View style={styles.brandHeroCard}>
          <View style={styles.brandHeroLeft}>
            <View style={styles.heroLogoBadge}>
              <Image source={AppLogo} style={styles.heroLogoImage} resizeMode="cover" />
            </View>
            <View>
              <Text style={styles.brandHeroTitle}>Vedi Pocket PC</Text>
              <Text style={styles.brandHeroSubtitle}>Remote Mouse & Display Hub</Text>
            </View>
          </View>
        </View>

        {/* Status card — M3 elevated surface */}
        <View style={styles.statusCard}>
          <View style={styles.statusHeader}>
            <View style={[styles.statusDot, { backgroundColor: statusColor }]} />
            <Text style={styles.statusLabel}>{statusLabel}</Text>
          </View>

          {activeDevice ? (
            <View>
              <Text style={styles.deviceName}>{activeDevice.hostname}</Text>
              <Text style={styles.deviceSub}>
                {activeDevice.ip}:{activeDevice.port}
              </Text>
              <TouchableOpacity
                style={[
                  styles.filledBtn,
                  connectionStatus === 'connected' && styles.filledBtnError,
                ]}
                onPress={() => handleConnectToggle(activeDevice)}
              >
                <Power color={palette.onPrimary} size={18} style={{ marginRight: 8 }} />
                <Text style={styles.filledBtnText}>
                  {connectionStatus === 'connected' ? 'Disconnect' : 'Connect'}
                </Text>
              </TouchableOpacity>
            </View>
          ) : (
            <Text style={styles.emptyActive}>No active connection.</Text>
          )}
        </View>

        {/* Pair actions — M3 button row */}
        <View style={styles.actionRow}>
          <TouchableOpacity style={styles.filledBtn} onPress={() => router.push('/pairing')}>
            <ScanLine color={palette.onPrimary} size={18} style={{ marginRight: 8 }} />
            <Text style={styles.filledBtnText}>Scan QR</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.tonalBtn}
            onPress={() => setShowManualForm(!showManualForm)}
          >
            <Plus color={palette.onSecondaryContainer} size={18} style={{ marginRight: 8 }} />
            <Text style={styles.tonalBtnText}>
              {showManualForm ? 'Hide manual' : 'Add manually'}
            </Text>
          </TouchableOpacity>
        </View>

        {/* Manual entry — M3 filled text fields */}
        {showManualForm && (
          <View style={styles.formCard}>
            <Text style={styles.sectionTitle}>Add PC manually</Text>

            <View style={styles.fieldGroup}>
              <Text style={styles.fieldLabel}>PC local IP</Text>
              <TextInput
                style={styles.input}
                placeholder="e.g. 192.168.1.15"
                placeholderTextColor={palette.outline}
                value={ip}
                onChangeText={setIp}
                keyboardType="numeric"
                autoCapitalize="none"
              />
            </View>

            <View style={styles.fieldRow}>
              <View style={[styles.fieldGroup, { flex: 1, marginRight: Spacing.sm }]}>
                <Text style={styles.fieldLabel}>Port</Text>
                <TextInput
                  style={styles.input}
                  placeholder="8000"
                  placeholderTextColor={palette.outline}
                  value={port}
                  onChangeText={setPort}
                  keyboardType="numeric"
                />
              </View>
              <View style={[styles.fieldGroup, { flex: 1.4 }]}>
                <Text style={styles.fieldLabel}>Pairing PIN</Text>
                <TextInput
                  style={styles.input}
                  placeholder="4-digit"
                  placeholderTextColor={palette.outline}
                  value={pin}
                  onChangeText={setPin}
                  keyboardType="numeric"
                  maxLength={4}
                  secureTextEntry
                />
              </View>
            </View>

            <TouchableOpacity style={styles.filledBtn} onPress={handleManualPair} disabled={loading}>
              {loading ? (
                <ActivityIndicator color={palette.onPrimary} size="small" />
              ) : (
                <>
                  <Link color={palette.onPrimary} size={18} style={{ marginRight: 8 }} />
                  <Text style={styles.filledBtnText}>Verify &amp; pair</Text>
                </>
              )}
            </TouchableOpacity>
          </View>
        )}

        {/* Section header */}
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>Paired devices</Text>
          <View style={styles.countChip}>
            <Text style={styles.countChipText}>{pairedDevices.length}</Text>
          </View>
        </View>

        {pairedDevices.length === 0 ? (
          <View style={styles.emptyState}>
            <CircleAlert color={palette.outline} size={48} />
            <Text style={styles.emptyTitle}>No paired devices yet</Text>
            <Text style={styles.emptySubtitle}>
              Start the agent on your PC, then scan the terminal QR code or enter details
              manually.
            </Text>
          </View>
        ) : (
          <View style={styles.deviceList}>
            {pairedDevices.map(item => {
              const isActive = activeDevice?.ip === item.ip;
              return (
                <View key={item.ip} style={[styles.deviceCard, isActive && styles.deviceCardActive]}>
                  <View style={styles.deviceIcon}>
                    <Monitor color={isActive ? palette.primary : palette.onSurfaceVariant} size={24} />
                  </View>
                  <View style={styles.deviceInfo}>
                    <Text style={styles.deviceCardName}>{item.hostname}</Text>
                    <Text style={styles.deviceCardSub}>
                      {item.ip}:{item.port}
                    </Text>
                  </View>
                  <View style={styles.deviceActions}>
                    <TouchableOpacity
                      style={[
                        styles.iconBtn,
                        isActive && connectionStatus === 'connected' && styles.iconBtnActive,
                      ]}
                      onPress={() => handleConnectToggle(item)}
                    >
                      <Power
                        color={
                          isActive && connectionStatus === 'connected'
                            ? palette.onPrimary
                            : palette.onSurfaceVariant
                        }
                        size={18}
                      />
                    </TouchableOpacity>
                    <TouchableOpacity
                      style={styles.iconBtn}
                      onPress={() => handleDeleteDevice(item)}
                    >
                      <Trash2 color={palette.onSurfaceVariant} size={18} />
                    </TouchableOpacity>
                  </View>
                </View>
              );
            })}
          </View>
        )}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: palette.background,
  },
  scroll: {
    padding: Spacing.md,
    paddingBottom: Spacing.xxxl,
  },

  // --- Status card -------------------------------------------------------
  statusCard: {
    backgroundColor: palette.surfaceContainer,
    borderRadius: Radius.lg,
    padding: Spacing.lg,
    marginBottom: Spacing.lg,
    ...Elevation.level1,
  },
  statusHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: Spacing.md,
  },
  statusDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    marginRight: Spacing.xs,
  },
  statusLabel: {
    ...Typography.labelLarge,
    color: palette.onSurfaceVariant,
    textTransform: 'uppercase',
    letterSpacing: 1,
  },
  deviceName: {
    ...Typography.headlineSmall,
    color: palette.onSurface,
    marginBottom: 4,
  },
  deviceSub: {
    ...Typography.bodyMedium,
    color: palette.onSurfaceVariant,
    marginBottom: Spacing.md,
  },
  emptyActive: {
    ...Typography.bodyMedium,
    color: palette.onSurfaceVariant,
  },

  // --- Action row --------------------------------------------------------
  actionRow: {
    flexDirection: 'row',
    gap: Spacing.sm,
    marginBottom: Spacing.lg,
  },

  // --- Manual form -------------------------------------------------------
  formCard: {
    backgroundColor: palette.surfaceContainer,
    borderRadius: Radius.lg,
    padding: Spacing.lg,
    marginBottom: Spacing.lg,
    ...Elevation.level1,
  },
  fieldGroup: { marginBottom: Spacing.md },
  fieldRow: { flexDirection: 'row' },
  fieldLabel: {
    ...Typography.labelMedium,
    color: palette.onSurfaceVariant,
    marginBottom: 6,
  },
  input: {
    backgroundColor: palette.surfaceContainerHigh,
    borderRadius: Radius.sm,
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.sm + 2,
    color: palette.onSurface,
    ...Typography.bodyLarge,
  },

  // --- Section header ----------------------------------------------------
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: Spacing.sm,
    marginTop: Spacing.xs,
  },
  sectionTitle: {
    ...Typography.titleMedium,
    color: palette.onSurface,
  },
  countChip: {
    backgroundColor: palette.secondaryContainer,
    paddingHorizontal: Spacing.sm,
    paddingVertical: 4,
    borderRadius: Radius.full,
  },
  countChipText: {
    ...Typography.labelMedium,
    color: palette.onSecondaryContainer,
  },

  // --- Empty state -------------------------------------------------------
  emptyState: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: Spacing.xxxl,
    paddingHorizontal: Spacing.lg,
    backgroundColor: palette.surfaceContainer,
    borderRadius: Radius.lg,
    borderWidth: 1,
    borderColor: palette.outlineVariant,
    borderStyle: 'dashed',
  },
  emptyTitle: {
    ...Typography.titleMedium,
    color: palette.onSurface,
    marginTop: Spacing.sm,
    marginBottom: 4,
  },
  emptySubtitle: {
    ...Typography.bodySmall,
    color: palette.onSurfaceVariant,
    textAlign: 'center',
    lineHeight: 18,
  },

  // --- Device list -------------------------------------------------------
  deviceList: { gap: Spacing.xs },
  deviceCard: {
    backgroundColor: palette.surfaceContainer,
    borderRadius: Radius.lg,
    padding: Spacing.md,
    flexDirection: 'row',
    alignItems: 'center',
    ...Elevation.level1,
  },
  deviceCardActive: {
    backgroundColor: palette.primaryContainer,
  },
  deviceIcon: {
    width: 40,
    height: 40,
    borderRadius: Radius.full,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: palette.surfaceContainerHighest,
    marginRight: Spacing.sm,
  },
  deviceInfo: { flex: 1 },
  deviceCardName: {
    ...Typography.titleSmall,
    color: palette.onSurface,
  },
  deviceCardSub: {
    ...Typography.bodySmall,
    color: palette.onSurfaceVariant,
    marginTop: 2,
  },
  deviceActions: { flexDirection: 'row', gap: Spacing.xxs },
  iconBtn: {
    width: 40,
    height: 40,
    borderRadius: Radius.full,
    backgroundColor: palette.surfaceContainerHigh,
    alignItems: 'center',
    justifyContent: 'center',
  },
  iconBtnActive: {
    backgroundColor: palette.primary,
  },

  // --- Buttons (M3: filled, tonal, error-filled) -------------------------
  filledBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: palette.primary,
    paddingVertical: 12,
    paddingHorizontal: Spacing.lg,
    borderRadius: Radius.full,
    alignSelf: 'flex-start',
  },
  filledBtnText: {
    ...Typography.labelLarge,
    color: palette.onPrimary,
  },
  filledBtnError: {
    backgroundColor: palette.error,
  },
  tonalBtn: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: palette.secondaryContainer,
    paddingVertical: 12,
    paddingHorizontal: Spacing.md,
    borderRadius: Radius.full,
  },
  tonalBtnText: {
    ...Typography.labelLarge,
    color: palette.onSecondaryContainer,
  },

  // --- Hero Brand Logo Badge Header -------------------------
  brandHeroCard: {
    backgroundColor: palette.surfaceContainerHigh,
    borderRadius: Radius.lg,
    padding: Spacing.md,
    marginBottom: Spacing.md,
    ...Elevation.level1,
  },
  brandHeroLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.sm,
  },
  heroLogoBadge: {
    width: 44,
    height: 44,
    borderRadius: 12,
    overflow: 'hidden',
    borderWidth: 1.5,
    borderColor: 'rgba(255, 255, 255, 0.25)',
    ...Elevation.level2,
  },
  heroLogoImage: {
    width: '100%',
    height: '100%',
  },
  brandHeroTitle: {
    ...Typography.titleMedium,
    color: palette.onSurface,
    fontWeight: '700',
  },
  brandHeroSubtitle: {
    ...Typography.bodySmall,
    color: palette.onSurfaceVariant,
  },
});
