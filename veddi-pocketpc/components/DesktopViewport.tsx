import React, { useEffect, useState, useRef, useCallback } from 'react';
import {
  StyleSheet,
  View,
  Text,
  Image,
  TouchableOpacity,
  ActivityIndicator,
  Dimensions,
  GestureResponderEvent,
  Modal,
  TextInput,
  PanResponder,
} from 'react-native';
import {
  Play,
  Square,
  RefreshCw,
  Maximize2,
  Minimize2,
  Tv,
  Settings,
  X,
  Wifi,
  MousePointer,
  Eye,
} from 'lucide-react-native';
import { useDeviceStore } from '../src/store/deviceStore';
import wsClient from '../src/ws/client';
import { palette, Spacing, Radius, Typography, Elevation } from '../constants/theme-m3';

function arrayBufferToBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let binary = '';
  const chunkSize = 0x8000;
  for (let i = 0; i < bytes.length; i += chunkSize) {
    const chunk = bytes.subarray(i, i + chunkSize);
    binary += String.fromCharCode.apply(null, chunk as unknown as number[]);
  }
  if (typeof btoa !== 'undefined') {
    return btoa(binary);
  }
  if (typeof globalThis !== 'undefined' && (globalThis as any).btoa) {
    return (globalThis as any).btoa(binary);
  }
  return '';
}

interface DesktopViewportProps {
  streamPort?: number;
  interactive?: boolean;
}

