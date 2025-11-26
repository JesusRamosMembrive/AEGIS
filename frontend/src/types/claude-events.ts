/**
 * Claude Code JSON Streaming Event Types
 *
 * Types for events received from `claude -p --output-format stream-json --verbose`
 * Used by the ClaudeAgentView component for rendering structured Claude output.
 */

// ============================================================================
// Core Event Types
// ============================================================================

/**
 * Event type from Claude Code JSON stream
 */
export type ClaudeEventType =
  | "system"
  | "assistant"
  | "user"
  | "result"
  | "connected"
  | "done"
  | "error"
  | "cancelled"
  | "session_reset"
  | "status"
  | "unknown";

/**
 * Event subtype for more specific classification
 */
export type ClaudeEventSubtype =
  | "init"
  | "text"
  | "tool_use"
  | "tool_result"
  | "thinking"
  | "error"
  | "unknown";

// ============================================================================
// Event Interfaces
// ============================================================================

/**
 * Base event structure from WebSocket
 */
export interface ClaudeBaseEvent {
  type: ClaudeEventType;
  subtype?: ClaudeEventSubtype;
  timestamp?: string;
  session_id?: string | null;
}

/**
 * System initialization event
 */
export interface ClaudeSystemInitEvent extends ClaudeBaseEvent {
  type: "system";
  subtype: "init";
  content: {
    session_id: string;
    model: string;
    tools: string[];
    mcp_servers: Array<{ name: string; status: string }>;
  };
}

/**
 * Assistant text message event
 */
export interface ClaudeTextEvent extends ClaudeBaseEvent {
  type: "assistant";
  subtype: "text";
  content: string;
  usage?: ClaudeUsage;
}

/**
 * Assistant tool use event
 */
export interface ClaudeToolUseEvent extends ClaudeBaseEvent {
  type: "assistant";
  subtype: "tool_use";
  content: {
    id: string;
    name: string;
    input: Record<string, unknown>;
  };
  tool_id?: string;
  tool_name?: string;
  usage?: ClaudeUsage;
}

/**
 * User tool result event
 */
export interface ClaudeToolResultEvent extends ClaudeBaseEvent {
  type: "user";
  subtype: "tool_result";
  content: {
    tool_use_id: string;
    content: string;
    is_error?: boolean;
  };
  tool_id?: string;
}

/**
 * Connection event
 */
export interface ClaudeConnectedEvent extends ClaudeBaseEvent {
  type: "connected";
  cwd: string;
}

/**
 * Done event
 */
export interface ClaudeDoneEvent extends ClaudeBaseEvent {
  type: "done";
}

/**
 * Error event
 */
export interface ClaudeErrorEvent extends ClaudeBaseEvent {
  type: "error";
  content: string;
}

/**
 * Cancelled event
 */
export interface ClaudeCancelledEvent extends ClaudeBaseEvent {
  type: "cancelled";
  note?: string;
}

/**
 * Session reset event
 */
export interface ClaudeSessionResetEvent extends ClaudeBaseEvent {
  type: "session_reset";
}

/**
 * Status event
 */
export interface ClaudeStatusEvent extends ClaudeBaseEvent {
  type: "status";
  session_info: {
    session_id: string | null;
    model: string | null;
    tools: string[];
    mcp_servers: Array<{ name: string; status: string }>;
  };
  running: boolean;
  continue_session: boolean;
}

/**
 * Union type of all Claude events
 */
export type ClaudeEvent =
  | ClaudeSystemInitEvent
  | ClaudeTextEvent
  | ClaudeToolUseEvent
  | ClaudeToolResultEvent
  | ClaudeConnectedEvent
  | ClaudeDoneEvent
  | ClaudeErrorEvent
  | ClaudeCancelledEvent
  | ClaudeSessionResetEvent
  | ClaudeStatusEvent;

// ============================================================================
// Supporting Types
// ============================================================================

/**
 * Token usage information
 */
export interface ClaudeUsage {
  input_tokens?: number;
  output_tokens?: number;
  cache_creation_input_tokens?: number;
  cache_read_input_tokens?: number;
}

