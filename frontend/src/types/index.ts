// TypeScript types for the Knowledge Agent UI

export type IntentType =
  | 'greeting'
  | 'get_ticket'
  | 'search_tickets'
  | 'get_project'
  | 'get_time'
  | 'list_tools'
  | 'unknown';

export type MessageRole = 'user' | 'agent' | 'system';
export type MessageStatus = 'sending' | 'thinking' | 'done' | 'error';

export interface AgentUser {
  account_id: string;
  display_name: string;
  email: string;
  avatar_url?: string;
}

export interface TicketStatus {
  name: string;
  category: 'new' | 'indeterminate' | 'done';
  color: string;
}

export interface Ticket {
  id: string;
  key: string;
  summary: string;
  description: string;
  status: TicketStatus;
  priority: { name: string; icon: string };
  issue_type: { name: string; icon: string };
  project: { key: string; name: string };
  assignee: AgentUser | null;
  reporter: AgentUser;
  labels: string[];
  components: string[];
  story_points: number | null;
  sprint: { name: string; state: string } | null;
  created: string;
  updated: string;
  due_date: string | null;
  comments: TicketComment[];
  linked_issues: LinkedIssue[];
}

export interface TicketComment {
  author: AgentUser;
  body: string;
  created: string;
}

export interface LinkedIssue {
  type: string;
  key: string;
  summary: string;
}

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
  error: string | null;
  structured_response: StructuredResponse | null;
  timestamp: string;
  processing_ms: number;
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
  version: string;
}
