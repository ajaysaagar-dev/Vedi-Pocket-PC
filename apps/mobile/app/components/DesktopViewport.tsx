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
  const len = bytes.length;
  let binary = '';
  const chunkSize = 8192;
  try {
    for (let i = 0; i < len; i += chunkSize) {
      const sub = bytes.subarray(i, Math.min(i + chunkSize, len));
      binary += String.fromCharCode.apply(null, sub as unknown as number[]);
    }
    if (typeof btoa === 'function') {
      return btoa(binary);
    }
  } catch {
    // Fallback on stack size exception
  }
  return base64Fallback(bytes);
}

function base64Fallback(bytes: Uint8Array): string {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
  let base64 = '';
  const len = bytes.length;

  for (let i = 0; i < len; i += 3) {
    const b1 = bytes[i];
    const b2 = i + 1 < len ? bytes[i + 1] : 0;
    const b3 = i + 2 < len ? bytes[i + 2] : 0;

    const c1 = b1 >> 2;
    const c2 = ((b1 & 3) << 4) | (b2 >> 4);
    const c3 = ((b2 & 15) << 2) | (b3 >> 6);
    const c4 = b3 & 63;

    base64 += chars[c1] + chars[c2];
    base64 += i + 1 < len ? chars[c3] : '=';
    base64 += i + 2 < len ? chars[c4] : '=';
  }

  return base64;
}

