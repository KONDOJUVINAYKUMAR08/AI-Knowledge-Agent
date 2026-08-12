import { describe, it, expect, afterEach } from 'vitest'
import { render, screen, cleanup } from '@testing-library/react'
import { AgentResponseRenderer } from '../components/AgentResponseRenderer'
import type { AgentQueryResponse } from '../types'

describe('AgentResponseRenderer', () => {
  afterEach(() => {
    cleanup()
  })
  it('renders error state correctly', () => {
    const errorResponse: AgentQueryResponse = {
      success: false,
      error: 'Test error message',
      structured_response: null,
      timestamp: '2026-08-12T12:00:00Z',
      processing_ms: 100
    }

    render(<AgentResponseRenderer response={errorResponse} />)
    expect(screen.getByText('Test error message')).toBeDefined()
  })

  it('renders missing structured_response gracefully', () => {
    const missingResponse: AgentQueryResponse = {
      success: true,
      error: null,
      structured_response: null,
      timestamp: '2026-08-12T12:00:00Z',
      processing_ms: 100
    }

    render(<AgentResponseRenderer response={missingResponse} />)
    expect(screen.getByText('No structured response was returned from the agent.')).toBeDefined()
  })

  it('renders full structured response correctly', () => {
    const fullResponse: AgentQueryResponse = {
      success: true,
      error: null,
      structured_response: {
        ticket_summary: 'This is the summary',
        what_we_know: 'This is what we know',
        similar_historical_tickets: 'These are similar tickets',
        previous_resolution: 'This was resolved',
        recommended_investigation: 'Investigate this',
        missing_information: 'Missing this',
        sources: ['PROJ-1002', 'PROJ-908']
      },
      timestamp: '2026-08-12T12:00:00Z',
      processing_ms: 100
    }

    render(<AgentResponseRenderer response={fullResponse} />)

    // Check headers
    expect(screen.getByText('📝 Ticket Summary')).toBeDefined()
    expect(screen.getByText('🔍 What We Know')).toBeDefined()
    expect(screen.getByText('🕰️ Similar Historical Tickets')).toBeDefined()
    expect(screen.getByText('✅ Previous Resolution')).toBeDefined()
    expect(screen.getByText('🛠️ Recommended Investigation')).toBeDefined()
    expect(screen.getByText('❓ Missing Information')).toBeDefined()

    // Check content (ReactMarkdown renders paragraphs)
    expect(screen.getByText('This is the summary')).toBeDefined()
    expect(screen.getByText('This is what we know')).toBeDefined()
    
    // Check sources
    expect(screen.getByText('PROJ-1002')).toBeDefined()
    expect(screen.getByText('PROJ-908')).toBeDefined()
  })

  it('omits missing_information section when empty', () => {
    const responseWithoutMissingInfo: AgentQueryResponse = {
      success: true,
      error: null,
      structured_response: {
        ticket_summary: 'This is the summary',
        what_we_know: 'This is what we know',
        similar_historical_tickets: 'These are similar tickets',
        previous_resolution: 'This was resolved',
        recommended_investigation: 'Investigate this',
        missing_information: '   ', // blank
        sources: []
      },
      timestamp: '2026-08-12T12:00:00Z',
      processing_ms: 100
    }

    const { queryByText } = render(<AgentResponseRenderer response={responseWithoutMissingInfo} />)
    expect(queryByText('❓ Missing Information')).toBeNull()
    expect(queryByText('SOURCES:')).toBeNull()
  })
})
