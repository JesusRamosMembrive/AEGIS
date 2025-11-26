/**
 * Claude Session Store
 *
 * Manages Claude Code JSON streaming session state using Zustand.
 * Handles WebSocket connection, message processing, and UI state.
 */

import { create } from "zustand";
import { devtools, subscribeWithSelector } from "zustand/middleware";
import {
  ClaudeEvent,
  ClaudeMessage,
  ClaudeSessionInfo,
  ToolCall,
  AgentCommand,
  isSystemInitEvent,
  isTextEvent,
  isToolUseEvent,
  isToolResultEvent,
  isDoneEvent,
  isErrorEvent,
  generateMessageId,
} from "../types/claude-events";

// ============================================================================
// Store Interface
// ============================================================================

interface ClaudeSessionStore {
  // Connection state
  connected: boolean;
  connecting: boolean;
  wsUrl: string | null;
  cwd: string | null;

  // Session state
  running: boolean;
  sessionInfo: ClaudeSessionInfo;
  continueSession: boolean;

  // Messages and tool calls
  messages: ClaudeMessage[];
  activeToolCalls: Map<string, ToolCall>;
  completedToolCalls: ToolCall[];

  // Error handling
  lastError: string | null;

  // WebSocket instance (internal)
  _ws: WebSocket | null;

  // Actions
  connect: (wsUrl: string) => void;
  disconnect: () => void;
  sendPrompt: (prompt: string) => void;
  cancel: () => void;
  newSession: () => void;
  requestStatus: () => void;
  clearMessages: () => void;
  setError: (error: string | null) => void;

  // Event processing
  processEvent: (event: ClaudeEvent) => void;

  // Getters
  getActiveToolCall: () => ToolCall | undefined;
  getMessagesByType: (type: ClaudeMessage["type"]) => ClaudeMessage[];
  getToolCallById: (id: string) => ToolCall | undefined;
}

// ============================================================================
// Initial State
// ============================================================================

const initialSessionInfo: ClaudeSessionInfo = {
  sessionId: null,
  model: null,
  tools: [],
  mcpServers: [],
};

// ============================================================================
// Store Implementation
// ============================================================================

