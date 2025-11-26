/**
 * Claude Agent View
 *
 * UI for interacting with Claude Code via JSON streaming mode.
 * Replaces the TUI-based terminal with a structured, custom-rendered interface.
 */

import { useEffect, useRef, useState, useCallback } from "react";
import { useClaudeSessionStore } from "../stores/claudeSessionStore";
import { useBackendStore } from "../state/useBackendStore";
import { resolveBackendBaseUrl } from "../api/client";
import {
  ClaudeMessage,
  getToolIcon,
  formatToolInput,
} from "../types/claude-events";

// ============================================================================
// Main Component
// ============================================================================

export function ClaudeAgentView() {
  const [promptValue, setPromptValue] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Store state
  const {
    connected,
    connecting,
    running,
    messages,
    sessionInfo,
    lastError,
    cwd,
    activeToolCalls,
    connect,
    disconnect,
    sendPrompt,
    cancel,
    newSession,
    clearMessages,
  } = useClaudeSessionStore();

  const backendUrl = useBackendStore((state) => state.backendUrl);

  // Build WebSocket URL
  const getWsUrl = useCallback(() => {
    const stripApi = (value: string) =>
      value.endsWith("/api") ? value.slice(0, -4) : value;

    const base =
      resolveBackendBaseUrl(backendUrl) ??
      (typeof window !== "undefined"
        ? window.location.origin
        : "http://127.0.0.1:8010");

    const sanitized = base.replace(/\/+$/, "");
    const httpBase = stripApi(sanitized);
    const wsBase = httpBase.replace(/^http/, "ws");
    return `${wsBase}/api/terminal/ws/agent`;
  }, [backendUrl]);

  // Auto-connect on mount
  useEffect(() => {
    if (!connected && !connecting) {
      const wsUrl = getWsUrl();
      console.log("[ClaudeAgent] Connecting to:", wsUrl);
      connect(wsUrl);
    }
  }, [connected, connecting, connect, getWsUrl]);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Handle submit
  const handleSubmit = useCallback(
    (e?: React.FormEvent) => {
      e?.preventDefault();
      if (!promptValue.trim() || running) return;

      sendPrompt(promptValue.trim());
      setPromptValue("");
    },
    [promptValue, running, sendPrompt]
  );

  // Handle key press in textarea
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSubmit();
      }
    },
    [handleSubmit]
  );

  // Reconnect
  const handleReconnect = useCallback(() => {
    disconnect();
    setTimeout(() => {
      const wsUrl = getWsUrl();
      connect(wsUrl);
    }, 100);
  }, [disconnect, connect, getWsUrl]);

  return (
    <div className="claude-agent-view">
      {/* Header */}
      <AgentHeader
        connected={connected}
        connecting={connecting}
        running={running}
        sessionInfo={sessionInfo}
        cwd={cwd}
        onReconnect={handleReconnect}
        onNewSession={newSession}
        onClearMessages={clearMessages}
      />

      {/* Messages Area */}
      <div className="claude-messages-container">
        {messages.length === 0 && !running ? (
          <EmptyState />
        ) : (
          <div className="claude-messages">
            {messages.map((msg, idx) => (
              <MessageItem key={msg.id || idx} message={msg} />
            ))}

            {/* Running indicator */}
            {running && (
              <div className="claude-thinking">
                <span className="thinking-icon">🤔</span>
                <span className="thinking-text">Claude is thinking...</span>
                {activeToolCalls.size > 0 && (
                  <span className="active-tools">
                    (Running {activeToolCalls.size} tool
                    {activeToolCalls.size > 1 ? "s" : ""})
                  </span>
                )}
              </div>
            )}

            {/* Error display */}
            {lastError && (
              <div className="claude-error">
                <span className="error-icon">!</span>
                <span className="error-text">{lastError}</span>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input Area */}
      <div className="claude-input-container">
        <form onSubmit={handleSubmit} className="claude-input-form">
          <textarea
            ref={inputRef}
            value={promptValue}
            onChange={(e) => setPromptValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              connected
                ? "Ask Claude anything... (Enter to send, Shift+Enter for newline)"
                : "Connecting..."
            }
            disabled={!connected || running}
            className="claude-input"
            rows={3}
          />
          <div className="claude-input-actions">
            <button
              type="submit"
              disabled={!connected || running || !promptValue.trim()}
              className="claude-send-btn"
            >
              Send
            </button>
            {running && (
              <button
                type="button"
                onClick={cancel}
                className="claude-cancel-btn"
              >
                Cancel
              </button>
            )}
          </div>
        </form>
      </div>

      <style>{styles}</style>
    </div>
  );
}

// ============================================================================
// Sub-Components
// ============================================================================

interface AgentHeaderProps {
  connected: boolean;
  connecting: boolean;
  running: boolean;
  sessionInfo: {
    sessionId: string | null;
    model: string | null;
    tools: string[];
    mcpServers: Array<{ name: string; status: string }>;
  };
  cwd: string | null;
  onReconnect: () => void;
  onNewSession: () => void;
  onClearMessages: () => void;
}

function AgentHeader({
  connected,
  connecting,
  running,
  sessionInfo,
  cwd,
  onReconnect,
  onNewSession,
  onClearMessages,
}: AgentHeaderProps) {
  return (
    <div className="claude-header">
      <div className="claude-header-left">
        <h2 className="claude-title">Claude Agent</h2>
        <div className="claude-status">
          <span
            className={`status-dot ${connected ? "connected" : connecting ? "connecting" : "disconnected"}`}
          />
          <span className="status-text">
            {connected ? "Connected" : connecting ? "Connecting..." : "Disconnected"}
          </span>
        </div>
        {sessionInfo.model && (
          <span className="claude-model">{sessionInfo.model}</span>
        )}
      </div>
      <div className="claude-header-right">
        {cwd && <span className="claude-cwd" title={cwd}>{truncatePath(cwd, 40)}</span>}
        <div className="claude-header-actions">
          <button onClick={onClearMessages} className="header-btn" title="Clear messages">
            Clear
          </button>
          <button onClick={onNewSession} className="header-btn" title="Start new session">
            New Session
          </button>
          {!connected && !connecting && (
            <button onClick={onReconnect} className="header-btn primary" title="Reconnect">
              Reconnect
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="claude-empty">
      <div className="empty-icon">💬</div>
      <h3>Start a conversation</h3>
      <p>Type a message below to start interacting with Claude Code.</p>
      <p className="empty-hint">
        Claude can read files, run commands, write code, and more.
      </p>
    </div>
  );
}

interface MessageItemProps {
  message: ClaudeMessage;
}

function MessageItem({ message }: MessageItemProps) {
  const [expanded, setExpanded] = useState(false);

  switch (message.type) {
    case "text":
      return (
        <div className="message message-text">
          <div className="message-content">
            <pre className="message-text-content">{String(message.content)}</pre>
          </div>
          <div className="message-meta">
            {message.timestamp.toLocaleTimeString()}
          </div>
        </div>
      );

    case "tool_use":
      const toolContent = message.content as {
        id: string;
        name: string;
        input: Record<string, unknown>;
      };
      return (
        <div className="message message-tool-use">
          <div
            className="tool-header"
            onClick={() => setExpanded(!expanded)}
          >
            <span className="tool-icon">{getToolIcon(toolContent.name)}</span>
            <span className="tool-name">{toolContent.name}</span>
            <span className="tool-expand">{expanded ? "▼" : "▶"}</span>
          </div>
          {expanded && (
            <div className="tool-details">
              <pre className="tool-input">
                {formatToolInput(toolContent.input, 500)}
              </pre>
            </div>
          )}
          <div className="message-meta">
            {message.timestamp.toLocaleTimeString()}
          </div>
        </div>
      );

    case "tool_result":
      const resultContent = String(message.content);
      const isLong = resultContent.length > 300;
      return (
        <div className={`message message-tool-result ${message.isError ? "error" : ""}`}>
          <div className="result-header">
            <span className="result-icon">{message.isError ? "!" : ">"}</span>
            <span className="result-label">Result</span>
            {isLong && (
              <button
                className="result-toggle"
                onClick={() => setExpanded(!expanded)}
              >
                {expanded ? "Collapse" : "Expand"}
              </button>
            )}
          </div>
          <pre className={`result-content ${!expanded && isLong ? "truncated" : ""}`}>
            {expanded || !isLong ? resultContent : resultContent.substring(0, 300) + "..."}
          </pre>
          <div className="message-meta">
            {message.timestamp.toLocaleTimeString()}
          </div>
        </div>
      );

    case "error":
      return (
        <div className="message message-error">
          <span className="error-icon">!</span>
          <span className="error-content">{String(message.content)}</span>
        </div>
      );

    case "system":
      return (
        <div className="message message-system">
          <span className="system-icon">i</span>
          <span className="system-content">{String(message.content)}</span>
        </div>
      );

    default:
      return null;
  }
}

// ============================================================================
// Helpers
// ============================================================================

function truncatePath(path: string, maxLength: number): string {
  if (path.length <= maxLength) return path;
  const parts = path.split("/");
  let result = parts[parts.length - 1];
  for (let i = parts.length - 2; i >= 0 && result.length < maxLength - 4; i--) {
    result = parts[i] + "/" + result;
  }
  return ".../" + result;
}

// ============================================================================
// Styles
// ============================================================================

const styles = `
.claude-agent-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #0a0e18;
  color: #e2e8f0;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}

/* Header */
.claude-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #111827;
  border-bottom: 1px solid #1e293b;
}

.claude-header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.claude-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #f1f5f9;
}

.claude-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.status-dot.connected {
  background: #10b981;
}

.status-dot.connecting {
  background: #f59e0b;
  animation: pulse 1s infinite;
}

.status-dot.disconnected {
  background: #ef4444;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.claude-model {
  font-size: 11px;
  padding: 2px 8px;
  background: #1e293b;
  border-radius: 4px;
  color: #94a3b8;
}

.claude-header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.claude-cwd {
  font-size: 11px;
  color: #64748b;
  font-family: monospace;
}

.claude-header-actions {
  display: flex;
  gap: 8px;
}

.header-btn {
  padding: 4px 12px;
  font-size: 12px;
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 4px;
  color: #94a3b8;
  cursor: pointer;
  transition: all 0.2s;
}

.header-btn:hover {
  background: #334155;
  color: #e2e8f0;
}

.header-btn.primary {
  background: #3b82f6;
  border-color: #3b82f6;
  color: white;
}

.header-btn.primary:hover {
  background: #2563eb;
}

/* Messages Container */
.claude-messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.claude-messages {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

/* Empty State */
.claude-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  text-align: center;
  color: #64748b;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.claude-empty h3 {
  margin: 0 0 8px;
  color: #94a3b8;
}

.claude-empty p {
  margin: 0 0 4px;
  font-size: 14px;
}

.empty-hint {
  font-size: 12px;
  color: #475569;
}

/* Messages */
.message {
  padding: 12px;
  border-radius: 8px;
  background: #111827;
  border: 1px solid #1e293b;
}

.message-meta {
  font-size: 10px;
  color: #475569;
  margin-top: 8px;
  text-align: right;
}

.message-text-content {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: inherit;
  font-size: 14px;
  line-height: 1.5;
}

/* Tool Use */
.message-tool-use {
  background: #0f172a;
  border-color: #3b82f6;
}

.tool-header {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
}

.tool-header:hover {
  background: #1e293b;
}

.tool-icon {
  font-size: 16px;
}

.tool-name {
  font-weight: 500;
  color: #60a5fa;
  font-family: monospace;
}

.tool-expand {
  margin-left: auto;
  font-size: 10px;
  color: #64748b;
}

.tool-details {
  margin-top: 8px;
  padding: 8px;
  background: #0a0e18;
  border-radius: 4px;
}

.tool-input {
  margin: 0;
  font-size: 12px;
  font-family: 'JetBrains Mono', monospace;
  color: #94a3b8;
  white-space: pre-wrap;
  word-break: break-word;
}

/* Tool Result */
.message-tool-result {
  background: #0f172a;
  border-color: #10b981;
}

.message-tool-result.error {
  border-color: #ef4444;
}

.result-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.result-icon {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #10b981;
  color: white;
  font-size: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.message-tool-result.error .result-icon {
  background: #ef4444;
}

.result-label {
  font-size: 12px;
  font-weight: 500;
  color: #64748b;
}

.result-toggle {
  margin-left: auto;
  padding: 2px 8px;
  font-size: 10px;
  background: transparent;
  border: 1px solid #334155;
  border-radius: 4px;
  color: #64748b;
  cursor: pointer;
}

.result-toggle:hover {
  background: #1e293b;
}

.result-content {
  margin: 0;
  font-size: 12px;
  font-family: 'JetBrains Mono', monospace;
  color: #94a3b8;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 400px;
  overflow-y: auto;
}

.result-content.truncated {
  max-height: 100px;
  overflow: hidden;
}

/* Error Message */
.message-error {
  background: #450a0a;
  border-color: #ef4444;
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.message-error .error-icon {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #ef4444;
  color: white;
  font-size: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.message-error .error-content {
  color: #fca5a5;
  font-size: 13px;
}

/* System Message */
.message-system {
  background: #172554;
  border-color: #3b82f6;
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 12px;
  color: #93c5fd;
}

.system-icon {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #3b82f6;
  color: white;
  font-size: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

/* Thinking */
.claude-thinking {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
  background: #1e293b;
  border-radius: 8px;
  color: #94a3b8;
}

.thinking-icon {
  font-size: 20px;
  animation: bounce 1s infinite;
}

@keyframes bounce {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-4px); }
}

.thinking-text {
  font-size: 14px;
}

.active-tools {
  font-size: 12px;
  color: #64748b;
}

/* Error Display */
.claude-error {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
  background: #450a0a;
  border: 1px solid #ef4444;
  border-radius: 8px;
  color: #fca5a5;
}

.claude-error .error-icon {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #ef4444;
  color: white;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Input Area */
.claude-input-container {
  padding: 16px;
  background: #111827;
  border-top: 1px solid #1e293b;
}

.claude-input-form {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.claude-input {
  width: 100%;
  padding: 12px;
  background: #0a0e18;
  border: 1px solid #334155;
  border-radius: 8px;
  color: #e2e8f0;
  font-size: 14px;
  font-family: inherit;
  resize: none;
  outline: none;
  transition: border-color 0.2s;
}

.claude-input:focus {
  border-color: #3b82f6;
}

.claude-input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.claude-input::placeholder {
  color: #64748b;
}

.claude-input-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.claude-send-btn {
  padding: 8px 24px;
  background: #3b82f6;
  border: none;
  border-radius: 6px;
  color: white;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;
}

.claude-send-btn:hover:not(:disabled) {
  background: #2563eb;
}

.claude-send-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.claude-cancel-btn {
  padding: 8px 24px;
  background: #ef4444;
  border: none;
  border-radius: 6px;
  color: white;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;
}

.claude-cancel-btn:hover {
  background: #dc2626;
}
`;
