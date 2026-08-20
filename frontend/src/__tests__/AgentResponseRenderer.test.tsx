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
      error_code: 'test_error',
      error: 'Test error message',
      structured_response: null,
      timestamp: '2026-08-12T12:00:00Z',
      processing_ms: 100,
      request_id: 'request-1'
    }

    render(<AgentResponseRenderer response={errorResponse} />)
    expect(screen.getByText('Test error message')).toBeDefined()
  })

  it('renders missing structured_response gracefully', () => {
    const missingResponse: AgentQueryResponse = {
      success: true,
      error_code: null,
      error: null,
      structured_response: null,
      timestamp: '2026-08-12T12:00:00Z',
      processing_ms: 100,
      request_id: 'request-2'
    }

    render(<AgentResponseRenderer response={missingResponse} />)
    expect(screen.getByText('No structured response was returned from the agent.')).toBeDefined()
  })

  it('renders structured Jira evidence when AI generation is degraded', () => {
    const degradedResponse: AgentQueryResponse = {
      success: false,
      error_code: 'llm_invalid_response',
      error: 'AI-generated analysis did not pass response validation. Verified Jira evidence is shown below.',
      structured_response: {
        ticket_summary: 'Verified Jira ticket PROJ-1003',
        what_we_know: 'Verified AKS DNS incident facts',
        similar_historical_tickets: 'PROJ-904 is a retrieved historical incident.',
        previous_resolution: 'Restored the required network configuration.',
        recommended_investigation: 'Validate current DNS and network evidence.',
        missing_information: 'Current runtime telemetry was not supplied.',
        sources: ['PROJ-1003', 'PROJ-904']
      },
      timestamp: '2026-08-12T12:00:00Z',
      processing_ms: 100,
      request_id: 'request-degraded'
    }

    render(<AgentResponseRenderer response={degradedResponse} />)

    expect(screen.getByRole('alert')).toHaveTextContent('Verified Jira evidence is shown below.')
    expect(screen.getByText('Verified Jira ticket PROJ-1003')).toBeDefined()
    expect(screen.getByText('Verified AKS DNS incident facts')).toBeDefined()
    expect(screen.getByText('PROJ-1003')).toBeDefined()
    expect(screen.getByText('PROJ-904')).toBeDefined()
  })

  it('renders full structured response correctly', () => {
    const fullResponse: AgentQueryResponse = {
      success: true,
      error_code: null,
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
      processing_ms: 100,
      request_id: 'request-3'
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
    expect(screen.getByText('These are similar tickets')).toBeDefined()
    expect(screen.getByText('This was resolved')).toBeDefined()
    expect(screen.getByText('Investigate this')).toBeDefined()
    expect(screen.getByText('Missing this')).toBeDefined()
    
    // Check the seventh structured section: sources
    expect(screen.getByText('SOURCES:')).toBeDefined()
    expect(screen.getByText('PROJ-1002')).toBeDefined()
    expect(screen.getByText('PROJ-908')).toBeDefined()
  })

  it('omits missing_information section when empty', () => {
    const responseWithoutMissingInfo: AgentQueryResponse = {
      success: true,
      error_code: null,
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
      processing_ms: 100,
      request_id: 'request-4'
    }

    const { queryByText } = render(<AgentResponseRenderer response={responseWithoutMissingInfo} />)
    expect(queryByText('❓ Missing Information')).toBeNull()
    expect(queryByText('SOURCES:')).toBeNull()
  })
})