export default function DesktopViewport({
  streamPort = 8080,
  interactive = true,
}: DesktopViewportProps) {
  const activeDevice = useDeviceStore(state => state.activeDevice);

  const [isStreaming, setIsStreaming] = useState(false);
  const [frameUri, setFrameUri] = useState<string | null>(null);
  const [fps, setFps] = useState(0);
  const [kbps, setKbps] = useState(0);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [touchMode, setTouchMode] = useState<'click' | 'view'>('click');

  // Custom stream server configuration modal & realtime resolution/FPS settings
  const [showConfigModal, setShowConfigModal] = useState(false);
  const [customIp, setCustomIp] = useState('');
  const [customPort, setCustomPort] = useState(String(streamPort));

  const [selectedRes, setSelectedRes] = useState({ label: '360p', w: 640, h: 360 });
  const [selectedFps, setSelectedFps] = useState<number>(30);

  const sendStreamSettings = (w: number, h: number, fps: number) => {
    const payloadObj = {
      type: 'set_stream_settings',
      max_width: w,
      max_height: h,
      fps: fps,
    };

    // Send over control client
    wsClient.send(payloadObj);

    // Also send directly over active stream socket if connected
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      try {
        wsRef.current.send(JSON.stringify(payloadObj));
      } catch (e) {
        console.warn('Error sending settings on stream socket:', e);
      }
    }
  };

  const wsRef = useRef<WebSocket | null>(null);
  const frameCountRef = useRef(0);
  const bytesCountRef = useRef(0);
  const statsTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const lastPanDx = useRef(0);
  const lastPanDy = useRef(0);

  // PanResponder to handle dragging finger on Desktop Viewport to move PC cursor
  const panResponder = useRef(
    PanResponder.create({
      onStartShouldSetPanResponder: () => interactive && touchMode === 'click',
      onMoveShouldSetPanResponder: () => interactive && touchMode === 'click',
      onPanResponderGrant: () => {
        lastPanDx.current = 0;
        lastPanDy.current = 0;
      },
      onPanResponderMove: (evt, gestureState) => {
        const dx = gestureState.dx - lastPanDx.current;
        const dy = gestureState.dy - lastPanDy.current;
        lastPanDx.current = gestureState.dx;
        lastPanDy.current = gestureState.dy;

        if (Math.abs(dx) > 0.1 || Math.abs(dy) > 0.1) {
          wsClient.send({
            type: 'mouse_move',
            dx,
            dy,
          });
        }
      },
      onPanResponderRelease: (evt, gestureState) => {
        if (Math.abs(gestureState.dx) < 3 && Math.abs(gestureState.dy) < 3) {
          wsClient.send({
            type: 'mouse_click',
            button: 'left',
          });
        }
        lastPanDx.current = 0;
        lastPanDy.current = 0;
      },
    })
  ).current;

  // Determine effective target IP and Port
  const targetIp = customIp || activeDevice?.ip || '127.0.0.1';
  const targetPort = customPort || String(streamPort);

  // Start FPS & KB/s calculation timer
  useEffect(() => {
    statsTimerRef.current = setInterval(() => {
      setFps(frameCountRef.current);
      setKbps(Math.round((bytesCountRef.current * 8) / 1024));
      frameCountRef.current = 0;
      bytesCountRef.current = 0;
    }, 1000);

    return () => {
      if (statsTimerRef.current) clearInterval(statsTimerRef.current);
    };
  }, []);

  const [frontUri, setFrontUri] = useState<string | null>(null);
  const [backUri, setBackUri] = useState<string | null>(null);
  const activeBufferRef = useRef<'front' | 'back'>('front');
  const [activeBuffer, setActiveBuffer] = useState<'front' | 'back'>('front');

  const stopStream = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setIsStreaming(false);
    setFrontUri(null);
    setBackUri(null);
  }, []);

  const startStream = useCallback(() => {
    stopStream();

    const wsUrl = `ws://${targetIp}:${targetPort}/ws`;
    console.log(`[ScreenViewport] Connecting to ${wsUrl}`);
    setIsStreaming(true);

    try {
      const ws = new WebSocket(wsUrl);
      ws.binaryType = 'arraybuffer';
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('[ScreenViewport] Connected to screen stream');
        try {
          ws.send(
            JSON.stringify({
              type: 'set_stream_settings',
              max_width: selectedRes.w,
              max_height: selectedRes.h,
              fps: selectedFps,
            })
          );
        } catch (e) {
          console.warn('Failed sending initial settings on connect:', e);
        }
      };

      ws.onmessage = event => {
        if (event.data instanceof ArrayBuffer) {
          const byteLength = event.data.byteLength;
          bytesCountRef.current += byteLength;
          frameCountRef.current += 1;

          const base64 = arrayBufferToBase64(event.data);
          const nextUri = `data:image/jpeg;base64,${base64}`;

          if (activeBufferRef.current === 'front') {
            setBackUri(nextUri);
          } else {
            setFrontUri(nextUri);
          }
        }
      };

      ws.onerror = err => {
        console.warn('[ScreenViewport] Stream socket connection pending or offline.');
      };

      ws.onclose = () => {
        console.log('[ScreenViewport] Stream disconnected');
        setIsStreaming(false);
        wsRef.current = null;
      };
    } catch (e) {
      console.error('[ScreenViewport] Failed to open stream socket:', e);
      setIsStreaming(false);
    }
  }, [targetIp, targetPort, stopStream]);

  // Auto-start screen stream on component mount & clean up on unmount
  useEffect(() => {
    startStream();
    return () => {
      stopStream();
    };
  }, [startStream, stopStream]);

  const hasFrame = Boolean(frontUri || backUri);

  return (
    <View style={[styles.container, isFullscreen && styles.fullscreenContainer]}>
      {/* Header bar / Toolbar */}
      {!isFullscreen && (
        <View style={styles.toolbar}>
          <View style={styles.statusInfo}>
            <View
              style={[
                styles.statusBadge,
                { backgroundColor: isStreaming ? '#2E7D32' : palette.outline },
              ]}
            />
            <Text style={styles.statusTitle}>
              {isStreaming ? `${fps} FPS | ${kbps} kbps` : 'Screen Offline'}
            </Text>
          </View>

          <View style={styles.toolActions}>
            <TouchableOpacity
              style={styles.toolBtn}
              onPress={() => setTouchMode(touchMode === 'click' ? 'view' : 'click')}
            >
              {touchMode === 'click' ? (
                <MousePointer color={palette.primary} size={18} />
              ) : (
                <Eye color={palette.onSurfaceVariant} size={18} />
              )}
            </TouchableOpacity>

            <TouchableOpacity
              style={styles.toolBtn}
              onPress={() => setShowConfigModal(true)}
            >
              <Settings color={palette.onSurfaceVariant} size={18} />
            </TouchableOpacity>

            <TouchableOpacity
              style={[
                styles.toggleBtn,
                isStreaming ? styles.stopBtn : styles.startBtn,
              ]}
              onPress={isStreaming ? stopStream : startStream}
            >
              {isStreaming ? (
                <Square color={palette.onPrimary} size={16} />
              ) : (
                <Play color={palette.onPrimary} size={16} />
              )}
              <Text style={styles.toggleBtnText}>
                {isStreaming ? 'Stop' : 'Start'}
              </Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={styles.toolBtn}
              onPress={() => setIsFullscreen(!isFullscreen)}
            >
              <Maximize2 color={palette.onSurfaceVariant} size={18} />
            </TouchableOpacity>
          </View>
        </View>
      )}

      {/* Screen Viewport Canvas */}
      <View
        {...panResponder.panHandlers}
        style={[styles.viewportFrame, isFullscreen && styles.fullscreenFrame]}
      >
        {hasFrame ? (
          <View style={StyleSheet.absoluteFill}>
            {frontUri && (
              <Image
                source={{ uri: frontUri }}
                style={[
                  styles.screenImage,
                  StyleSheet.absoluteFill,
                  { opacity: activeBuffer === 'front' ? 1 : 0 },
                ]}
                resizeMode="contain"
                fadeDuration={0}
                onLoad={() => {
                  if (activeBufferRef.current === 'back') {
                    activeBufferRef.current = 'front';
                    setActiveBuffer('front');
                  }
                }}
              />
            )}
            {backUri && (
              <Image
                source={{ uri: backUri }}
                style={[
                  styles.screenImage,
                  StyleSheet.absoluteFill,
                  { opacity: activeBuffer === 'back' ? 1 : 0 },
                ]}
                resizeMode="contain"
                fadeDuration={0}
                onLoad={() => {
                  if (activeBufferRef.current === 'front') {
                    activeBufferRef.current = 'back';
                    setActiveBuffer('back');
                  }
                }}
              />
            )}
          </View>
        ) : (
          <View style={styles.placeholderContainer}>
            {isStreaming ? (
              <>
                <ActivityIndicator size="large" color={palette.primary} />
                <Text style={styles.placeholderText}>Waiting for frames...</Text>
              </>
            ) : (
              <>
                <Tv color={palette.outline} size={48} />
                <Text style={styles.placeholderTitle}>PC Screen Stream</Text>
                <Text style={styles.placeholderSub}>
                  Target: {targetIp}:{targetPort}
                </Text>
                <TouchableOpacity style={styles.connectBigBtn} onPress={startStream}>
                  <Play color={palette.onPrimary} size={18} style={{ marginRight: 8 }} />
                  <Text style={styles.connectBigBtnText}>Start Desktop Viewport</Text>
                </TouchableOpacity>
              </>
            )}
          </View>
        )}

        {/* Fullscreen Floating Controls */}
        {isFullscreen && (
          <View style={styles.floatingControls}>
            <TouchableOpacity
              style={styles.floatingBtn}
              onPress={() => setIsFullscreen(false)}
            >
              <Minimize2 color="#FFFFFF" size={20} />
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.floatingBtn, { backgroundColor: isStreaming ? '#D32F2F' : '#388E3C' }]}
              onPress={isStreaming ? stopStream : startStream}
            >
              {isStreaming ? (
                <Square color="#FFFFFF" size={20} />
              ) : (
                <Play color="#FFFFFF" size={20} />
              )}
            </TouchableOpacity>
          </View>
        )}
      </View>

      {/* Settings Modal */}
      <Modal
        visible={showConfigModal}
        transparent
        animationType="fade"
        onRequestClose={() => setShowConfigModal(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Stream Configuration</Text>
              <TouchableOpacity onPress={() => setShowConfigModal(false)}>
                <X color={palette.onSurfaceVariant} size={20} />
              </TouchableOpacity>
            </View>

            <View style={styles.modalBody}>
              <Text style={styles.fieldLabel}>Stream Server IP</Text>
              <TextInput
                style={styles.modalInput}
                placeholder={activeDevice?.ip || '192.168.1.10'}
                placeholderTextColor={palette.outline}
                value={customIp}
                onChangeText={setCustomIp}
              />

              <Text style={[styles.fieldLabel, { marginTop: Spacing.md }]}>
                Screen Resolution
              </Text>
              <View style={styles.segmented}>
                {[
                  { label: '1080p', w: 1920, h: 1080 },
                  { label: '720p', w: 1280, h: 720 },
                  { label: '480p', w: 854, h: 480 },
                  { label: '360p', w: 640, h: 360 },
                ].map(res => {
                  const active = selectedRes.w === res.w;
                  return (
                    <TouchableOpacity
                      key={res.label}
                      style={[styles.segment, active && styles.segmentActive]}
                      onPress={() => {
                        setSelectedRes(res);
                        sendStreamSettings(res.w, res.h, selectedFps);
                      }}
                    >
                      <Text style={[styles.segmentText, active && styles.segmentTextActive]}>
                        {res.label}
                      </Text>
                    </TouchableOpacity>
                  );
                })}
              </View>

              <Text style={[styles.fieldLabel, { marginTop: Spacing.md }]}>
                Stream Frame Rate (FPS)
              </Text>
              <View style={styles.segmented}>
                {[15, 30, 60].map(f => {
                  const active = selectedFps === f;
                  return (
                    <TouchableOpacity
                      key={f}
                      style={[styles.segment, active && styles.segmentActive]}
                      onPress={() => {
                        setSelectedFps(f);
                        sendStreamSettings(selectedRes.w, selectedRes.h, f);
                      }}
                    >
                      <Text style={[styles.segmentText, active && styles.segmentTextActive]}>
                        {f} FPS
                      </Text>
                    </TouchableOpacity>
                  );
                })}
              </View>

              <TouchableOpacity
                style={styles.modalSaveBtn}
                onPress={() => {
                  setShowConfigModal(false);
                  startStream();
                }}
              >
                <RefreshCw color={palette.onPrimary} size={18} style={{ marginRight: 8 }} />
                <Text style={styles.modalSaveBtnText}>Apply &amp; Reconnect</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: palette.surfaceContainer,
    borderRadius: Radius.lg,
    overflow: 'hidden',
    marginBottom: Spacing.md,
    ...Elevation.level1,
  },
  fullscreenContainer: {
    position: 'absolute',
    top: 0,
    bottom: 0,
    left: 0,
    right: 0,
    zIndex: 999,
    borderRadius: 0,
    backgroundColor: '#000000',
    marginBottom: 0,
  },

  // --- Toolbar -----------------------------------------------------------
  toolbar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.sm + 2,
    backgroundColor: palette.surfaceContainerHigh,
    borderBottomWidth: 1,
    borderBottomColor: palette.outlineVariant,
  },
  statusInfo: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  statusBadge: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginRight: Spacing.xs,
  },
  statusTitle: {
    ...Typography.labelMedium,
    color: palette.onSurface,
  },
  toolActions: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.xs,
  },
  toolBtn: {
    width: 32,
    height: 32,
    borderRadius: Radius.full,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: palette.surfaceContainerHighest,
  },
  toggleBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: Spacing.md,
    paddingVertical: 6,
    borderRadius: Radius.full,
  },
  startBtn: {
    backgroundColor: palette.primary,
  },
  stopBtn: {
    backgroundColor: palette.error,
  },
  toggleBtnText: {
    ...Typography.labelMedium,
    color: palette.onPrimary,
    marginLeft: 6,
  },

  // --- Viewport frame ----------------------------------------------------
  viewportFrame: {
    width: '100%',
    aspectRatio: 16 / 9,
    backgroundColor: '#000000',
    alignItems: 'center',
    justifyContent: 'center',
  },
  fullscreenFrame: {
    flex: 1,
    aspectRatio: undefined,
  },
  screenImage: {
    width: '100%',
    height: '100%',
  },

  // --- Placeholder state -------------------------------------------------
  placeholderContainer: {
    alignItems: 'center',
    justifyContent: 'center',
    padding: Spacing.lg,
  },
  placeholderTitle: {
    ...Typography.titleMedium,
    color: palette.onSurface,
    marginTop: Spacing.sm,
  },
  placeholderSub: {
    ...Typography.bodySmall,
    color: palette.onSurfaceVariant,
    marginTop: 4,
    marginBottom: Spacing.md,
  },
  placeholderText: {
    ...Typography.bodyMedium,
    color: palette.onSurfaceVariant,
    marginTop: Spacing.sm,
  },
  connectBigBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: palette.primary,
    paddingHorizontal: Spacing.lg,
    paddingVertical: 10,
    borderRadius: Radius.full,
  },
  connectBigBtnText: {
    ...Typography.labelLarge,
    color: palette.onPrimary,
  },

  // --- Fullscreen floating controls -------------------------------------
  floatingControls: {
    position: 'absolute',
    top: 40,
    right: 20,
    flexDirection: 'row',
    gap: 12,
  },
  floatingBtn: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: 'rgba(0,0,0,0.6)',
    alignItems: 'center',
    justifyContent: 'center',
  },

  // --- Modal styles ------------------------------------------------------
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    alignItems: 'center',
    justifyContent: 'center',
    padding: Spacing.md,
  },
  modalContent: {
    width: '100%',
    maxWidth: 360,
    backgroundColor: palette.surfaceContainer,
    borderRadius: Radius.xl,
    padding: Spacing.lg,
    ...Elevation.level3,
  },
  modalHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: Spacing.md,
  },
  modalTitle: {
    ...Typography.titleMedium,
    color: palette.onSurface,
  },
  modalBody: {
    gap: Spacing.xs,
  },
  fieldLabel: {
    ...Typography.labelMedium,
    color: palette.onSurfaceVariant,
  },
  modalInput: {
    backgroundColor: palette.surfaceContainerHigh,
    borderRadius: Radius.sm,
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.sm,
    color: palette.onSurface,
    ...Typography.bodyMedium,
    marginTop: 4,
  },
  modalSaveBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: palette.primary,
    paddingVertical: 12,
    borderRadius: Radius.full,
    marginTop: Spacing.lg,
  },
  modalSaveBtnText: {
    ...Typography.labelLarge,
    color: palette.onPrimary,
  },
  segmented: {
    flexDirection: 'row',
    backgroundColor: palette.surfaceContainerHighest,
    borderRadius: Radius.full,
    padding: 4,
    gap: 4,
    marginTop: 4,
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
});
