/**
 * Shared TypeScript types — mirrors backend Pydantic models.
 *
 * CONTRACT: Changes here must be coordinated with backend/app/models.py.
 */

// ---------------------------------------------------------------------------
// Request types
// ---------------------------------------------------------------------------

export interface ChatRequest {
  message: string;
  session_id?: string;
  context?: Record<string, unknown>;
}

export interface SessionCreate {
  title?: string;
}

// ---------------------------------------------------------------------------
// Response types
// ---------------------------------------------------------------------------

export interface SessionResponse {
  id: string;
  title: string;
  created_at: string;
  message_count: number;
}

export interface HealthResponse {
  status: "ok" | "degraded";
  version: string;
  anthropic_configured: boolean;
}

// ---------------------------------------------------------------------------
// SSE event data shapes
// ---------------------------------------------------------------------------

export interface ThinkingEventData {
  text: string;
}

export interface ErrorEventData {
  message: string;
  recoverable: boolean;
}

export interface TokenUsage {
  input: number;
  output: number;
}

export interface DoneEventData {
  tokens_used: TokenUsage;
  agents_used: string[];
}

export interface AgentActivityData {
  agent: string;
  status: "running" | "completed";
  task: string;
  thinking?: string;
}

export interface CitationData {
  type: "slack" | "linear" | "web";
  url: string;
  title: string;
  snippet: string;
}

export interface ToolCallData {
  tool: string;
  params: Record<string, unknown>;
}

// ---------------------------------------------------------------------------
// UI state types
// ---------------------------------------------------------------------------

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations: CitationData[];
  toolCalls?: ToolCallData[];
  isStreaming?: boolean;
}

export type SSEEventType =
  | "thinking"
  | "text"
  | "agent_activity"
  | "tool_call"
  | "citation"
  | "error"
  | "done";
