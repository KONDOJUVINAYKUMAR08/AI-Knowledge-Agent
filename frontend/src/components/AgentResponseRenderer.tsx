import type { AgentQueryResponse, Ticket } from '../../types'
import { TicketCard } from './TicketCard'

interface Props {
  response: AgentQueryResponse
}

const INTENT_LABELS: Record<string, string> = {
  greeting: '👋 Greeting',
  get_ticket: '🎫 Ticket Lookup',
  search_tickets: '🔍 Search',
  get_project: '📊 Project',
  get_time: '🕐 Time',
  list_tools: '🛠️ Tools',
  unknown: '❓ Unknown',
}

export function AgentResponseRenderer({ response }: Props) {
  if (!response.success) {
    return (
      <div className="error-message">
        <span>⚠️</span>
        <span>{response.error ?? 'An unexpected error occurred.'}</span>
      </div>
    )
  }

  const result = response.result as Record<string, unknown>

  return (
    <div>
      {/* Intent + Tool Trace */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap', marginBottom: '8px' }}>
        <span className={`intent-badge ${response.intent}`}>
          {INTENT_LABELS[response.intent] ?? response.intent}
        </span>
      </div>

      {response.tool_name && (
        <div className="tool-trace">
          <span style={{ color: 'var(--color-text-muted)' }}>→</span>
          <span className="tool-trace-name">{response.tool_name}</span>
          {Object.keys(response.tool_arguments).length > 0 && (
            <span className="tool-trace-args">
              ({JSON.stringify(response.tool_arguments)})
            </span>
          )}
          <span className="perf-badge">{response.processing_ms}ms</span>
        </div>
      )}

      {/* Render by intent */}
      {response.intent === 'get_ticket' && result?.ticket && (
        <TicketCard ticket={result.ticket as Ticket} />
      )}

      {response.intent === 'get_ticket' && result?.error && (
        <div className="result-card">
          <div className="result-card-body">
            <div className="error-message">
              <span>🔍</span>
              <div>
                <div style={{ fontWeight: 600, marginBottom: '4px' }}>{result.message as string}</div>
                {result.available_tickets && (
                  <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>
                    Available: {(result.available_tickets as string[]).join(', ')}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {response.intent === 'search_tickets' && (
        <div className="result-card">
          <div className="result-card-header">
            <div className="result-card-title">
              🔍 Search Results
              <span
                style={{
                  fontSize: 'var(--text-xs)',
                  color: 'var(--color-text-muted)',
                  fontWeight: 400,
                }}
              >
                {result?.total as number} ticket{(result?.total as number) !== 1 ? 's' : ''} found
              </span>
            </div>
          </div>
          <div className="result-card-body">
            {((result?.tickets as unknown[]) ?? []).length === 0 ? (
              <div style={{ color: 'var(--color-text-muted)', fontSize: 'var(--text-sm)', textAlign: 'center', padding: '24px' }}>
                No tickets match your search criteria.
              </div>
            ) : (
              <div className="search-results-list">
                {((result?.tickets as Record<string, unknown>[]) ?? []).map((ticket) => (
                  <div key={ticket.key as string} className="search-result-item">
                    <span className="search-result-key">{ticket.key as string}</span>
                    <span className="search-result-summary">{ticket.summary as string}</span>
                    <div className={`status-pill ${getStatusClass(ticket.status as string)}`} style={{ fontSize: '0.65rem', padding: '1px 8px' }}>
                      {ticket.status as string}
                    </div>
                    <span className="search-result-assignee">{ticket.assignee as string}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {response.intent === 'get_project' && result?.project && (
        <ProjectCard data={result as Record<string, unknown>} />
      )}

      {response.intent === 'get_time' && result?.timestamp && (
        <TimeCard data={result} />
      )}

      {response.intent === 'greeting' && result?.message && (
        <div
          style={{
            padding: '16px',
            background: 'var(--color-bg-elevated)',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius-xl)',
            fontSize: 'var(--text-sm)',
            color: 'var(--color-text-secondary)',
            lineHeight: 1.6,
          }}
        >
          <div style={{ fontSize: 'var(--text-base)', fontWeight: 600, color: 'var(--color-text-primary)', marginBottom: '4px' }}>
            {result.message as string}
          </div>
          {result.status && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: 'var(--text-xs)', color: 'var(--color-accent-green)' }}>
              <div className="status-dot connected" />
              Status: {result.status as string}
            </div>
          )}
        </div>
      )}

      {response.intent === 'list_tools' && result?.tools && (
        <div className="result-card">
          <div className="result-card-header">
            <div className="result-card-title">🛠️ Available Tools</div>
            <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>
              {result.count as number} registered
            </span>
          </div>
          <div className="result-card-body">
            <div className="tools-grid">
              {((result.tools as Record<string, unknown>[]) ?? []).map((tool) => (
                <div key={tool.name as string} className="tool-item">
                  <div className="tool-item-name">{tool.name as string}()</div>
                  <div className="tool-item-desc">{tool.description as string}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Fallback: raw JSON for unrecognized intents */}
      {['unknown'].includes(response.intent) && (
        <div className="result-card">
          <div className="result-card-body">
            <div style={{ color: 'var(--color-text-muted)', fontSize: 'var(--text-sm)', marginBottom: '8px' }}>
              I wasn't sure what you meant, so I called{' '}
              <code style={{ fontFamily: 'var(--font-mono)', color: 'var(--color-brand-primary)' }}>
                {response.tool_name}
              </code>{' '}
              as a fallback:
            </div>
            <pre className="raw-result">{JSON.stringify(response.result, null, 2)}</pre>
          </div>
        </div>
      )}
    </div>
  )
}

function getStatusClass(status: string): string {
  const map: Record<string, string> = {
    'In Progress': 'in-progress',
    'In Review': 'in-review',
    Done: 'done',
    Open: 'open',
    Backlog: 'backlog',
  }
  return map[status] ?? 'open'
}

function ProjectCard({ data }: { data: Record<string, unknown> }) {
  const project = data.project as Record<string, unknown>
  const stats = project?.stats as Record<string, number>
  const team = data.team as Record<string, unknown>[]

  return (
    <div className="result-card">
      <div className="result-card-header">
        <div className="result-card-title">
          📊 {project?.name as string}
          <span
            style={{
              fontFamily: 'var(--font-mono)',
              fontSize: 'var(--text-xs)',
              color: 'var(--color-text-muted)',
            }}
          >
            [{project?.key as string}]
          </span>
        </div>
      </div>
      <div className="result-card-body" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        <p style={{ fontSize: 'var(--text-sm)', color: 'var(--color-text-secondary)' }}>
          {project?.description as string}
        </p>

        {stats && (
          <div>
            <div className="ticket-meta-label" style={{ marginBottom: '10px' }}>Issue Statistics</div>
            <div className="stats-grid">
              <div className="stat-card">
                <div className="stat-value">{stats.total_issues}</div>
                <div className="stat-label">Total</div>
              </div>
              <div className="stat-card">
                <div className="stat-value" style={{ color: 'var(--color-accent-amber)' }}>
                  {stats.in_progress}
                </div>
                <div className="stat-label">In Progress</div>
              </div>
              <div className="stat-card">
                <div className="stat-value" style={{ color: 'var(--color-text-muted)' }}>
                  {stats.open}
                </div>
                <div className="stat-label">Open</div>
              </div>
              <div className="stat-card">
                <div className="stat-value" style={{ color: 'var(--color-accent-green)' }}>
                  {stats.done}
                </div>
                <div className="stat-label">Done</div>
              </div>
            </div>
          </div>
        )}

        {team && team.length > 0 && (
          <div>
            <div className="ticket-meta-label" style={{ marginBottom: '10px' }}>Team Members</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {team.map((member) => (
                <div
                  key={member.account_id as string}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '12px',
                    padding: '8px 12px',
                    background: 'var(--color-bg-input)',
                    border: '1px solid var(--color-border)',
                    borderRadius: 'var(--radius-md)',
                  }}
                >
                  <div
                    style={{
                      width: '32px',
                      height: '32px',
                      borderRadius: '50%',
                      background: 'linear-gradient(135deg, var(--color-brand-primary), var(--color-accent-purple))',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: '0.65rem',
                      fontWeight: 700,
                      color: 'white',
                      flexShrink: 0,
                    }}
                  >
                    {(member.display_name as string)
                      .split(' ')
                      .map((n: string) => n[0])
                      .join('')
                      .slice(0, 2)}
                  </div>
                  <div>
                    <div style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--color-text-primary)' }}>
                      {member.display_name as string}
                    </div>
                    <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>
                      {member.email as string}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function TimeCard({ data }: { data: Record<string, unknown> }) {
  return (
    <div className="result-card">
      <div className="result-card-body">
        <div style={{ textAlign: 'center', padding: '16px' }}>
          <div
            style={{
              fontSize: '2.5rem',
              fontWeight: 700,
              fontFamily: 'var(--font-mono)',
              color: 'var(--color-brand-primary)',
              letterSpacing: '-0.02em',
              marginBottom: '8px',
            }}
          >
            {new Date(data.timestamp as string).toLocaleTimeString()}
          </div>
          <div style={{ fontSize: 'var(--text-sm)', color: 'var(--color-text-secondary)' }}>
            {data.formatted as string}
          </div>
          <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', marginTop: '4px' }}>
            UTC · Unix: {data.unix_epoch as number}
          </div>
        </div>
      </div>
    </div>
  )
}