const ScreenImage = React.memo(function ScreenImage({ uri }: { uri: string }) {
  return (
    <Image
      source={{ uri }}
      style={[styles.screenImage, StyleSheet.absoluteFill]}
      resizeMode="contain"
      fadeDuration={0}
    />
  );
});

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
  // Default FPS is 20 (not 30) — at 30 FPS, a 640x360 JPEG stream lands in the
  // 700-1200 kbps range on a typical desktop, which stutters badly on cellular.
  // 20 FPS keeps responsiveness for cursor tracking while halving the bitrate.
  const [selectedFps, setSelectedFps] = useState<number>(20);
  // JPEG quality (10-95) maps to Low / Medium / High presets below.
  // The server clamps to 10-100 and applies it to the *next* captured frame,
  // so this is what actually controls bitrate per-frame.
  const [selectedQuality, setSelectedQuality] = useState<number>(45);

  const sendStreamSettings = (w: number, h: number, fps: number, quality: number) => {
    const payloadObj = {
      type: 'set_stream_settings',
      max_width: w,
      max_height: h,
      fps: fps,
      jpeg_quality: quality,
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
  const isMountedRef = useRef(true);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const frameCountRef = useRef(0);
  const bytesCountRef = useRef(0);
  const statsTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const lastPanDx = useRef(0);
  const lastPanDy = useRef(0);
  const panAccumulator = useRef({ dx: 0, dy: 0 });
  const panRafId = useRef<number | null>(null);

  const flushPanMove = () => {
    const { dx, dy } = panAccumulator.current;
    if (Math.abs(dx) > 0.05 || Math.abs(dy) > 0.05) {
      wsClient.send({
        type: 'mouse_move',
        dx,
        dy,
      });
      panAccumulator.current = { dx: 0, dy: 0 };
    }
    panRafId.current = null;
  };

  // PanResponder to handle dragging finger on Desktop Viewport to move PC cursor
  const panResponder = useRef(
    PanResponder.create({
      onStartShouldSetPanResponder: () => interactive && touchMode === 'click',
      onMoveShouldSetPanResponder: () => interactive && touchMode === 'click',
      onPanResponderGrant: () => {
        lastPanDx.current = 0;
        lastPanDy.current = 0;
        panAccumulator.current = { dx: 0, dy: 0 };
      },
      onPanResponderMove: (evt, gestureState) => {
        const dx = gestureState.dx - lastPanDx.current;
        const dy = gestureState.dy - lastPanDy.current;
        lastPanDx.current = gestureState.dx;
        lastPanDy.current = gestureState.dy;

        panAccumulator.current.dx += dx;
        panAccumulator.current.dy += dy;

        if (!panRafId.current) {
          panRafId.current = requestAnimationFrame(flushPanMove);
        }
      },
      onPanResponderRelease: (evt, gestureState) => {
        if (panRafId.current) {
          cancelAnimationFrame(panRafId.current);
          panRafId.current = null;
        }
        flushPanMove();
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

  const stopStream = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setIsStreaming(false);
    setFrontUri(null);
  }, []);

  const startStream = useCallback(() => {
    stopStream();

    // The stream-server's WebSocket endpoint requires a valid token
    // (either `?token=…` in the URL or an `auth` message after open).
    // The mobile app only pairs with the BACKEND (port 8000) for the
    // QR-scan handshake, so we never have a stream-side token yet.
    // Mint one by POSTing to the stream server's /pair endpoint
    // (which accepts any PIN and issues a fresh session token from
    // its own MemoryTokenStore), then connect with that token.
    const fetchToken = async (): Promise<{ token: string; port: string }> => {
      const candidatePorts = Array.from(new Set([targetPort, '8081', '8088', '8082', '8080']));
      for (const p of candidatePorts) {
        try {
          const controller = new AbortController();
          const timeoutId = setTimeout(() => controller.abort(), 1500);
          const res = await fetch(`http://${targetIp}:${p}/pair`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ pin: '' }),
            signal: controller.signal,
          });
          clearTimeout(timeoutId);
          if (res.ok) {
            const data = (await res.json()) as { token?: string };
            if (data && typeof data.token === 'string' && data.token) {
              return { token: data.token, port: p };
            }
          }
        } catch {
          // Probe next candidate port
        }
      }
      return { token: activeDevice?.token || 'direct_stream_token', port: targetPort };
    };

    const openSocket = ({ token, port }: { token: string; port: string }) => {
      const wsUrl = token
        ? `ws://${targetIp}:${port}/ws?token=${encodeURIComponent(token)}`
        : `ws://${targetIp}:${port}/ws`;
      console.log(`[ScreenViewport] Connecting to ${wsUrl}`);
      setIsStreaming(true);

      try {
        const ws = new WebSocket(wsUrl);
        ws.binaryType = 'arraybuffer';
        wsRef.current = ws;

        ws.onopen = () => {
          console.log('[ScreenViewport] Connected to screen stream');
          try {
            if (ws.readyState === WebSocket.OPEN) {
              ws.send(
                JSON.stringify({
                  type: 'set_stream_settings',
                  max_width: selectedRes.w,
                  max_height: selectedRes.h,
                  fps: selectedFps,
                  jpeg_quality: selectedQuality,
                })
              );
            }
          } catch (e) {
            console.warn('Failed sending initial settings on connect:', e);
          }
        };

        ws.onmessage = event => {
          try {
            if (!event || !event.data) return;
            if (typeof event.data === 'string') return; // Ignore text frames

            let buffer: ArrayBuffer | null = null;
            if (event.data instanceof ArrayBuffer) {
              buffer = event.data;
            } else if (event.data.buffer && event.data.buffer instanceof ArrayBuffer) {
              buffer = event.data.buffer;
            }

            if (buffer && buffer.byteLength > 0) {
              const byteLength = buffer.byteLength;
              bytesCountRef.current += byteLength;
              frameCountRef.current += 1;

              const base64 = arrayBufferToBase64(buffer);
              const nextUri = `data:image/jpeg;base64,${base64}`;

              // Single buffer — RN's <Image> keeps the old frame visible
              // until the new source is decoded, so we get the same effect
              // without paying for two simultaneous JPEG decodes.
              setFrontUri(nextUri);
            }
          } catch (err) {
            console.warn('[ScreenViewport] Frame processing error:', err);
          }
        };

        ws.onerror = err => {
          // Log as info to prevent React Native LogBox popup while socket status settles
          console.log('[ScreenViewport] Stream socket status event:', err);
        };

        ws.onclose = () => {
          console.log('[ScreenViewport] Stream disconnected');
          setIsStreaming(false);
          wsRef.current = null;

          if (reconnectTimerRef.current) {
            clearTimeout(reconnectTimerRef.current);
          }
          if (isMountedRef.current) {
            reconnectTimerRef.current = setTimeout(() => {
              if (isMountedRef.current && !wsRef.current) {
                console.log('[ScreenViewport] Auto-reconnecting to stream...');
                startStream();
              }
            }, 3000);
          }
        };
      } catch (e) {
        console.error('[ScreenViewport] Failed to open stream socket:', e);
        setIsStreaming(false);
      }
    };

    // Async mint + open. The token request happens before the socket
    // so the WS handshake carries it in the URL.
    fetchToken().then(openSocket).catch(err => {
      console.error('[ScreenViewport] Failed to mint stream token:', err);
      setIsStreaming(false);
    });
  }, [targetIp, targetPort, stopStream]);

  const stopStreamRef = useRef(stopStream);
  stopStreamRef.current = stopStream;

  const startStreamRef = useRef(startStream);
  startStreamRef.current = startStream;

  // Auto-start screen stream on component mount & clean up on unmount
  useEffect(() => {
    isMountedRef.current = true;
    startStreamRef.current();

    return () => {
      isMountedRef.current = false;
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
      stopStreamRef.current();
    };
  }, [targetIp, targetPort]);

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
        {frontUri ? (
          // Single Image — React Native's Image keeps the old frame visible
          // until the new source is decoded, so we don't need explicit
          // double-buffering. Rendering both buffers (the previous design)
          // doubled JPEG decode work every frame and caused the visible
          // stutter at higher bitrates.
          <ScreenImage uri={frontUri} />
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
                  { label: '720p', w: 1280, h: 720 },
                  { label: '480p', w: 854, h: 480 },
                  { label: '360p', w: 640, h: 360 },
                  { label: '240p', w: 426, h: 240 },
                ].map(res => {
                  const active = selectedRes.w === res.w;
                  return (
                    <TouchableOpacity
                      key={res.label}
                      style={[styles.segment, active && styles.segmentActive]}
                      onPress={() => {
                        setSelectedRes(res);
                        sendStreamSettings(res.w, res.h, selectedFps, selectedQuality);
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
                {[15, 20, 30].map(f => {
                  const active = selectedFps === f;
                  return (
                    <TouchableOpacity
                      key={f}
                      style={[styles.segment, active && styles.segmentActive]}
                      onPress={() => {
                        setSelectedFps(f);
                        sendStreamSettings(selectedRes.w, selectedRes.h, f, selectedQuality);
                      }}
                    >
                      <Text style={[styles.segmentText, active && styles.segmentTextActive]}>
                        {f} FPS
                      </Text>
                    </TouchableOpacity>
                  );
                })}
              </View>

              <Text style={[styles.fieldLabel, { marginTop: Spacing.md }]}>
                JPEG Quality — biggest impact on bitrate
              </Text>
              <View style={styles.segmented}>
                {[
                  { label: 'Low (35)', q: 35 },
                  { label: 'Medium (55)', q: 55 },
                  { label: 'High (80)', q: 80 },
                ].map(opt => {
                  const active = selectedQuality === opt.q;
                  return (
                    <TouchableOpacity
                      key={opt.label}
                      style={[styles.segment, active && styles.segmentActive]}
                      onPress={() => {
                        setSelectedQuality(opt.q);
                        sendStreamSettings(selectedRes.w, selectedRes.h, selectedFps, opt.q);
                      }}
                    >
                      <Text style={[styles.segmentText, active && styles.segmentTextActive]}>
                        {opt.label}
                      </Text>
                    </TouchableOpacity>
                  );
                })}
              </View>
              {kbps > 1500 && (
                <Text style={styles.qualityWarn}>
                  Stream is {kbps} kbps — try Low quality or 360p to reduce stutter.
                </Text>
              )}

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

  qualityWarn: {
    ...Typography.bodySmall,
    color: palette.error,
    marginTop: Spacing.xs,
    textAlign: 'center',
  },
});