export const useClaudeSessionStore = create<ClaudeSessionStore>()(
  devtools(
    subscribeWithSelector((set, get) => ({
      // Initial state
      connected: false,
      connecting: false,
      wsUrl: null,
      cwd: null,
      running: false,
      sessionInfo: { ...initialSessionInfo },
      continueSession: true,
      messages: [],
      activeToolCalls: new Map(),
      completedToolCalls: [],
      lastError: null,
      _ws: null,

      // Connect to WebSocket
      connect: (wsUrl: string) => {
        const state = get();
        if (state._ws) {
          state._ws.close();
        }

        set({ connecting: true, wsUrl, lastError: null });

        const ws = new WebSocket(wsUrl);

        ws.onopen = () => {
          console.log("[ClaudeSession] WebSocket connected");
          set({ connected: true, connecting: false, _ws: ws });
        };

        ws.onclose = (event) => {
          console.log("[ClaudeSession] WebSocket closed:", event.code);
          set({
            connected: false,
            connecting: false,
            running: false,
            _ws: null,
          });
        };

        ws.onerror = (error) => {
          console.error("[ClaudeSession] WebSocket error:", error);
          set({
            connected: false,
            connecting: false,
            lastError: "Connection error",
            _ws: null,
          });
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data) as ClaudeEvent;
            get().processEvent(data);
          } catch (e) {
            console.error("[ClaudeSession] Failed to parse message:", e);
          }
        };

        set({ _ws: ws });
      },

      // Disconnect
      disconnect: () => {
        const { _ws } = get();
        if (_ws) {
          _ws.close();
        }
        set({
          connected: false,
          connecting: false,
          running: false,
          _ws: null,
        });
      },

      // Send a prompt
      sendPrompt: (prompt: string) => {
        const { _ws, connected, running, continueSession } = get();
        if (!_ws || !connected || running) {
          console.warn("[ClaudeSession] Cannot send prompt: not ready");
          return;
        }

        const command: AgentCommand = {
          command: "run",
          prompt,
          continue: continueSession,
        };

        _ws.send(JSON.stringify(command));
        set({ running: true, lastError: null });

        // Add user message to history
        const userMessage: ClaudeMessage = {
          id: generateMessageId(),
          type: "text",
          content: prompt,
          timestamp: new Date(),
        };

        set((state) => ({
          messages: [...state.messages, userMessage],
        }));
      },

      // Cancel running process
      cancel: () => {
        const { _ws, connected } = get();
        if (!_ws || !connected) return;

        const command: AgentCommand = { command: "cancel" };
        _ws.send(JSON.stringify(command));
      },

      // Start new session
      newSession: () => {
        const { _ws, connected } = get();
        if (!_ws || !connected) return;

        const command: AgentCommand = { command: "new_session" };
        _ws.send(JSON.stringify(command));

        // Clear local state
        set({
          messages: [],
          activeToolCalls: new Map(),
          completedToolCalls: [],
          sessionInfo: { ...initialSessionInfo },
          continueSession: false,
        });
      },

      // Request status
      requestStatus: () => {
        const { _ws, connected } = get();
        if (!_ws || !connected) return;

        const command: AgentCommand = { command: "status" };
        _ws.send(JSON.stringify(command));
      },

      // Clear messages
      clearMessages: () => {
        set({
          messages: [],
          activeToolCalls: new Map(),
          completedToolCalls: [],
        });
      },

      // Set error
      setError: (error: string | null) => {
        set({ lastError: error });
      },

      // Process incoming event
      processEvent: (event: ClaudeEvent) => {
        set((state) => {
          // Handle connection event
          if (event.type === "connected") {
            return {
              cwd: (event as { cwd: string }).cwd,
            };
          }

          // Handle system init
          if (isSystemInitEvent(event)) {
            const content = event.content;
            return {
              sessionInfo: {
                sessionId: content.session_id,
                model: content.model,
                tools: content.tools,
                mcpServers: content.mcp_servers,
              },
              continueSession: true, // Reset for next run
            };
          }

          // Handle text message
          if (isTextEvent(event)) {
            const message: ClaudeMessage = {
              id: generateMessageId(),
              type: "text",
              content: event.content,
              timestamp: new Date(),
              usage: event.usage,
            };
            return {
              messages: [...state.messages, message],
            };
          }

          // Handle tool use
          if (isToolUseEvent(event)) {
            const toolCall: ToolCall = {
              id: event.content.id,
              name: event.content.name,
              input: event.content.input,
              startTime: new Date(),
              status: "running",
            };

            const message: ClaudeMessage = {
              id: generateMessageId(),
              type: "tool_use",
              content: event.content,
              timestamp: new Date(),
              toolName: event.content.name,
              toolId: event.content.id,
              usage: event.usage,
            };

            const newActiveToolCalls = new Map(state.activeToolCalls);
            newActiveToolCalls.set(toolCall.id, toolCall);

            return {
              messages: [...state.messages, message],
              activeToolCalls: newActiveToolCalls,
            };
          }

          // Handle tool result
          if (isToolResultEvent(event)) {
            const toolId = event.content.tool_use_id;
            const existingToolCall = state.activeToolCalls.get(toolId);

            const message: ClaudeMessage = {
              id: generateMessageId(),
              type: "tool_result",
              content: event.content.content,
              timestamp: new Date(),
              toolId,
              isError: event.content.is_error,
            };

            const newActiveToolCalls = new Map(state.activeToolCalls);
            let newCompletedToolCalls = [...state.completedToolCalls];

            if (existingToolCall) {
              const completedToolCall: ToolCall = {
                ...existingToolCall,
                endTime: new Date(),
                result: event.content.content,
                isError: event.content.is_error,
                status: event.content.is_error ? "failed" : "completed",
              };
              newActiveToolCalls.delete(toolId);
              newCompletedToolCalls.push(completedToolCall);
            }

            return {
              messages: [...state.messages, message],
              activeToolCalls: newActiveToolCalls,
              completedToolCalls: newCompletedToolCalls,
            };
          }

          // Handle done
          if (isDoneEvent(event)) {
            return {
              running: false,
            };
          }

          // Handle error
          if (isErrorEvent(event)) {
            const message: ClaudeMessage = {
              id: generateMessageId(),
              type: "error",
              content: event.content,
              timestamp: new Date(),
              isError: true,
            };
            return {
              messages: [...state.messages, message],
              lastError: event.content,
              running: false,
            };
          }

          // Handle cancelled
          if (event.type === "cancelled") {
            return {
              running: false,
            };
          }

          // Handle session reset
          if (event.type === "session_reset") {
            return {
              sessionInfo: { ...initialSessionInfo },
              continueSession: false,
            };
          }

          // Handle status
          if (event.type === "status") {
            const statusEvent = event as {
              session_info: {
                session_id: string | null;
                model: string | null;
                tools: string[];
                mcp_servers: Array<{ name: string; status: string }>;
              };
              running: boolean;
              continue_session: boolean;
            };
            return {
              sessionInfo: {
                sessionId: statusEvent.session_info.session_id,
                model: statusEvent.session_info.model,
                tools: statusEvent.session_info.tools,
                mcpServers: statusEvent.session_info.mcp_servers,
              },
              running: statusEvent.running,
              continueSession: statusEvent.continue_session,
            };
          }

          return {};
        });
      },

      // Getters
      getActiveToolCall: () => {
        const state = get();
        const entries = Array.from(state.activeToolCalls.values());
        return entries[entries.length - 1];
      },

      getMessagesByType: (type: ClaudeMessage["type"]) => {
        const state = get();
        return state.messages.filter((m) => m.type === type);
      },

      getToolCallById: (id: string) => {
        const state = get();
        return (
          state.activeToolCalls.get(id) ||
          state.completedToolCalls.find((tc) => tc.id === id)
        );
      },
    })),
    {
      name: "claude-session-store",
    }
  )
);

// ============================================================================
// Selectors (for performance)
// ============================================================================

export const selectConnected = (state: ClaudeSessionStore) => state.connected;
export const selectRunning = (state: ClaudeSessionStore) => state.running;
export const selectMessages = (state: ClaudeSessionStore) => state.messages;
export const selectSessionInfo = (state: ClaudeSessionStore) =>
  state.sessionInfo;
export const selectLastError = (state: ClaudeSessionStore) => state.lastError;
export const selectActiveToolCalls = (state: ClaudeSessionStore) =>
  state.activeToolCalls;
