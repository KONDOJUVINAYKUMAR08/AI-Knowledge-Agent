import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { AgentWebSocketService, type ConnectionState } from '../services/agentService'

class FakeWebSocket {
  static readonly CONNECTING = 0
  static readonly OPEN = 1
  static readonly CLOSED = 3
  static instances: FakeWebSocket[] = []

  readyState = FakeWebSocket.CONNECTING
  sent: string[] = []
  onopen: (() => void) | null = null
  onmessage: ((event: { data: string }) => void) | null = null
  onerror: (() => void) | null = null
  onclose: (() => void) | null = null

  constructor(public readonly url: string) {
    FakeWebSocket.instances.push(this)
  }

  open(): void {
    this.readyState = FakeWebSocket.OPEN
    this.onopen?.()
  }

  send(value: string): void {
    this.sent.push(value)
  }

  close(): void {
    this.readyState = FakeWebSocket.CLOSED
    this.onclose?.()
  }

  emitMessage(value: object): void {
    this.onmessage?.({ data: JSON.stringify(value) })
  }
}

describe('AgentWebSocketService reconnect lifecycle', () => {
  beforeEach(() => {
    FakeWebSocket.instances = []
    vi.useFakeTimers()
    vi.stubGlobal('WebSocket', FakeWebSocket)
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
  })

  it('preserves handlers and reports accurate state after reconnect', async () => {
    const service = new AgentWebSocketService('ws://example.test/ws')
    const states: ConnectionState[] = []
    const messages: string[] = []
    service.addConnectionHandler((state) => states.push(state))
    service.addHandler((message) => messages.push(message.type))

    const connecting = service.connect()
    expect(FakeWebSocket.instances).toHaveLength(1)
    FakeWebSocket.instances[0].open()
    await connecting
    expect(service.isConnected).toBe(true)

    service.sendQuery('Get PROJ-1002', 'request-123')
    expect(JSON.parse(FakeWebSocket.instances[0].sent[0])).toEqual({
      type: 'query',
      payload: {
        query: 'Get PROJ-1002',
        request_id: 'request-123',
      },
    })

    FakeWebSocket.instances[0].close()
    expect(states).toContain('reconnecting')
    await vi.advanceTimersByTimeAsync(1000)
    expect(FakeWebSocket.instances).toHaveLength(2)
    FakeWebSocket.instances[1].open()
    FakeWebSocket.instances[1].emitMessage({
      type: 'response',
      payload: { request_id: 'request-123' },
    })

    expect(states[states.length - 1]).toBe('connected')
    expect(messages).toEqual(['response'])
    service.disconnect()
  })

  it('does not reconnect after an intentional disconnect', async () => {
    const service = new AgentWebSocketService('ws://example.test/ws')
    const connecting = service.connect()
    FakeWebSocket.instances[0].open()
    await connecting

    service.disconnect()
    await vi.advanceTimersByTimeAsync(10_000)

    expect(FakeWebSocket.instances).toHaveLength(1)
    expect(service.isConnected).toBe(false)
  })

  it('opens a fresh connection after disconnecting during startup', async () => {
    const service = new AgentWebSocketService('ws://example.test/ws')

    const firstConnection = service.connect()
    expect(FakeWebSocket.instances).toHaveLength(1)
    const staleCloseHandler = FakeWebSocket.instances[0].onclose
    FakeWebSocket.instances[0].onclose = null
    service.disconnect()

    const secondConnection = service.connect()
    expect(FakeWebSocket.instances).toHaveLength(2)
    const firstRejection = expect(firstConnection).rejects.toThrow('Unable to connect')
    staleCloseHandler?.()
    FakeWebSocket.instances[1].open()

    await firstRejection
    await expect(secondConnection).resolves.toBeUndefined()
    expect(service.isConnected).toBe(true)
    await vi.advanceTimersByTimeAsync(1000)
    expect(FakeWebSocket.instances).toHaveLength(2)
    service.disconnect()
  })
})
