// TypeScript types for the Knowledge Agent UI

export type MessageRole = 'user' | 'agent' | 'system';
export type MessageStatus = 'sending' | 'thinking' | 'done' | 'error';

export interface ToolInfo {
  name: string;
  description: string | null;
  parameters?: Record<string, unknown>;
}

export interface StructuredResponse {
  ticket_summary: string;
  what_we_know: string;
  similar_historical_tickets: string;
  previous_resolution: string;
  recommended_investigation: string;
  missing_information: string;
  sources: string[];
}

export interface AgentQueryResponse {
  success: boolean;
  error_code: string | null;
  error: string | null;
  structured_response: StructuredResponse | null;
  timestamp: string;
  processing_ms: number;
  request_id: string;
}

export interface ChatMessage {
  id: string;
  role: MessageRole;
  status: MessageStatus;
  content: string;
  response?: AgentQueryResponse;
  timestamp: Date;
}

export interface HealthStatus {
  status: 'healthy' | 'degraded' | 'unknown';
  mcp_connected: boolean;
  available_tools: string[];
  llm: {
    provider: string;
    model: string;
    configured: boolean;
  };
  version: string;
}
