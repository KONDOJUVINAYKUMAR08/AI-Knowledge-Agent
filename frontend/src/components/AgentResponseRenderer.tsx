import ReactMarkdown from 'react-markdown'
import type { AgentQueryResponse } from '../types'

interface Props {
  response: AgentQueryResponse
}

export function AgentResponseRenderer({ response }: Props) {
  const { structured_response } = response

  if (!structured_response) {
    const message = !response.success
      ? response.error ?? 'An unexpected error occurred.'
      : 'No structured response was returned from the agent.'
    return (
      <div className="error-message">
        <span>⚠️</span>
        <span>{message}</span>
      </div>
    )
  }

  return (
    <div className="structured-response-container" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {!response.success && (
        <div className="error-message" role="alert">
          <span>⚠️</span>
          <span>{response.error ?? 'The request completed with limited results.'}</span>
        </div>
      )}
      
      {/* Summary Section */}
      <div className="result-card">
        <div className="result-card-header">
          <div className="result-card-title">📝 Ticket Summary</div>
          <span className="perf-badge">{response.processing_ms}ms</span>
        </div>
        <div className="result-card-body" style={{ color: 'var(--color-text-secondary)', lineHeight: 1.6 }}>
          <ReactMarkdown>{structured_response.ticket_summary}</ReactMarkdown>
        </div>
      </div>

      {/* What We Know */}
      <div className="result-card">
        <div className="result-card-header">
          <div className="result-card-title">🔍 What We Know</div>
        </div>
        <div className="result-card-body" style={{ color: 'var(--color-text-secondary)', lineHeight: 1.6 }}>
          <ReactMarkdown>{structured_response.what_we_know}</ReactMarkdown>
        </div>
      </div>

      {/* Similar Historical Tickets */}
      <div className="result-card">
        <div className="result-card-header">
          <div className="result-card-title">🕰️ Similar Historical Tickets</div>
        </div>
        <div className="result-card-body" style={{ color: 'var(--color-text-secondary)', lineHeight: 1.6 }}>
          <ReactMarkdown>{structured_response.similar_historical_tickets}</ReactMarkdown>
        </div>
      </div>

      {/* Previous Resolution */}
      <div className="result-card">
        <div className="result-card-header">
          <div className="result-card-title">✅ Previous Resolution</div>
        </div>
        <div className="result-card-body" style={{ color: 'var(--color-text-secondary)', lineHeight: 1.6 }}>
          <ReactMarkdown>{structured_response.previous_resolution}</ReactMarkdown>
        </div>
      </div>

      {/* Recommended Investigation */}
      <div className="result-card">
        <div className="result-card-header">
          <div className="result-card-title">🛠️ Recommended Investigation</div>
        </div>
        <div className="result-card-body" style={{ color: 'var(--color-text-secondary)', lineHeight: 1.6 }}>
          <ReactMarkdown>{structured_response.recommended_investigation}</ReactMarkdown>
        </div>
      </div>

      {/* Missing Information (Only show if present and not empty/N/A) */}
      {Boolean(structured_response.missing_information?.trim()) && (
        <div className="result-card">
          <div className="result-card-header">
            <div className="result-card-title">❓ Missing Information</div>
          </div>
          <div className="result-card-body" style={{ color: 'var(--color-text-secondary)', lineHeight: 1.6 }}>
            <ReactMarkdown>{structured_response.missing_information}</ReactMarkdown>
          </div>
        </div>
      )}

      {/* Sources */}
      {structured_response.sources && structured_response.sources.length > 0 && (
        <div style={{ marginTop: '8px' }}>
          <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-muted)' }}>SOURCES:</span>
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginTop: '4px' }}>
            {structured_response.sources.map((source: string, idx: number) => (
              <span key={idx} className="status-pill done" style={{ fontSize: '0.7rem', padding: '2px 8px' }}>
                {source}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
