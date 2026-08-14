/** Zustand store for chat state, transport fallback, and lifecycle cleanup. */

import { create } from 'zustand'
import type { AgentQueryResponse, ChatMessage, HealthStatus } from '../types'
import {
  AgentRestService,
  AgentWebSocketService,
  isAgentQueryResponse,
  type ConnectionState,
  type WSMessage,
} from '../services/agentService'

const API_BASE = '/api'
const WS_URL = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws`
const QUERY_TIMEOUT_MS = 95_000

interface ChatStore {
  messages: ChatMessage[]
  health: HealthStatus | null
  wsConnected: boolean
  connectionState: ConnectionState
  isThinking: boolean
  wsService: AgentWebSocketService
  restService: AgentRestService
  initialize: () => Promise<void>
  shutdown: () => void
  sendMessage: (query: string) => Promise<void>
  clearMessages: () => void
  addExampleQuery: (query: string) => void
}

interface PendingQuery {
  requestId: string
  query: string
  thinkingMessageId: string
  timeout: ReturnType<typeof setTimeout>
  fallbackStarted: boolean
}

const wsService = new AgentWebSocketService(WS_URL)
const restService = new AgentRestService(API_BASE)

let messageCounter = 0
let initialized = false
let lifecycleGeneration = 0
let pingInterval: ReturnType<typeof setInterval> | null = null
let healthInterval: ReturnType<typeof setInterval> | null = null
let removeMessageHandler: (() => void) | null = null
let removeConnectionHandler: (() => void) | null = null
let pendingQuery: PendingQuery | null = null

const nextMessageId = () => `msg-${++messageCounter}-${Date.now()}`
const nextRequestId = () => {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return `request-${Date.now()}-${++messageCounter}`
}

const unknownHealth = (): HealthStatus => ({
  status: 'unknown',
  mcp_connected: false,
  available_tools: [],
  llm: { provider: 'unknown', model: 'unknown', configured: false },
  version: '?',
})

function clearPendingQuery(): PendingQuery | null {
  const pending = pendingQuery
  if (pending) clearTimeout(pending.timeout)
  pendingQuery = null
  return pending
}

function finishWithResponse(response: AgentQueryResponse, requestId: string): void {
  if (!pendingQuery || pendingQuery.requestId !== requestId) return
  const pending = clearPendingQuery()
  if (!pending) return
  useChatStore.setState((state) => ({
    messages: state.messages.map((message) =>
      message.id === pending.thinkingMessageId
        ? {
            id: nextMessageId(),
            role: 'agent',
            status: 'done',
            content: '',
            response,
            timestamp: new Date(),
          }
        : message,
    ),
    isThinking: false,
  }))
}

function finishWithError(message: string, requestId?: string): void {
  if (!pendingQuery || (requestId && pendingQuery.requestId !== requestId)) return
  const pending = clearPendingQuery()
  if (!pending) return
  useChatStore.setState((state) => ({
    messages: state.messages.map((item) =>
      item.id === pending.thinkingMessageId
        ? {
            id: nextMessageId(),
            role: 'agent',
            status: 'error',
            content: message,
            timestamp: new Date(),
          }
        : item,
    ),
    isThinking: false,
  }))
}

async function fallbackPendingToRest(): Promise<void> {
  const pending = pendingQuery
  if (!pending || pending.fallbackStarted) return
  pending.fallbackStarted = true
  clearTimeout(pending.timeout)
  try {
    const response = await restService.query(pending.query, pending.requestId)
    finishWithResponse(response, pending.requestId)
  } catch {
    finishWithError('Unable to connect to the knowledge service. Please try again.', pending.requestId)
  }
}

function handleWebSocketMessage(message: WSMessage): void {
  const requestId = typeof message.payload.request_id === 'string'
    ? message.payload.request_id
    : undefined

  if (message.type === 'thinking') {
    if (pendingQuery && (!requestId || pendingQuery.requestId === requestId)) {
      useChatStore.setState({ isThinking: true })
    }
    return
  }
  if (message.type === 'response' && requestId) {
    if (!isAgentQueryResponse(message.payload)) {
      finishWithError('The knowledge service returned an invalid response.', requestId)
      return
    }
    finishWithResponse(message.payload, requestId)
    return
  }
  if (message.type === 'error') {
    const errorMessage = typeof message.payload.message === 'string'
      ? message.payload.message
      : 'The Knowledge Agent could not complete the request.'
    finishWithError(errorMessage, requestId)
  }
}

async function refreshHealth(generation: number): Promise<void> {
  try {
    const health = await restService.health()
    if (initialized && generation === lifecycleGeneration) {
      useChatStore.setState({ health })
    }
  } catch {
    if (initialized && generation === lifecycleGeneration) {
      useChatStore.setState({ health: unknownHealth() })
    }
  }
}

export const useChatStore = create<ChatStore>((set, get) => ({
  messages: [],
  health: null,
  wsConnected: false,
  connectionState: 'disconnected',
  isThinking: false,
  wsService,
  restService,

  initialize: async () => {
    if (initialized) return
    initialized = true
    const generation = ++lifecycleGeneration

    removeMessageHandler = wsService.addHandler(handleWebSocketMessage)
    removeConnectionHandler = wsService.addConnectionHandler((connectionState) => {
      if (!initialized || generation !== lifecycleGeneration) return
      set({ connectionState, wsConnected: connectionState === 'connected' })
      if (connectionState === 'disconnected' && pendingQuery) {
        void fallbackPendingToRest()
      }
    })

    await Promise.allSettled([refreshHealth(generation), wsService.connect()])
    if (!initialized || generation !== lifecycleGeneration) return

    pingInterval = setInterval(() => {
      if (wsService.isConnected) wsService.ping(nextRequestId())
    }, 30_000)
    healthInterval = setInterval(() => {
      void refreshHealth(generation)
    }, 60_000)
  },

  shutdown: () => {
    initialized = false
    lifecycleGeneration += 1
    if (pingInterval) clearInterval(pingInterval)
    if (healthInterval) clearInterval(healthInterval)
    pingInterval = null
    healthInterval = null
    removeMessageHandler?.()
    removeConnectionHandler?.()
    removeMessageHandler = null
    removeConnectionHandler = null
    clearPendingQuery()
    wsService.disconnect()
    set({ wsConnected: false, connectionState: 'disconnected', isThinking: false })
  },

  sendMessage: async (rawQuery: string) => {
    const query = rawQuery.trim()
    if (!query || get().isThinking) return

    const requestId = nextRequestId()
    const thinkingMessageId = nextMessageId()
    const userMessage: ChatMessage = {
      id: nextMessageId(),
      role: 'user',
      status: 'done',
      content: query,
      timestamp: new Date(),
    }
    const thinkingMessage: ChatMessage = {
      id: thinkingMessageId,
      role: 'agent',
      status: 'thinking',
      content: '',
      timestamp: new Date(),
    }

    set((state) => ({
      messages: [...state.messages, userMessage, thinkingMessage],
      isThinking: true,
    }))

    const timeout = setTimeout(() => {
      void fallbackPendingToRest()
    }, QUERY_TIMEOUT_MS)
    pendingQuery = {
      requestId,
      query,
      thinkingMessageId,
      timeout,
      fallbackStarted: false,
    }

    if (wsService.isConnected) {
      try {
        wsService.sendQuery(query, requestId)
        return
      } catch {
        await fallbackPendingToRest()
        return
      }
    }
    await fallbackPendingToRest()
  },

  clearMessages: () => {
    clearPendingQuery()
    set({ messages: [], isThinking: false })
  },

  addExampleQuery: (query: string) => {
    void get().sendMessage(query)
  },
}))
