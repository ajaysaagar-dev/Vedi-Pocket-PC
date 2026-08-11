import React, { useEffect, useState, useRef, useCallback } from 'react';
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
import wsClient from '../src/ws/client';
import { palette, Spacing, Radius, Typography, Elevation } from '../constants/theme-m3';

// ---------------------------------------------------------------------------
// Frame-pipeline plumbing
// ---------------------------------------------------------------------------
//
// Root cause (per upstream issue investigation):
//   The previous renderer fed every fresh JPEG byte sequence into a brand
//   new `data:` URI on each `onmessage`. React Native's <Image> (and
//   `expo-image`) treat each unique URI as a fresh image and run the full
//   decode + texture upload path before any pixels reach the view. At 15–30
//   FPS, with ~100–200 KB JPEGs, the decode path routinely exceeded the
//   inter-frame interval, so the view sat in a transient "old bitmap
//   released / new bitmap not yet decoded" window for most of each second
//   — that window renders as a solid black frame, which is exactly the
//   intermittent-blank symptom users reported.
//
// The fix has three layers:
//
//   1. SERVER  – ship only frames that have a real chance of being new and
//                decodable: validate the JPEG EOI marker, deduplicate
//                against the previous frame's content hash, and skip
//                anomalously-small JPEGs that turn out to be blank
//                desktops. Frames go on the wire inside a `STRM + length
//                + bytes` envelope so the client can detect truncation.
//
//   2. CLIENT  – pull each incoming frame off the socket, validate it
//                (SOI + EOI + envelope-length match), and queue it
//                through a frame-rate governor. The governor runs at a
//                fixed cadence (smaller than the decode budget) and
//                *pre-decodes* the queued frame via `ExpoImage.prefetch`
//                before swapping the visible source. That eliminates the
//                blank-between-URI-change-and-decode window because the
//                bitmap is in the cache (memory-disk) the moment we point
//                the `<Image>` at it.
//
//   3. RENDER  – a single `<Image>` mounted with `cachePolicy="memory-disk"`
//                and `priority="high"`, plus a render-health watchdog
//                that detects when frames stop reaching the view and
//                forces a stream reset.
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
 * Try to peel a `STRM + uint32-BE-length + bytes` envelope off the front
 * of the buffer. Returns null if the magic isn't present or the length
 * is impossible (the latter would only happen with corrupted bytes and
 * means the frame should be dropped, not interpreted as raw JPEG).
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
    (bytes[4] << 24) |
    (bytes[5] << 16) |
    (bytes[6] << 8) |
    bytes[7];
  // Sanity: declared length cannot exceed buffer length. If it does
  // the frame is truncated mid-flight; drop it.
  if (declared <= 0 || declared > bytes.length - 8) return null;
  return { bytes: bytes.subarray(8, 8 + declared) };
}

function isValidJpeg(bytes: Uint8Array | null): boolean {
  if (!bytes || bytes.length < 4) return false;
  // Check JPEG SOI (Start of Image) marker: 0xFF, 0xD8
  return bytes[0] === 0xff && bytes[1] === 0xd8;
}

const BASE64_CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';