/**
 * Message for UI rendering
 */
export interface ClaudeMessage {
  id: string;
  type: "text" | "tool_use" | "tool_result" | "error" | "system";
  content: string | Record<string, unknown>;
  timestamp: Date;
  toolName?: string;
  toolId?: string;
  isError?: boolean;
  usage?: ClaudeUsage;
}

/**
 * Tool call tracking
 */
export interface ToolCall {
  id: string;
  name: string;
  input: Record<string, unknown>;
  startTime: Date;
  endTime?: Date;
  result?: string;
  isError?: boolean;
  status: "running" | "completed" | "failed";
}

/**
 * Session information
 */
export interface ClaudeSessionInfo {
  sessionId: string | null;
  model: string | null;
  tools: string[];
  mcpServers: Array<{ name: string; status: string }>;
}

// ============================================================================
// WebSocket Commands
// ============================================================================

/**
 * Commands to send to the agent WebSocket
 */
export interface AgentCommand {
  command: "run" | "cancel" | "new_session" | "status";
  prompt?: string;
  continue?: boolean;
}

// ============================================================================
// Helpers
// ============================================================================

/**
 * Type guard for system init event
 */
export function isSystemInitEvent(
  event: ClaudeEvent
): event is ClaudeSystemInitEvent {
  return event.type === "system" && event.subtype === "init";
}

/**
 * Type guard for text event
 */
export function isTextEvent(event: ClaudeEvent): event is ClaudeTextEvent {
  return event.type === "assistant" && event.subtype === "text";
}

/**
 * Type guard for tool use event
 */
export function isToolUseEvent(
  event: ClaudeEvent
): event is ClaudeToolUseEvent {
  return event.type === "assistant" && event.subtype === "tool_use";
}

/**
 * Type guard for tool result event
 */
export function isToolResultEvent(
  event: ClaudeEvent
): event is ClaudeToolResultEvent {
  return event.type === "user" && event.subtype === "tool_result";
}

/**
 * Type guard for done event
 */
export function isDoneEvent(event: ClaudeEvent): event is ClaudeDoneEvent {
  return event.type === "done";
}

/**
 * Type guard for error event
 */
export function isErrorEvent(event: ClaudeEvent): event is ClaudeErrorEvent {
  return event.type === "error";
}

/**
 * Tool icons by name
 */
export const TOOL_ICONS: Record<string, string> = {
  Read: "📖",
  Write: "✏️",
  Edit: "📝",
  Bash: "💻",
  Glob: "🔍",
  Grep: "🔎",
  Task: "📋",
  TodoWrite: "✅",
  WebFetch: "🌐",
  WebSearch: "🔍",
  NotebookEdit: "📓",
  // MCP tools
  mcp__playwright__browser_navigate: "🌐",
  mcp__playwright__browser_click: "🖱️",
  mcp__playwright__browser_snapshot: "📸",
  mcp__context7__resolve_library_id: "📚",
  mcp__context7__get_library_docs: "📖",
  mcp__sequential_thinking__sequentialthinking: "🧠",
};

/**
 * Get icon for a tool
 */
export function getToolIcon(toolName: string): string {
  // Check exact match
  if (TOOL_ICONS[toolName]) {
    return TOOL_ICONS[toolName];
  }

  // Check prefix match for MCP tools
  if (toolName.startsWith("mcp__playwright")) return "🎭";
  if (toolName.startsWith("mcp__context7")) return "📚";
  if (toolName.startsWith("mcp__sequential")) return "🧠";
  if (toolName.startsWith("mcp__magic")) return "✨";
  if (toolName.startsWith("mcp__chrome")) return "🔧";

  // Default
  return "🔧";
}

/**
 * Format tool input for display
 */
export function formatToolInput(
  input: Record<string, unknown>,
  maxLength = 100
): string {
  const str = JSON.stringify(input, null, 2);
  if (str.length <= maxLength) return str;
  return str.substring(0, maxLength) + "...";
}

/**
 * Generate unique message ID
 */
export function generateMessageId(): string {
  return `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}
