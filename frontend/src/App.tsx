import { useEffect } from 'react'
import { Sidebar } from './components/Sidebar'
import { ChatMessages } from './components/ChatMessages'
import { ChatInput } from './components/ChatInput'
import { useChatStore } from './store/chatStore'

export default function App() {
  const { initialize, isThinking, health } = useChatStore()

  useEffect(() => {
    initialize()
  }, [initialize])

  const isDisabled = isThinking

  return (
    <div className="app-layout">
      <Sidebar />
      <main className="main-area">
        {/* Header */}
        <div className="chat-header">
          <div>
            <div className="chat-title">AI Knowledge Agent</div>
            <div className="chat-subtitle">
              {health?.mcp_connected
                ? `${health.available_tools.length} tools available · Ask anything`
                : 'Connecting to MCP Server…'}
            </div>
          </div>
          <div className="header-actions">
            {health && (
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '4px 12px',
                  background: health.mcp_connected
                    ? 'rgba(16,185,129,0.1)'
                    : 'rgba(239,68,68,0.1)',
                  border: `1px solid ${health.mcp_connected ? 'rgba(16,185,129,0.2)' : 'rgba(239,68,68,0.2)'}`,
                  borderRadius: 'var(--radius-full)',
                  fontSize: 'var(--text-xs)',
                  color: health.mcp_connected ? 'var(--color-accent-green)' : 'var(--color-accent-red)',
                }}
              >
                <div
                  style={{
                    width: '6px',
                    height: '6px',
                    borderRadius: '50%',
                    background: health.mcp_connected
                      ? 'var(--color-accent-green)'
                      : 'var(--color-accent-red)',
                  }}
                />
                {health.mcp_connected ? 'MCP Connected' : 'MCP Disconnected'}
              </div>
            )}
          </div>
        </div>

        {/* Messages */}
        <ChatMessages />

        {/* Input */}
        <ChatInput disabled={isDisabled} />
      </main>
    </div>
  )
}
