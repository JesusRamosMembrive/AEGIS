/**
 * Gemini Terminal Embed
 *
 * Embedded terminal for Gemini CLI with robust dimension handling.
 *
 * CRITICAL: The PTY requires correct dimensions (cols/rows) to avoid line break issues.
 * This component uses:
 * - Fixed height CSS (not flex) for predictable dimensions
 * - containerReady state to wait for valid dimensions before init
 * - safeFit() function to validate and correct terminal dimensions
 * - Backend validation as second line of defense
 */

import { useEffect, useMemo, useRef, useState, memo, useCallback } from "react";
import { Terminal } from "@xterm/xterm";
import { FitAddon } from "@xterm/addon-fit";
import { WebLinksAddon } from "@xterm/addon-web-links";
import { useBackendStore } from "../state/useBackendStore";
import { resolveBackendBaseUrl } from "../api/client";

import "@xterm/xterm/css/xterm.css";

// Constants for dimension validation
const MIN_VALID_COLS = 40;
const MIN_VALID_ROWS = 10;
const DEFAULT_COLS = 80;
const DEFAULT_ROWS = 24;
const MIN_CONTAINER_SIZE = 100; // pixels

interface GeminiTerminalEmbedProps {
  selectedModel: string;
  cwd?: string;
  onError?: (error: string) => void;
}

