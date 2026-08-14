/** Same-origin REST and resilient WebSocket services. */

import type { AgentQueryResponse, HealthStatus, ToolInfo } from '../types'

export type WSMessageType = 'response' | 'thinking' | 'error' | 'pong'
export type ConnectionState = 'connecting' | 'connected' | 'reconnecting' | 'disconnected'

export interface WSMessage {
  type: WSMessageType
  payload: Record<string, unknown>
}

export type MessageHandler = (message: WSMessage) => void
export type ConnectionHandler = (state: ConnectionState) => void

export class AgentWebSocketService {
  private ws: WebSocket | null = null
  private messageHandlers = new Set<MessageHandler>()
  private connectionHandlers = new Set<ConnectionHandler>()
  private reconnectAttempts = 0
  private readonly maxReconnectAttempts = 5
  private readonly reconnectDelayMs = 1000
  private readonly connectTimeoutMs = 10_000
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private connectPromise: Promise<void> | null = null
  private manuallyClosed = false
  private state: ConnectionState = 'disconnected'

  constructor(private readonly url: string) {}

  connect(): Promise<void> {
    this.manuallyClosed = false
    if (this.isConnected) return Promise.resolve()
    if (this.connectPromise) return this.connectPromise

    const pendingConnection = this.openSocket(false)
    this.connectPromise = pendingConnection
    void pendingConnection.then(
      () => {
        if (this.connectPromise === pendingConnection) this.connectPromise = null
      },
      () => {
        if (this.connectPromise === pendingConnection) this.connectPromise = null
      },
    )
    return pendingConnection
  }

  private openSocket(reconnecting: boolean): Promise<void> {
    this.setConnectionState(reconnecting ? 'reconnecting' : 'connecting')
    return new Promise((resolve, reject) => {
      let settled = false
      const socket = new WebSocket(this.url)
      this.ws = socket
      const timeout = setTimeout(() => {
        if (!settled) {
          settled = true
          socket.close()
          reject(new Error('Knowledge service connection timed out.'))
        }
      }, this.connectTimeoutMs)

      socket.onopen = () => {
        clearTimeout(timeout)
        if (this.ws !== socket) {
          socket.close()
          return
        }
        settled = true
        this.reconnectAttempts = 0
        this.setConnectionState('connected')
        resolve()
      }

      socket.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data as string) as WSMessage
          this.messageHandlers.forEach((handler) => handler(message))
        } catch {
          // Ignore malformed server frames; the request timeout recovers pending UI state.
        }
      }

      socket.onerror = () => {
        if (!settled) {
          settled = true
          clearTimeout(timeout)
          reject(new Error('Unable to connect to the knowledge service.'))
          socket.close()
        }
      }

      socket.onclose = () => {
        clearTimeout(timeout)
        const isCurrentSocket = this.ws === socket
        if (isCurrentSocket) {
          this.ws = null
          this.setConnectionState('disconnected')
        }
        if (!settled) {
          settled = true
          reject(new Error('Unable to connect to the knowledge service.'))
        }
        if (isCurrentSocket) this.scheduleReconnect()
      }
    })
  }

  private scheduleReconnect(): void {
    if (this.manuallyClosed || this.reconnectTimer || this.reconnectAttempts >= this.maxReconnectAttempts) {
      return
    }
    const delay = this.reconnectDelayMs * 2 ** this.reconnectAttempts
    this.reconnectAttempts += 1
    this.setConnectionState('reconnecting')
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null
      this.openSocket(true).catch(() => undefined)
    }, delay)
  }

  disconnect(): void {
    this.manuallyClosed = true
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
    const socket = this.ws
    this.ws = null
    this.connectPromise = null
    if (socket) {
      socket.close()
    }
    this.setConnectionState('disconnected')
  }

  sendQuery(query: string, requestId: string, sessionId?: string): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      throw new Error('WebSocket not connected')
    }
    this.ws.send(
      JSON.stringify({
        type: 'query',
        payload: { query, request_id: requestId, session_id: sessionId },
      }),
    )
  }

  ping(requestId: string): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: 'ping', payload: { request_id: requestId } }))
    }
  }

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN
  }

  addHandler(handler: MessageHandler): () => void {
    this.messageHandlers.add(handler)
    return () => this.messageHandlers.delete(handler)
  }

  addConnectionHandler(handler: ConnectionHandler): () => void {
    this.connectionHandlers.add(handler)
    handler(this.state)
    return () => this.connectionHandlers.delete(handler)
  }

  private setConnectionState(state: ConnectionState): void {
    if (this.state === state) return
    this.state = state
    this.connectionHandlers.forEach((handler) => handler(state))
  }
}

export class AgentRestService {
  constructor(
    private readonly baseUrl: string,
    private readonly timeoutMs = 100_000,
  ) {}

  async health(): Promise<HealthStatus> {
    return this.request<HealthStatus>(`${this.baseUrl}/health`)
  }

  async listTools(): Promise<{ tools: ToolInfo[]; count: number }> {
    return this.request(`${this.baseUrl}/tools`)
  }

  async query(query: string, requestId: string): Promise<AgentQueryResponse> {
    const response = await this.request<AgentQueryResponse>(`${this.baseUrl}/query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Request-ID': requestId },
      body: JSON.stringify({ query }),
    }, true)
    if (!isAgentQueryResponse(response)) {
      throw new Error('The knowledge service returned an invalid response.')
    }
    return response
  }

  private async request<T>(url: string, init?: RequestInit, acceptErrorBody = false): Promise<T> {
    const controller = new AbortController()
    const timeout = setTimeout(() => controller.abort(), this.timeoutMs)
    try {
      const response = await fetch(url, { ...init, signal: controller.signal })
      let body: unknown
      try {
        body = await response.json()
      } catch {
        throw new Error('The knowledge service returned an invalid response.')
      }
      if (!response.ok && !acceptErrorBody) {
        throw new Error('The knowledge service is temporarily unavailable.')
      }
      return body as T
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') {
        throw new Error('The knowledge service request timed out.')
      }
      throw error
    } finally {
      clearTimeout(timeout)
    }
  }
}

export function isAgentQueryResponse(value: unknown): value is AgentQueryResponse {
  if (!value || typeof value !== 'object') return false
  const candidate = value as Partial<AgentQueryResponse>
  if (
    typeof candidate.success !== 'boolean'
    || typeof candidate.timestamp !== 'string'
    || typeof candidate.processing_ms !== 'number'
    || typeof candidate.request_id !== 'string'
  ) {
    return false
  }
  if (!candidate.success) {
    return typeof candidate.error === 'string'
  }
  const structured = candidate.structured_response
  return Boolean(
    structured
    && typeof structured.ticket_summary === 'string'
    && typeof structured.what_we_know === 'string'
    && typeof structured.similar_historical_tickets === 'string'
    && typeof structured.previous_resolution === 'string'
    && typeof structured.recommended_investigation === 'string'
    && typeof structured.missing_information === 'string'
    && Array.isArray(structured.sources)
    && structured.sources.every((source) => typeof source === 'string'),
  )
}
