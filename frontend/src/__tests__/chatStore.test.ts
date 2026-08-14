import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { AgentQueryResponse } from '../types'

type TestConnectionState = 'connecting' | 'connected' | 'reconnecting' | 'disconnected'

const serviceMocks = vi.hoisted(() => ({
  wsConnected: false,
  connect: vi.fn(),
  sendQuery: vi.fn(),
  ping: vi.fn(),
  addHandler: vi.fn((_handler: (message: unknown) => void) => vi.fn()),
  addConnectionHandler: vi.fn(
    (_handler: (state: TestConnectionState) => void) => vi.fn(),
  ),
  disconnect: vi.fn(),
  query: vi.fn(),
  health: vi.fn(),
  listTools: vi.fn(),
}))

vi.mock('../services/agentService', () => ({
  isAgentQueryResponse: (value: unknown) => (
    typeof value === 'object'
    && value !== null
    && typeof (value as { success?: unknown }).success === 'boolean'
  ),
  AgentWebSocketService: class {
    get isConnected() {
      return serviceMocks.wsConnected
    }

    connect = serviceMocks.connect
    sendQuery = serviceMocks.sendQuery
    ping = serviceMocks.ping
    addHandler = serviceMocks.addHandler
    addConnectionHandler = serviceMocks.addConnectionHandler
    disconnect = serviceMocks.disconnect
  },
  AgentRestService: class {
    query = serviceMocks.query
    health = serviceMocks.health
    listTools = serviceMocks.listTools
  },
}))

import { useChatStore } from '../store/chatStore'

let connectionHandler: ((state: TestConnectionState) => void) | null = null

const restResponse: AgentQueryResponse = {
  success: true,
  error_code: null,
  error: null,
  structured_response: {
    ticket_summary: 'PROJ-1002 summary',
    what_we_know: 'Known facts',
    similar_historical_tickets: 'PROJ-908',
    previous_resolution: 'Historical resolution',
    recommended_investigation: 'Investigation steps',
    missing_information: 'Missing metrics',
    sources: ['PROJ-1002', 'PROJ-908'],
  },
  timestamp: '2026-08-13T12:00:00Z',
  processing_ms: 100,
  request_id: 'request-rest-fallback',
}

describe('chatStore REST fallback', () => {
  beforeEach(() => {
    useChatStore.getState().shutdown()
    serviceMocks.wsConnected = false
    connectionHandler = null
    serviceMocks.connect.mockReset().mockResolvedValue(undefined)
    serviceMocks.sendQuery.mockReset()
    serviceMocks.query.mockReset()
    serviceMocks.query.mockResolvedValue(restResponse)
    serviceMocks.health.mockReset().mockResolvedValue({
      status: 'healthy',
      mcp_connected: true,
      available_tools: ['get_ticket', 'search_tickets', 'find_similar_tickets'],
      llm: { provider: 'gemini', model: 'gemini-3.5-flash', configured: true },
      version: '0.1.0',
    })
    serviceMocks.addConnectionHandler.mockReset().mockImplementation(
      (handler: (state: TestConnectionState) => void) => {
        connectionHandler = handler
        return vi.fn()
      },
    )
    serviceMocks.addHandler.mockReset().mockReturnValue(vi.fn())
    useChatStore.setState({
      messages: [],
      isThinking: false,
      wsConnected: false,
      connectionState: 'disconnected',
    })
  })

  afterEach(() => {
    useChatStore.getState().shutdown()
  })

  it('uses REST and stores the structured response when WebSocket is unavailable', async () => {
    await useChatStore.getState().sendMessage('Help me understand PROJ-1002')

    expect(serviceMocks.sendQuery).not.toHaveBeenCalled()
    expect(serviceMocks.query).toHaveBeenCalledOnce()
    expect(serviceMocks.query.mock.calls[0][0]).toBe('Help me understand PROJ-1002')
    expect(typeof serviceMocks.query.mock.calls[0][1]).toBe('string')

    const state = useChatStore.getState()
    expect(state.isThinking).toBe(false)
    expect(state.messages).toHaveLength(2)
    expect(state.messages[0]).toMatchObject({
      role: 'user',
      status: 'done',
      content: 'Help me understand PROJ-1002',
    })
    expect(state.messages[1]).toMatchObject({
      role: 'agent',
      status: 'done',
      response: restResponse,
    })
  })

  it('recovers after a failed request and accepts a repeated query', async () => {
    serviceMocks.query
      .mockRejectedValueOnce(new Error('provider internals'))
      .mockResolvedValueOnce(restResponse)

    await useChatStore.getState().sendMessage('Help me understand PROJ-9999')
    expect(useChatStore.getState().messages[1]).toMatchObject({
      role: 'agent',
      status: 'error',
      content: 'Unable to connect to the knowledge service. Please try again.',
    })
    expect(useChatStore.getState().isThinking).toBe(false)

    await useChatStore.getState().sendMessage('Help me understand PROJ-1002')
    const state = useChatStore.getState()
    expect(state.isThinking).toBe(false)
    expect(state.messages).toHaveLength(4)
    expect(state.messages[3]).toMatchObject({ status: 'done', response: restResponse })
  })

  it('falls back to REST when an active WebSocket disconnects mid-query', async () => {
    serviceMocks.wsConnected = true
    await useChatStore.getState().initialize()
    expect(connectionHandler).not.toBeNull()
    connectionHandler!('connected')

    await useChatStore.getState().sendMessage('Get PROJ-1002')
    expect(serviceMocks.sendQuery).toHaveBeenCalledOnce()
    expect(useChatStore.getState().isThinking).toBe(true)

    serviceMocks.wsConnected = false
    connectionHandler!('disconnected')
    await vi.waitFor(() => expect(serviceMocks.query).toHaveBeenCalledOnce())
    await vi.waitFor(() => expect(useChatStore.getState().isThinking).toBe(false))
  })

  it('recovers a stuck WebSocket query through the bounded REST fallback', async () => {
    vi.useFakeTimers()
    try {
      serviceMocks.wsConnected = true
      await useChatStore.getState().initialize()
      connectionHandler!('connected')

      await useChatStore.getState().sendMessage('Get PROJ-1002')
      expect(useChatStore.getState().isThinking).toBe(true)

      await vi.advanceTimersByTimeAsync(95_000)
      await Promise.resolve()

      expect(serviceMocks.query).toHaveBeenCalledOnce()
      expect(useChatStore.getState().isThinking).toBe(false)
    } finally {
      vi.useRealTimers()
    }
  })
})