function GeminiTerminalEmbedInner({
  selectedModel,
  cwd,
  onError,
}: GeminiTerminalEmbedProps) {
  const [connected, setConnected] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [containerReady, setContainerReady] = useState(false);

  const backendUrl = useBackendStore((state) => state.backendUrl);

  const terminalRef = useRef<HTMLDivElement>(null);
  const xtermRef = useRef<Terminal | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const fitAddonRef = useRef<FitAddon | null>(null);
  const disposablesRef = useRef<{
    data?: { dispose: () => void };
    resize?: { dispose: () => void };
    observer?: ResizeObserver;
  }>({});

  // Build WebSocket URL
  const wsBaseUrl = useMemo(() => {
    const stripApi = (value: string) =>
      value.endsWith("/api") ? value.slice(0, -4) : value;

    const base =
      resolveBackendBaseUrl(backendUrl) ??
      (typeof window !== "undefined"
        ? window.location.origin
        : "http://127.0.0.1:8010");

    const sanitized = base.replace(/\/+$/, "");
    return stripApi(sanitized);
  }, [backendUrl]);

  // Safe fit function that validates and corrects dimensions
  const safeFit = useCallback((): { cols: number; rows: number } => {
    const container = terminalRef.current;
    const terminal = xtermRef.current;
    const fitAddon = fitAddonRef.current;

    if (!container || !terminal || !fitAddon) {
      console.log("[GeminiTerminal] safeFit: refs not ready, using defaults");
      return { cols: DEFAULT_COLS, rows: DEFAULT_ROWS };
    }

    const rect = container.getBoundingClientRect();

    // Validate container has proper dimensions
    if (rect.width < MIN_CONTAINER_SIZE || rect.height < MIN_CONTAINER_SIZE) {
      console.warn(`[GeminiTerminal] safeFit: container too small (${rect.width}x${rect.height}), using defaults`);
      terminal.resize(DEFAULT_COLS, DEFAULT_ROWS);
      return { cols: DEFAULT_COLS, rows: DEFAULT_ROWS };
    }

    // Perform fit
    try {
      fitAddon.fit();
    } catch (err) {
      console.error("[GeminiTerminal] safeFit: fit() failed:", err);
      terminal.resize(DEFAULT_COLS, DEFAULT_ROWS);
      return { cols: DEFAULT_COLS, rows: DEFAULT_ROWS };
    }

    const { cols, rows } = terminal;

    // Validate result
    if (cols < MIN_VALID_COLS || rows < MIN_VALID_ROWS) {
      console.warn(`[GeminiTerminal] safeFit: invalid dimensions (${cols}x${rows}), forcing defaults`);
      terminal.resize(DEFAULT_COLS, DEFAULT_ROWS);
      return { cols: DEFAULT_COLS, rows: DEFAULT_ROWS };
    }

    console.log(`[GeminiTerminal] safeFit: success (${cols}x${rows})`);
    return { cols, rows };
  }, []);

  // Step 1: Wait for container to have valid dimensions
  useEffect(() => {
    const container = terminalRef.current;
    if (!container) return;

    const checkDimensions = () => {
      const rect = container.getBoundingClientRect();
      if (rect.width >= MIN_CONTAINER_SIZE && rect.height >= MIN_CONTAINER_SIZE) {
        console.log(`[GeminiTerminal] Container ready: ${rect.width}x${rect.height}`);
        setContainerReady(true);
        return true;
      }
      return false;
    };

    // Check immediately
    if (checkDimensions()) return;

    // Use ResizeObserver as fallback
    console.log("[GeminiTerminal] Waiting for container dimensions...");
    const observer = new ResizeObserver(() => {
      if (checkDimensions()) {
        observer.disconnect();
      }
    });
    observer.observe(container);

    return () => observer.disconnect();
  }, []);

  // Step 2: Initialize terminal ONLY when container is ready
  useEffect(() => {
    if (!containerReady || !terminalRef.current || xtermRef.current) return;

    const container = terminalRef.current;
    const rect = container.getBoundingClientRect();

    console.log(`[GeminiTerminal] Initializing terminal with container: ${rect.width}x${rect.height}`);

    const terminal = new Terminal({
      cursorBlink: true,
      fontSize: 14,
      fontFamily: '"JetBrains Mono", "Fira Code", "Cascadia Code", monospace',
      theme: {
        background: "#0a0e18",
        foreground: "#e2e8f0",
        cursor: "#10b981",
        black: "#1e293b",
        red: "#ef4444",
        green: "#10b981",
        yellow: "#f59e0b",
        blue: "#3b82f6",
        magenta: "#a855f7",
        cyan: "#06b6d4",
        white: "#f1f5f9",
        brightBlack: "#475569",
        brightRed: "#f87171",
        brightGreen: "#34d399",
        brightYellow: "#fbbf24",
        brightBlue: "#60a5fa",
        brightMagenta: "#c084fc",
        brightCyan: "#22d3ee",
        brightWhite: "#ffffff",
      },
      cols: DEFAULT_COLS,
      rows: DEFAULT_ROWS,
      scrollback: 10000,
      disableStdin: false,
    });

    const fitAddon = new FitAddon();
    const webLinksAddon = new WebLinksAddon();

    terminal.loadAddon(fitAddon);
    terminal.loadAddon(webLinksAddon);

    terminal.open(container);

    xtermRef.current = terminal;
    fitAddonRef.current = fitAddon;

    // Fit after DOM is stable
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        const dims = safeFit();
        console.log(`[GeminiTerminal] Initial fit: ${dims.cols}x${dims.rows}`);
      });
    });

    // Welcome message
    terminal.writeln("\x1b[1;32mGemini Terminal Mode\x1b[0m");
    terminal.writeln("\x1b[2mInteractive terminal with native approval prompts.\x1b[0m");
    terminal.writeln("");
    terminal.writeln("\x1b[2mClick 'Connect' to start shell session...\x1b[0m");
    terminal.writeln("");

    return () => {
      terminal.dispose();
      xtermRef.current = null;
      fitAddonRef.current = null;
    };
  }, [containerReady, safeFit]);

  // Cleanup WebSocket on unmount
  useEffect(() => {
    return () => {
      if (disposablesRef.current.data) {
        disposablesRef.current.data.dispose();
        disposablesRef.current.data = undefined;
      }
      if (disposablesRef.current.resize) {
        disposablesRef.current.resize.dispose();
        disposablesRef.current.resize = undefined;
      }
      if (disposablesRef.current.observer) {
        disposablesRef.current.observer.disconnect();
        disposablesRef.current.observer = undefined;
      }

      if (wsRef.current) {
        const socket = wsRef.current;
        if (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING) {
          socket.close(1000, "Component unmounting");
        }
        wsRef.current = null;
      }
    };
  }, []);

  // Connect to shell
  const connectToShell = useCallback(() => {
    if (!xtermRef.current) {
      setError("Terminal not initialized");
      return;
    }

    if (wsRef.current && (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING)) {
      return;
    }

    const terminal = xtermRef.current;
    const wsUrl = wsBaseUrl.replace("http://", "ws://").replace("https://", "wss://");

    console.log(`[GeminiTerminal] Connecting to ${wsUrl}/api/terminal/ws`);

    setConnecting(true);
    setError(null);

    const socket = new WebSocket(`${wsUrl}/api/terminal/ws`);

    socket.onopen = () => {
      console.log("[GeminiTerminal] ✅ WebSocket connected");
      setConnected(true);
      setConnecting(false);
      setError(null);

      // Wait for DOM to stabilize, then fit and send resize
      requestAnimationFrame(() => {
        const dims = safeFit();
        console.log(`[GeminiTerminal] Sending resize: ${dims.cols}x${dims.rows}`);
        socket.send(`__RESIZE__:${dims.cols}:${dims.rows}`);
      });

      terminal.clear();
      terminal.writeln("\x1b[1;32m✓ Connected to shell\x1b[0m");
      terminal.writeln("");
      terminal.writeln(`\x1b[2mTip: Type 'gemini --model ${selectedModel}' to start Gemini CLI\x1b[0m`);
      terminal.writeln("");
    };

    socket.onmessage = (event) => {
      xtermRef.current?.write(event.data);
    };

    socket.onerror = (err) => {
      console.error("[GeminiTerminal] ❌ WebSocket error:", err);
      setConnected(false);
      setConnecting(false);
      const errorMsg = "Connection error";
      setError(errorMsg);
      onError?.(errorMsg);
      xtermRef.current?.writeln("\n\x1b[1;31m✗ Connection error\x1b[0m");
    };

    socket.onclose = (event) => {
      console.log(`[GeminiTerminal] WebSocket closed: code=${event.code}`);
      setConnected(false);
      setConnecting(false);
      if (!error) {
        xtermRef.current?.writeln("\n\x1b[2mConnection closed\x1b[0m");
      }
    };

    wsRef.current = socket;

    // Handle terminal input
    disposablesRef.current.data = xtermRef.current.onData((data) => {
      if (socket.readyState === WebSocket.OPEN) {
        socket.send(data);
      }
    });

    // Handle terminal resize events
    const sendResize = () => {
      if (socket?.readyState === WebSocket.OPEN && xtermRef.current) {
        const { cols, rows } = xtermRef.current;
        if (cols >= MIN_VALID_COLS && rows >= MIN_VALID_ROWS) {
          socket.send(`__RESIZE__:${cols}:${rows}`);
        }
      }
    };

    disposablesRef.current.resize = xtermRef.current.onResize(() => {
      sendResize();
    });

    // Debounced ResizeObserver
    let resizeTimeout: ReturnType<typeof setTimeout> | null = null;
    disposablesRef.current.observer = new ResizeObserver(() => {
      if (resizeTimeout) clearTimeout(resizeTimeout);
      resizeTimeout = setTimeout(() => {
        safeFit();
        sendResize();
      }, 150); // 150ms debounce
    });

    if (terminalRef.current) {
      disposablesRef.current.observer.observe(terminalRef.current);
    }
  }, [wsBaseUrl, selectedModel, onError, error, safeFit]);

  // Disconnect from shell
  const disconnectFromShell = useCallback(() => {
    if (disposablesRef.current.data) {
      disposablesRef.current.data.dispose();
      disposablesRef.current.data = undefined;
    }
    if (disposablesRef.current.resize) {
      disposablesRef.current.resize.dispose();
      disposablesRef.current.resize = undefined;
    }
    if (disposablesRef.current.observer) {
      disposablesRef.current.observer.disconnect();
      disposablesRef.current.observer = undefined;
    }

    if (wsRef.current) {
      const socket = wsRef.current;
      if (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING) {
        socket.close();
      }
      wsRef.current = null;
    }

    setConnected(false);
    setConnecting(false);
  }, []);

  return (
    <div className="gemini-terminal-embed">
      <div className="gemini-terminal-header">
        <span className="gemini-terminal-title">
          <span className="gemini-icon">G</span>
          Gemini Terminal
        </span>
        <div className="gemini-terminal-controls">
          {!connected && !connecting && (
            <button onClick={connectToShell} className="gemini-btn">
              Connect
            </button>
          )}
          {connecting && (
            <span className="gemini-status connecting">Connecting...</span>
          )}
          {connected && (
            <>
              <span className="gemini-status connected">
                <span className="status-dot" />
                Connected
              </span>
              <button onClick={disconnectFromShell} className="gemini-btn">
                Disconnect
              </button>
            </>
          )}
          {error && <span className="gemini-status error">{error}</span>}
        </div>
      </div>
      <div ref={terminalRef} className="gemini-terminal-content" />
      <div className="gemini-terminal-footer">
        <span className="gemini-hint">
          Type your prompts directly. Use Ctrl+C to cancel.
        </span>
        <span className="gemini-model">Model: {selectedModel}</span>
      </div>

      <style>{geminiTerminalStyles}</style>
    </div>
  );
}

