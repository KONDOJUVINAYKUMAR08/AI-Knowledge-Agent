import { useChatStore } from '../store/chatStore'

export function Sidebar() {
  const { health, connectionState, clearMessages } = useChatStore()

  const getStatusInfo = () => {
    if (!health) return { label: 'Connecting…', className: 'loading' }
    if (health.status === 'healthy' && connectionState === 'connected') return { label: 'Connected', className: 'connected' }
    if (connectionState === 'reconnecting') return { label: 'Reconnecting…', className: 'loading' }
    if (health.status === 'healthy') return { label: 'Degraded', className: 'loading' }
    return { label: 'Disconnected', className: 'disconnected' }
  }

  const statusInfo = getStatusInfo()

  return (
    <aside className="sidebar">
      {/* Logo */}
      <div className="sidebar-header">
        <div className="logo">
          <div className="logo-icon">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 2L2 7l10 5 10-5-10-5z" />
              <path d="M2 17l10 5 10-5" />
              <path d="M2 12l10 5 10-5" />
            </svg>
          </div>
          <div>
            <div className="logo-text">Knowledge Agent</div>
            <div className="logo-subtext">Powered by MCP</div>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="sidebar-nav">
        <div className="nav-section-title">Navigation</div>
        <div className="nav-item active" style={{ cursor: 'default' }}>
          <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
          </svg>
          Chat
        </div>

        <div className="nav-section-title" style={{ marginTop: '16px' }}>Jira Capabilities</div>

        {health?.available_tools.map((tool) => (
          <div key={tool} className="nav-item" style={{ cursor: 'default' }}>
            <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />
            </svg>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.7rem' }}>
              {tool.replace(/_/g, ' ')}
            </span>
          </div>
        ))}

        {(!health?.available_tools || health.available_tools.length === 0) && (
          <div className="nav-item" style={{ cursor: 'default', opacity: 0.5 }}>
            <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            No Jira capabilities loaded
          </div>
        )}

        <div className="nav-section-title" style={{ marginTop: '16px' }}>Actions</div>
        <button className="nav-item" onClick={clearMessages}>
          <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="3 6 5 6 21 6" />
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2" />
          </svg>
          Clear Chat
        </button>
      </nav>

      {/* Footer */}
      <div className="sidebar-footer">
        <div className="status-badge">
          <div className={`status-dot ${statusInfo.className}`} />
          <span>MCP Server: {statusInfo.label}</span>
        </div>

        {health && (
          <div style={{ marginTop: '8px', fontSize: '0.65rem', color: 'var(--color-text-muted)' }}>
            v{health.version} · {health.available_tools.length} Jira tools · {health.llm.provider}/{health.llm.model}
          </div>
        )}
      </div>
    </aside>
  )
}