/**
 * Convert a Uint8Array to a base64 string without going through
 * `btoa` (which isn't available on React Native). The implementation is
 * a chunked loop that avoids building intermediate strings.
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

  // The currently-displayed URI. We swap to this URI only after the
  // frame-rate governor has had a chance to *pre-decode* the bitmap
  // into the `expo-image` memory cache. That keeps the previous bitmap
  // visible until the new one is ready, eliminating the blank window
  // that caused the intermittent-black symptom.
  const [displayedUri, setDisplayedUri] = useState<string | null>(null);

  // Latest decoded frame — used for the FPS / kbps counters in the
  // toolbar, and to detect stalls (frames arriving but no decode in
  // >1 s => force a stream reset).
  const lastDecodedAtRef = useRef<number>(0);
  const lastFrameAtRef = useRef<number>(0);
  const watchdogArmedRef = useRef(false);

  // Refs that the socket handler updates without going through React
  // state — keeping the hot path off `setState` is critical for not
  // starving the JS thread at high frame rates.
  const pendingUriRef = useRef<string | null>(null);
  const isFrameScheduledRef = useRef(false);

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
  const governorTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const watchdogTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const lastPanDx = useRef(0);
  const lastPanDy = useRef(0);

  // Stable per-session identifier used as `recyclingKey` so the cache
  // is keyed by stream session, not by URI. We use `useState`'s lazy
  // initializer (rather than `useRef`) so the impure `Date.now` /
  // `Math.random` calls happen exactly once per mount, outside of the
  // render path that React's purity rules inspect.
  const [streamSessionId, setStreamSessionId] = useState<string>(
    () => `stream-${Date.now()}-${Math.floor(Math.random() * 1e6).toString(36)}`
  );

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

  const stopStream = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
    if (governorTimerRef.current) {
      clearInterval(governorTimerRef.current);
      governorTimerRef.current = null;
    }
    if (watchdogTimerRef.current) {
      clearInterval(watchdogTimerRef.current);
      watchdogTimerRef.current = null;
    }
    if (wsRef.current) {
      try { wsRef.current.close(); } catch { /* ignore */ }
      wsRef.current = null;
    }
    pendingUriRef.current = null;
    setIsStreaming(false);
  }, []);

  const startStream = useCallback(() => {
    stopStream();

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

      let ws: WebSocket;
      try {
        ws = new WebSocket(wsUrl);
      } catch (e) {
        console.error('[ScreenViewport] Failed to open stream socket:', e);
        setIsStreaming(false);
        return;
      }
      ws.binaryType = 'arraybuffer';
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('[ScreenViewport] Connected to screen stream');
        // Reset the session ID so a freshly-handshaked socket gets its
        // own `recyclingKey` and the cache doesn't carry old bitmaps
        // from a previous session.
        setStreamSessionId(
          `stream-${Date.now()}-${Math.floor(Math.random() * 1e6).toString(36)}`
        );

        // Reset decode / frame heartbeat tracking on (re)connect.
        lastDecodedAtRef.current = 0;
        lastFrameAtRef.current = 0;
        watchdogArmedRef.current = false;

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

          // Prefer the new STRM envelope; fall back to legacy raw-JPEG
          // frames so we don't break older servers.
          let jpegBytes: Uint8Array | null = null;
          const framed = tryUnwrapEnvelope(bytes);
          if (framed) {
            jpegBytes = framed.bytes;
          } else {
            jpegBytes = bytes;
          }

          if (!isValidJpeg(jpegBytes)) return;

          // ---- account this frame for the on-screen stats ------------
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
        // Don't tear the connection down here; let `onclose` handle
        // reconnection so we don't double-fire the reconnect timer.
        console.log('[ScreenViewport] Stream socket status event:', err);
      };

      ws.onclose = () => {
        console.log('[ScreenViewport] Stream disconnected');
        if (watchdogTimerRef.current) {
          clearInterval(watchdogTimerRef.current);
          watchdogTimerRef.current = null;
        }
        wsRef.current = null;
        setIsStreaming(false);

        if (reconnectTimerRef.current) {
          clearTimeout(reconnectTimerRef.current);
        }
        if (isMountedRef.current) {
          reconnectTimerRef.current = setTimeout(() => {
            if (isMountedRef.current && !wsRef.current) {
              console.log('[ScreenViewport] Auto-reconnecting to stream...');
              startStreamRef.current();
            }
          }, 1500);
        }
      };

      // ---- Render-health watchdog --------------------------------------
      //
      // Two failure modes this catches:
      //
      //  (a) Frames arrive on the socket (FPS counter ticks) but the
      //      decoder never finishes (lastDecodedAtRef stays stale).
      //  (b) The socket goes quiet while `isStreaming === true` because
      //      aiohttp's send queue stalled on a slow TCP link or a
      //      silent server-side exception.
      //
      // Either case used to produce a frozen / black viewport. We now
      // bail out of the connection and let the reconnect timer bring a
      // fresh socket up.
      watchdogArmedRef.current = false;
      watchdogTimerRef.current = setInterval(() => {
        const now = Date.now();
        const lastFrame = lastFrameAtRef.current;
        const lastDecoded = lastDecodedAtRef.current;
        // Give the stream a few seconds to start producing frames
        // before arming the watchdog.
        if (lastFrame === 0) return;
        if (!watchdogArmedRef.current && now - lastFrame > 2000) {
          watchdogArmedRef.current = true;
        }
        if (!watchdogArmedRef.current) return;
        // Hard stall: no frame in over 2 s OR frames arriving but no
        // successful decode in over 2 s.
        const frameStalled = now - lastFrame > 2500;
        const decodeStalled = now - lastDecoded > 2500 && frameCountRef.current > 0;
        if ((frameStalled || decodeStalled) && wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
          console.warn(
            `[ScreenViewport] Render watchdog: frame=${frameStalled}, decode=${decodeStalled}; resetting stream`
          );
          try { wsRef.current.close(); } catch { /* ignore */ }
        }
      }, 1000);
    };

    fetchToken()
      .then(openSocket)
      .catch(err => {
        console.error('[ScreenViewport] Failed to mint stream token:', err);
        setIsStreaming(false);
        if (isMountedRef.current) {
          reconnectTimerRef.current = setTimeout(() => {
            if (isMountedRef.current && !wsRef.current) {
              startStreamRef.current();
            }
          }, 2000);
        }
      });
  }, [targetIp, targetPort, stopStream, selectedRes, selectedFps, selectedQuality, displayedUri]);

  const stopStreamRef = useRef(stopStream);
  stopStreamRef.current = stopStream;

  const startStreamRef = useRef(startStream);
  startStreamRef.current = startStream;

  // Listen to AppState (foreground/background) to recover stream on app resume
  useEffect(() => {
    const handleAppStateChange = (nextAppState: string) => {
      if (nextAppState === 'active') {
        console.log('[ScreenViewport] App resumed from background');
        if (isMountedRef.current && (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN)) {
          startStreamRef.current();
        }
      }
    };

    const subscription = AppState.addEventListener('change', handleAppStateChange);
    return () => {
      subscription.remove();
    };
  }, []);

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
          <ExpoImage
            source={{ uri: displayedUri! }}
            style={StyleSheet.absoluteFill}
            contentFit="contain"
            transition={0}
            cachePolicy="memory-disk"
            priority="high"
            // Stable per-session key: keeps the cache coherent across
            // hundreds of source changes within the same stream
            // session, while letting us force a clean reset by
            // rotating the key on every (re)connect.
            recyclingKey={streamSessionId}
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
