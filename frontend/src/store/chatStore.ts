/**
 * Zustand store for global chat and agent state.
 */

import { create } from 'zustand'
import type { ChatMessage, HealthStatus } from '../types'
import { AgentWebSocketService, AgentRestService } from '../services/agentService'

const API_BASE = '/api'
const WS_URL = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws`

interface ChatStore {
  // State
  messages: ChatMessage[]
  health: HealthStatus | null
  wsConnected: boolean
  isThinking: boolean

  // Services (singletons)
  wsService: AgentWebSocketService
  restService: AgentRestService

  // Actions
  initialize: () => Promise<void>
  sendMessage: (query: string) => Promise<void>
  clearMessages: () => void
  addExampleQuery: (query: string) => void
}

const wsService = new AgentWebSocketService(WS_URL)
const restService = new AgentRestService(API_BASE)

let msgIdCounter = 0
const nextId = () => `msg-${++msgIdCounter}-${Date.now()}`

export const useChatStore = create<ChatStore>((set, get) => ({
  messages: [],
  health: null,
  wsConnected: false,
  isThinking: false,
  wsService,
  restService,

  initialize: async () => {
    // Fetch health
    try {
      const health = await restService.health()
      set({ health })
    } catch {
      set({ health: { status: 'unknown', mcp_connected: false, available_tools: [], version: '?' } })
    }

    // Connect WebSocket
    try {
      await wsService.connect()
      set({ wsConnected: true })

      wsService.addHandler((msg) => {
        if (msg.type === 'thinking') {
          set({ isThinking: true })
        } else if (msg.type === 'response') {
          const payload = msg.payload as Record<string, unknown>
          set((state) => {
            // Replace the last "thinking" message with the real response
            const messages = state.messages.filter((m) => m.status !== 'thinking')
            const agentMessage: ChatMessage = {
              id: nextId(),
              role: 'agent',
              status: 'done',
              content: '',
              response: payload as unknown as ChatMessage['response'],
              timestamp: new Date(),
            }
            return { messages: [...messages, agentMessage], isThinking: false }
          })
        } else if (msg.type === 'error') {
          const payload = msg.payload as { message?: string }
          set((state) => {
            const messages = state.messages.filter((m) => m.status !== 'thinking')
            return {
              messages: [
                ...messages,
                {
                  id: nextId(),
                  role: 'agent',
                  status: 'error',
                  content: payload.message ?? 'An error occurred',
                  timestamp: new Date(),
                },
              ],
              isThinking: false,
            }
          })
        }
      })
    } catch {
      set({ wsConnected: false })
    }

    // Ping every 30s to keep connection alive
    setInterval(() => {
      if (wsService.isConnected) wsService.ping()
    }, 30_000)
  },

  sendMessage: async (query: string) => {
    const userMsg: ChatMessage = {
      id: nextId(),
      role: 'user',
      status: 'done',
      content: query,
      timestamp: new Date(),
    }

    const thinkingMsg: ChatMessage = {
      id: nextId(),
      role: 'agent',
      status: 'thinking',
      content: '',
      timestamp: new Date(),
    }

    set((state) => ({
      messages: [...state.messages, userMsg, thinkingMsg],
      isThinking: true,
    }))

    try {
      if (wsService.isConnected) {
        wsService.sendQuery(query)
      } else {
        // Fallback to REST
        const result = await restService.query(query)
        set((state) => {
          const messages = state.messages.filter((m) => m.status !== 'thinking')
          return {
            messages: [
              ...messages,
              {
                id: nextId(),
                role: 'agent',
                status: 'done',
                content: '',
                response: result,
                timestamp: new Date(),
              },
            ],
            isThinking: false,
          }
        })
      }
    } catch (err) {
      set((state) => {
        const messages = state.messages.filter((m) => m.status !== 'thinking')
        return {
          messages: [
            ...messages,
            {
              id: nextId(),
              role: 'agent',
              status: 'error',
              content: err instanceof Error ? err.message : 'Failed to send query',
              timestamp: new Date(),
            },
          ],
          isThinking: false,
        }
      })
    }
  },

  clearMessages: () => set({ messages: [] }),

  addExampleQuery: (query: string) => {
    get().sendMessage(query)
  },
}))
