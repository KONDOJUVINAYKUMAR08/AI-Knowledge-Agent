/**
 * WebSocket service for real-time agent communication.
 * Manages connection lifecycle and message routing.
 */

import type { AgentQueryResponse } from '../types'

export type WSMessageType = 'response' | 'thinking' | 'error' | 'pong'

export interface WSMessage {
  type: WSMessageType
  payload: Record<string, unknown>
}

export type MessageHandler = (msg: WSMessage) => void

export class AgentWebSocketService {
  private ws: WebSocket | null = null
  private handlers: Set<MessageHandler> = new Set()
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectDelay = 1000
  private url: string

  constructor(url: string) {
    this.url = url
  }

  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        this.ws = new WebSocket(this.url)

        this.ws.onopen = () => {
          this.reconnectAttempts = 0
          resolve()
        }

        this.ws.onerror = (err) => {
          reject(err)
        }

        this.ws.onmessage = (event) => {
          try {
            const msg: WSMessage = JSON.parse(event.data as string)
            this.handlers.forEach((h) => h(msg))
          } catch {
            console.error('[WS] Failed to parse message:', event.data)
          }
        }

        this.ws.onclose = () => {
          if (this.reconnectAttempts < this.maxReconnectAttempts) {
            setTimeout(() => {
              this.reconnectAttempts++
              this.connect().catch(console.error)
            }, this.reconnectDelay * Math.pow(2, this.reconnectAttempts))
          }
        }
      } catch (err) {
        reject(err)
      }
    })
  }

  disconnect(): void {
    if (this.ws) {
      this.ws.onclose = null // Prevent reconnect
      this.ws.close()
      this.ws = null
    }
  }

  sendQuery(query: string, sessionId?: string): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      throw new Error('WebSocket not connected')
    }
    this.ws.send(
      JSON.stringify({
        type: 'query',
        payload: { query, session_id: sessionId },
      }),
    )
  }

  ping(): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: 'ping', payload: {} }))
    }
  }

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN
  }

  addHandler(handler: MessageHandler): () => void {
    this.handlers.add(handler)
    return () => this.handlers.delete(handler)
  }
}

/**
 * REST API service for non-streaming operations.
 */
export class AgentRestService {
  private baseUrl: string

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl
  }

  async health() {
    const res = await fetch(`${this.baseUrl}/health`)
    if (!res.ok) throw new Error(`Health check failed: ${res.status}`)
    return res.json()
  }

  async listTools() {
    const res = await fetch(`${this.baseUrl}/tools`)
    if (!res.ok) throw new Error(`Failed to fetch tools: ${res.status}`)
    return res.json()
  }

  async query(query: string): Promise<AgentQueryResponse> {
    const res = await fetch(`${this.baseUrl}/query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query }),
    })
    if (!res.ok) throw new Error(`Query failed: ${res.status}`)
    return res.json()
  }
}
