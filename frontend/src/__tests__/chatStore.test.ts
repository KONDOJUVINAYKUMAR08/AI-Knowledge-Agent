import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { AgentQueryResponse } from '../types'

const serviceMocks = vi.hoisted(() => ({
  wsConnected: false,
  connect: vi.fn(),
  sendQuery: vi.fn(),
  ping: vi.fn(),
  addHandler: vi.fn(() => vi.fn()),
  query: vi.fn(),
  health: vi.fn(),
  listTools: vi.fn(),
}))

vi.mock('../services/agentService', () => ({
  AgentWebSocketService: class {
    get isConnected() {
      return serviceMocks.wsConnected
    }

    connect = serviceMocks.connect
    sendQuery = serviceMocks.sendQuery
    ping = serviceMocks.ping
    addHandler = serviceMocks.addHandler
  },
  AgentRestService: class {
    query = serviceMocks.query
    health = serviceMocks.health
    listTools = serviceMocks.listTools
  },
}))

import { useChatStore } from '../store/chatStore'

const restResponse: AgentQueryResponse = {
  success: true,
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
}

describe('chatStore REST fallback', () => {
  beforeEach(() => {
    serviceMocks.wsConnected = false
    serviceMocks.sendQuery.mockReset()
    serviceMocks.query.mockReset()
    serviceMocks.query.mockResolvedValue(restResponse)
    useChatStore.setState({
      messages: [],
      isThinking: false,
      wsConnected: false,
    })
  })

  it('uses REST and stores the structured response when WebSocket is unavailable', async () => {
    await useChatStore.getState().sendMessage('Help me understand PROJ-1002')

    expect(serviceMocks.sendQuery).not.toHaveBeenCalled()
    expect(serviceMocks.query).toHaveBeenCalledOnce()
    expect(serviceMocks.query).toHaveBeenCalledWith('Help me understand PROJ-1002')

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
})