const geminiTerminalStyles = `
.gemini-terminal-embed {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: rgba(15, 23, 42, 0.6);
  backdrop-filter: blur(10.5px);
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 12px;
  overflow: hidden;
}

.gemini-terminal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 14px;
  background: rgba(30, 41, 59, 0.7);
  border-bottom: 1px solid rgba(148, 163, 184, 0.15);
}

.gemini-terminal-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 500;
  color: #e2e8f0;
}

.gemini-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  background: linear-gradient(135deg, #4285f4, #34a853);
  border-radius: 6px;
  font-size: 12px;
  font-weight: 700;
  color: white;
}

.gemini-terminal-controls {
  display: flex;
  align-items: center;
  gap: 10px;
}

.gemini-btn {
  padding: 5px 12px;
  font-size: 12px;
  font-weight: 500;
  background: rgba(59, 130, 246, 0.3);
  border: 1px solid rgba(59, 130, 246, 0.5);
  border-radius: 6px;
  color: #60a5fa;
  cursor: pointer;
  transition: all 0.2s;
}

.gemini-btn:hover {
  background: rgba(59, 130, 246, 0.5);
  border-color: rgba(59, 130, 246, 0.7);
}

.gemini-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  padding: 4px 10px;
  border-radius: 6px;
}

.gemini-status.connecting {
  color: #f59e0b;
  background: rgba(245, 158, 11, 0.15);
}

.gemini-status.connected {
  color: #10b981;
  background: rgba(16, 185, 129, 0.15);
}

.gemini-status.error {
  color: #ef4444;
  background: rgba(239, 68, 68, 0.15);
}

.gemini-status .status-dot {
  width: 6px;
  height: 6px;
  background: #10b981;
  border-radius: 50%;
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* CRITICAL: Use fixed height, NOT flex, for predictable terminal dimensions */
.gemini-terminal-content {
  height: 500px;
  min-height: 400px;
  padding: 8px;
  position: relative;
  background: #0a0e18;
}

.gemini-terminal-content .xterm {
  height: 100%;
  width: 100%;
}

.gemini-terminal-content .xterm-screen {
  height: 100% !important;
  width: 100% !important;
}

.gemini-terminal-content .xterm-viewport {
  overflow-y: auto;
  height: 100% !important;
}

.gemini-terminal-content .xterm-viewport::-webkit-scrollbar {
  width: 8px;
}

.gemini-terminal-content .xterm-viewport::-webkit-scrollbar-track {
  background: rgba(15, 23, 42, 0.5);
}

.gemini-terminal-content .xterm-viewport::-webkit-scrollbar-thumb {
  background: rgba(148, 163, 184, 0.3);
  border-radius: 4px;
}

.gemini-terminal-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 14px;
  background: rgba(15, 23, 42, 0.5);
  border-top: 1px solid rgba(148, 163, 184, 0.1);
  font-size: 11px;
  color: #64748b;
}

.gemini-hint {
  opacity: 0.8;
}

.gemini-model {
  font-family: 'JetBrains Mono', monospace;
  background: rgba(66, 133, 244, 0.15);
  padding: 2px 8px;
  border-radius: 4px;
  color: #60a5fa;
}
`;

// Export memoized component to prevent re-renders from parent state changes
export const GeminiTerminalEmbed = memo(GeminiTerminalEmbedInner);
