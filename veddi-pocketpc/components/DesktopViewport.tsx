import React, { useEffect, useState, useRef, useCallback, useMemo } from 'react';
import {
  StyleSheet,
  View,
  Text,
  TouchableOpacity,
  ActivityIndicator,
  Modal,
  TextInput,
  PanResponder,
  AppState,
} from 'react-native';
import { Image as ExpoImage } from 'expo-image';
import {
  Play,
  Square,
  RefreshCw,
  Maximize2,
  Minimize2,
  Tv,
  Settings,
  X,
  MousePointer,
  Eye,
} from 'lucide-react-native';
import { useDeviceStore } from '../src/store/deviceStore';
import { wsClient } from '../src/ws/client';
import { palette, Spacing, Radius, Typography, Elevation } from '../constants/theme-m3';

// ---------------------------------------------------------------------------
// Binary WebSocket Helpers
// ---------------------------------------------------------------------------

function getUint8ArrayFromEventData(data: any): Uint8Array | null {
  if (!data) return null;
  if (data instanceof Uint8Array) return data;
  if (data instanceof ArrayBuffer) return new Uint8Array(data);
  if (ArrayBuffer.isView(data)) {
    return new Uint8Array(data.buffer, data.byteOffset, data.byteLength);
  }
  if (data.buffer && data.buffer instanceof ArrayBuffer) {
    const offset = typeof data.byteOffset === 'number' ? data.byteOffset : 0;
    const length =
      typeof data.byteLength === 'number'
        ? data.byteLength
        : data.buffer.byteLength - offset;
    return new Uint8Array(data.buffer, offset, length);
  }
  return null;
}

/**
 * Unwrap a `STRM + uint32-BE-length + bytes` envelope if present.
 */
function tryUnwrapEnvelope(bytes: Uint8Array): { bytes: Uint8Array } | null {
  if (bytes.length < 8) return null;
  if (
    bytes[0] !== 0x53 || // 'S'
    bytes[1] !== 0x54 || // 'T'
    bytes[2] !== 0x52 || // 'R'
    bytes[3] !== 0x4d    // 'M'
  ) {
    return null;
  }
  const declared =
    ((bytes[4] & 0xff) << 24) |
    ((bytes[5] & 0xff) << 16) |
    ((bytes[6] & 0xff) << 8) |
    (bytes[7] & 0xff);

  if (declared <= 0 || declared > bytes.length - 8) return null;
  return { bytes: bytes.subarray(8, 8 + declared) };
}

function isValidJpeg(bytes: Uint8Array | null): boolean {
  if (!bytes || bytes.length < 4) return false;
  // Check JPEG SOI marker: 0xFF, 0xD8
  return bytes[0] === 0xff && bytes[1] === 0xd8;
}

const BASE64_CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';

/**
 * High-speed Uint8Array to base64 converter.
 */
