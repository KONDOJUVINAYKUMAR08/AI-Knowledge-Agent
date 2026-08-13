import { afterEach, describe, expect, it, vi } from 'vitest'
import { AgentRestService } from '../services/agentService'
import type { AgentQueryResponse } from '../types'

const structuredResponse: AgentQueryResponse = {
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

describe('AgentRestService', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('posts a query to the same-origin API path and returns its response', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue(structuredResponse),
    })
    vi.stubGlobal('fetch', fetchMock)

    const service = new AgentRestService('/api')
    const result = await service.query('Help me understand PROJ-1002')

    expect(fetchMock).toHaveBeenCalledOnce()
    expect(fetchMock).toHaveBeenCalledWith('/api/query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: 'Help me understand PROJ-1002' }),
    })
    expect(result).toEqual(structuredResponse)
  })
})
