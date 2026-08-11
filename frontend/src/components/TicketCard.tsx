import type { Ticket } from '../../types'
import { formatDistanceToNow } from 'date-fns'

interface Props {
  ticket: Ticket
}

function getStatusClass(category: string): string {
  const map: Record<string, string> = {
    indeterminate: 'in-progress',
    done: 'done',
    new: 'open',
  }
  return map[category] ?? 'open'
}

function getStatusDisplay(name: string): string {
  const map: Record<string, string> = {
    'In Progress': 'In Progress',
    'In Review': 'In Review',
    'Done': 'Done',
    'Open': 'Open',
    'Backlog': 'Backlog',
  }
  return map[name] ?? name
}

function UserAvatar({ name }: { name: string }) {
  const initials = name
    .split(' ')
    .map((n) => n[0])
    .join('')
    .slice(0, 2)
    .toUpperCase()
  return <div className="comment-avatar">{initials}</div>
}

export function TicketCard({ ticket }: Props) {
  return (
    <div className="result-card">
      <div className="result-card-header">
        <div className="result-card-title">
          <span>{ticket.issue_type.icon}</span>
          <span className="ticket-id-link">{ticket.key}</span>
          <span style={{ color: 'var(--color-text-muted)', fontSize: 'var(--text-xs)' }}>
            {ticket.project.name}
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div className={`status-pill ${getStatusClass(ticket.status.category)}`}>
            {getStatusDisplay(ticket.status.name)}
          </div>
          {ticket.sprint && (
            <span
              style={{
                fontSize: '0.65rem',
                color: 'var(--color-text-muted)',
                background: 'rgba(255,255,255,0.04)',
                padding: '2px 8px',
                borderRadius: 'var(--radius-full)',
                border: '1px solid var(--color-border)',
              }}
            >
              {ticket.sprint.name}
            </span>
          )}
        </div>
      </div>

      <div className="result-card-body">
        <div className="ticket-card">
          {/* Summary */}
          <div className="ticket-summary">{ticket.summary}</div>

          {/* Metadata Grid */}
          <div className="ticket-meta-grid">
            <div className="ticket-meta-item">
              <span className="ticket-meta-label">Priority</span>
              <span className="ticket-meta-value">
                <span>{ticket.priority.icon}</span>
                {ticket.priority.name}
              </span>
            </div>

            <div className="ticket-meta-item">
              <span className="ticket-meta-label">Assignee</span>
              <span className="ticket-meta-value">
                {ticket.assignee ? ticket.assignee.display_name : (
                  <span style={{ color: 'var(--color-text-muted)' }}>Unassigned</span>
                )}
              </span>
            </div>

            <div className="ticket-meta-item">
              <span className="ticket-meta-label">Reporter</span>
              <span className="ticket-meta-value">{ticket.reporter.display_name}</span>
            </div>

            {ticket.story_points !== null && (
              <div className="ticket-meta-item">
                <span className="ticket-meta-label">Story Points</span>
                <span className="ticket-meta-value">
                  <span
                    style={{
                      background: 'var(--color-brand-dim)',
                      color: 'var(--color-brand-primary)',
                      padding: '1px 8px',
                      borderRadius: 'var(--radius-full)',
                      fontWeight: 700,
                      fontSize: 'var(--text-xs)',
                    }}
                  >
                    {ticket.story_points}
                  </span>
                </span>
              </div>
            )}

            {ticket.due_date && (
              <div className="ticket-meta-item">
                <span className="ticket-meta-label">Due Date</span>
                <span className="ticket-meta-value">{ticket.due_date}</span>
              </div>
            )}

            <div className="ticket-meta-item">
              <span className="ticket-meta-label">Updated</span>
              <span className="ticket-meta-value">
                {formatDistanceToNow(new Date(ticket.updated), { addSuffix: true })}
              </span>
            </div>
          </div>

          {/* Labels */}
          {ticket.labels.length > 0 && (
            <div>
              <div className="ticket-meta-label" style={{ marginBottom: '6px' }}>Labels</div>
              <div className="tags-list">
                {ticket.labels.map((label) => (
                  <span key={label} className="tag">{label}</span>
                ))}
              </div>
            </div>
          )}

          {/* Components */}
          {ticket.components.length > 0 && (
            <div>
              <div className="ticket-meta-label" style={{ marginBottom: '6px' }}>Components</div>
              <div className="tags-list">
                {ticket.components.map((c) => (
                  <span
                    key={c}
                    className="tag"
                    style={{ color: 'var(--color-accent-cyan)', borderColor: 'rgba(6,182,212,0.2)' }}
                  >
                    {c}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Description */}
          {ticket.description && (
            <div>
              <div className="ticket-meta-label" style={{ marginBottom: '6px' }}>Description</div>
              <div className="ticket-description">{ticket.description}</div>
            </div>
          )}

          {/* Linked Issues */}
          {ticket.linked_issues.length > 0 && (
            <div>
              <div className="ticket-meta-label" style={{ marginBottom: '6px' }}>Linked Issues</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                {ticket.linked_issues.map((li, i) => (
                  <div
                    key={i}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px',
                      fontSize: 'var(--text-xs)',
                      color: 'var(--color-text-secondary)',
                    }}
                  >
                    <span
                      style={{
                        background: 'rgba(255,255,255,0.05)',
                        border: '1px solid var(--color-border)',
                        borderRadius: '4px',
                        padding: '1px 6px',
                        color: 'var(--color-text-muted)',
                        textTransform: 'capitalize',
                      }}
                    >
                      {li.type}
                    </span>
                    <span
                      style={{ fontFamily: 'var(--font-mono)', color: 'var(--color-brand-primary)' }}
                    >
                      {li.key}
                    </span>
                    <span>{li.summary}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Comments */}
          {ticket.comments.length > 0 && (
            <div>
              <div className="ticket-meta-label" style={{ marginBottom: '8px' }}>
                Comments ({ticket.comments.length})
              </div>
              {ticket.comments.map((comment, i) => (
                <div key={i} className="comment">
                  <UserAvatar name={comment.author.display_name} />
                  <div className="comment-content">
                    <div>
                      <span className="comment-author">{comment.author.display_name}</span>
                      <span className="comment-time">
                        {formatDistanceToNow(new Date(comment.created), { addSuffix: true })}
                      </span>
                    </div>
                    <div className="comment-body">{comment.body}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