function uint8ArrayToBase64(bytes: Uint8Array): string {
  const len = bytes.length;
  if (len === 0) return '';

  const extraBytes = len % 3;
  const mainLength = len - extraBytes;
  const CHUNK_SIZE = 0x8000;
  const parts: string[] = [];

  let i = 0;
  while (i < mainLength) {
    const chunkEnd = Math.min(i + CHUNK_SIZE, mainLength);
    let chunkStr = '';
    for (; i < chunkEnd; i += 3) {
      const b1 = bytes[i];
      const b2 = bytes[i + 1];
      const b3 = bytes[i + 2];

      chunkStr += BASE64_CHARS[(b1 >> 2) & 63];
      chunkStr += BASE64_CHARS[((b1 & 3) << 4) | ((b2 >> 4) & 15)];
      chunkStr += BASE64_CHARS[((b2 & 15) << 2) | ((b3 >> 6) & 3)];
      chunkStr += BASE64_CHARS[b3 & 63];
    }
    parts.push(chunkStr);
  }

  if (extraBytes === 1) {
    const b1 = bytes[mainLength];
    parts.push(BASE64_CHARS[(b1 >> 2) & 63] + BASE64_CHARS[(b1 & 3) << 4] + '==');
  } else if (extraBytes === 2) {
    const b1 = bytes[mainLength];
    const b2 = bytes[mainLength + 1];
    parts.push(
      BASE64_CHARS[(b1 >> 2) & 63] +
        BASE64_CHARS[((b1 & 3) << 4) | ((b2 >> 4) & 15)] +
        BASE64_CHARS[((b2 & 15) << 2) & 63] +
        '='
    );
  }

  return parts.join('');
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
  const [fps, setFps] = useState(0);
  const [kbps, setKbps] = useState(0);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [touchMode, setTouchMode] = useState<'click' | 'view'>('click');

  // Custom stream server configuration modal & realtime resolution/FPS settings
  const [showConfigModal, setShowConfigModal] = useState(false);
  const [customIp, setCustomIp] = useState('');
  const [customPort, setCustomPort] = useState(String(streamPort));

  const [selectedRes, setSelectedRes] = useState({ label: '360p', w: 640, h: 360 });
  const [selectedFps, setSelectedFps] = useState<number>(20);
  const [selectedQuality, setSelectedQuality] = useState<number>(45);

  const [displayedUri, setDisplayedUri] = useState<string | null>(null);

  const connectedAtRef = useRef<number>(0);
  const lastDecodedAtRef = useRef<number>(0);
  const lastFrameAtRef = useRef<number>(0);

  const pendingUriRef = useRef<string | null>(null);
  const isFrameScheduledRef = useRef(false);

  const wsRef = useRef<WebSocket | null>(null);
  const isMountedRef = useRef(true);
  const isManualStopRef = useRef(false);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const frameCountRef = useRef(0);
  const bytesCountRef = useRef(0);
  const statsTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const watchdogTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const panDeltaRef = useRef({ lastX: 0, lastY: 0 });

  const sendStreamSettings = (w: number, h: number, targetFps: number, quality: number) => {
    const payloadObj = {
      type: 'set_stream_settings',
      max_width: w,
      max_height: h,
      fps: targetFps,
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

  // PanResponder to handle dragging finger on Desktop Viewport to move PC cursor
  const panResponder = useMemo(
    () =>
      PanResponder.create({
        onStartShouldSetPanResponder: () => interactive && touchMode === 'click',
        onMoveShouldSetPanResponder: () => interactive && touchMode === 'click',
        onPanResponderGrant: () => {
          panDeltaRef.current.lastX = 0;
          panDeltaRef.current.lastY = 0;
        },
        onPanResponderMove: (evt, gestureState) => {
          const dx = gestureState.dx - panDeltaRef.current.lastX;
          const dy = gestureState.dy - panDeltaRef.current.lastY;
          panDeltaRef.current.lastX = gestureState.dx;
          panDeltaRef.current.lastY = gestureState.dy;

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
          panDeltaRef.current.lastX = 0;
          panDeltaRef.current.lastY = 0;
        },
      }),
    [interactive, touchMode]
  );

  // Determine effective target IP and Port
  const targetIp = customIp || activeDevice?.ip || '127.0.0.1';
  const targetPort = customPort || String(streamPort);
  const activeToken = activeDevice?.token;

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

  const stopStream = useCallback(() => {
    isManualStopRef.current = true;
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
    if (watchdogTimerRef.current) {
      clearInterval(watchdogTimerRef.current);
      watchdogTimerRef.current = null;
    }
    if (wsRef.current) {
      try {
        wsRef.current.close();
      } catch {
        /* ignore */
      }
      wsRef.current = null;
    }
    pendingUriRef.current = null;
    setFps(0);
    setKbps(0);
    setIsStreaming(false);
  }, []);

  const startStream = useCallback(
    function startStreamFn() {
      isManualStopRef.current = false;

      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
      if (watchdogTimerRef.current) {
        clearInterval(watchdogTimerRef.current);
        watchdogTimerRef.current = null;
      }
      if (wsRef.current) {
        try {
          wsRef.current.close();
        } catch {
          /* ignore */
        }
        wsRef.current = null;
      }

      setIsStreaming(true);

      const fetchToken = async (): Promise<{ token: string; port: string }> => {
        const candidatePorts = Array.from(new Set([targetPort, '8080', '8081', '8088', '8082']));
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
        return { token: activeToken || 'direct_stream_token', port: targetPort };
      };

      const openSocket = ({ token, port }: { token: string; port: string }) => {
        if (isManualStopRef.current || !isMountedRef.current) return;

        const wsUrl = token
          ? `ws://${targetIp}:${port}/ws?token=${encodeURIComponent(token)}`
          : `ws://${targetIp}:${port}/ws`;
        console.log(`[ScreenViewport] Connecting to ${wsUrl}`);

        let ws: WebSocket;
        try {
          ws = new WebSocket(wsUrl);
        } catch (e) {
          console.error('[ScreenViewport] Failed to open stream socket:', e);
          if (!isManualStopRef.current && isMountedRef.current) {
            reconnectTimerRef.current = setTimeout(() => {
              if (isMountedRef.current && !isManualStopRef.current) {
                startStreamFn();
              }
            }, 2000);
          }
          return;
        }
        ws.binaryType = 'arraybuffer';
        wsRef.current = ws;

        ws.onopen = () => {
          console.log('[ScreenViewport] Connected to screen stream');
          connectedAtRef.current = Date.now();
          lastDecodedAtRef.current = Date.now();
          lastFrameAtRef.current = Date.now();

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
            if (typeof event.data === 'string') return;

            const bytes = getUint8ArrayFromEventData(event.data);
            if (!bytes) return;

            let jpegBytes: Uint8Array | null = null;
            const framed = tryUnwrapEnvelope(bytes);
            if (framed) {
              jpegBytes = framed.bytes;
            } else {
              jpegBytes = bytes;
            }

            if (!isValidJpeg(jpegBytes)) return;

            // Account stats
            bytesCountRef.current += jpegBytes.byteLength;
            frameCountRef.current += 1;
            lastFrameAtRef.current = Date.now();

            const base64 = uint8ArrayToBase64(jpegBytes);
            const nextUri = `data:image/jpeg;base64,${base64}`;
            pendingUriRef.current = nextUri;

            if (!isFrameScheduledRef.current) {
              isFrameScheduledRef.current = true;
              requestAnimationFrame(() => {
                isFrameScheduledRef.current = false;
                const target = pendingUriRef.current;
                if (target && isMountedRef.current) {
                  setDisplayedUri(target);
                  lastDecodedAtRef.current = Date.now();
                }
              });
            }
          } catch (err) {
            console.warn('[ScreenViewport] Frame processing error:', err);
          }
        };

        ws.onerror = err => {
          console.log('[ScreenViewport] Stream socket event:', err);
        };

        ws.onclose = () => {
          console.log('[ScreenViewport] Stream disconnected');
          if (watchdogTimerRef.current) {
            clearInterval(watchdogTimerRef.current);
            watchdogTimerRef.current = null;
          }
          wsRef.current = null;

          if (reconnectTimerRef.current) {
            clearTimeout(reconnectTimerRef.current);
            reconnectTimerRef.current = null;
          }

          if (isManualStopRef.current || !isMountedRef.current) {
            setIsStreaming(false);
          } else {
            // Auto-reconnect after transient disconnection
            reconnectTimerRef.current = setTimeout(() => {
              if (isMountedRef.current && !isManualStopRef.current && !wsRef.current) {
                console.log('[ScreenViewport] Auto-reconnecting to stream...');
                startStreamFn();
              }
            }, 1500);
          }
        };

        // ---- Render-health watchdog --------------------------------------
        watchdogTimerRef.current = setInterval(() => {
          const now = Date.now();
          const connectedAt = connectedAtRef.current;
          const lastFrame = lastFrameAtRef.current;
          const lastDecoded = lastDecodedAtRef.current;

          // Grace period: allow 6 seconds after connecting before checking for stalls
          if (connectedAt === 0 || now - connectedAt < 6000) return;

          // Stall conditions:
          // 1. Frame capture stalled: no frame received in over 6s
          // 2. Decode stalled: frames are arriving but not rendering for over 6s
          const frameStalled = now - lastFrame > 6000;
          const decodeStalled = now - lastDecoded > 6000 && frameCountRef.current > 0;

          if ((frameStalled || decodeStalled) && wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            console.warn(
              `[ScreenViewport] Render watchdog: frameStalled=${frameStalled}, decodeStalled=${decodeStalled}; restarting stream...`
            );
            try {
              wsRef.current.close();
            } catch {
              /* ignore */
            }
          }
        }, 1000);
      };

      fetchToken()
        .then(openSocket)
        .catch(err => {
          console.error('[ScreenViewport] Failed to mint stream token:', err);
          if (!isManualStopRef.current && isMountedRef.current) {
            reconnectTimerRef.current = setTimeout(() => {
              if (isMountedRef.current && !isManualStopRef.current && !wsRef.current) {
                startStreamFn();
              }
            }, 2000);
          } else {
            setIsStreaming(false);
          }
        });
    },
    [targetIp, targetPort, activeToken, selectedRes.w, selectedRes.h, selectedFps, selectedQuality]
  );

  // Listen to AppState (foreground/background) to recover stream on app resume
  useEffect(() => {
    const handleAppStateChange = (nextAppState: string) => {
      if (nextAppState === 'active') {
        console.log('[ScreenViewport] App resumed from background');
        if (isMountedRef.current && !isManualStopRef.current && (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN)) {
          startStream();
        }
      }
    };

    const subscription = AppState.addEventListener('change', handleAppStateChange);
    return () => {
      subscription.remove();
    };
  }, [startStream]);

  // Auto-start screen stream on component mount & clean up on unmount
  useEffect(() => {
    isMountedRef.current = true;
    startStream();

    return () => {
      isMountedRef.current = false;
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
      stopStream();
    };
  }, [startStream, stopStream]);

  const hasFrame = displayedUri != null;

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
              {isStreaming
                ? fps > 0 || kbps > 0
                  ? `${fps} FPS | ${kbps} kbps`
                  : 'Connecting...'
                : 'Screen Offline'}
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
          <ExpoImage
            source={{ uri: displayedUri! }}
            style={StyleSheet.absoluteFill}
            contentFit="contain"
            transition={0}
            cachePolicy="none"
            priority="high"
            onError={() => {
              console.warn('[ScreenViewport] Image decode error on active buffer');
            }}
          />
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

              <Text style={[styles.fieldLabel, { marginTop: Spacing.md }]}>Stream Server Port</Text>
              <TextInput
                style={styles.modalInput}
                placeholder={String(streamPort)}
                placeholderTextColor={palette.outline}
                value={customPort}
                keyboardType="numeric"
                onChangeText={setCustomPort}
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
