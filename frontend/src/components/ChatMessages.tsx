import { useEffect, useRef } from 'react'
import { useChatStore } from '../store/chatStore'
import { AgentResponseRenderer } from './AgentResponseRenderer'

function formatRelativeTime(timestamp: Date): string {
  const elapsedSeconds = Math.max(0, Math.floor((Date.now() - timestamp.getTime()) / 1000))
  if (elapsedSeconds < 5) return 'just now'
  if (elapsedSeconds < 60) return `${elapsedSeconds} seconds ago`
  const elapsedMinutes = Math.floor(elapsedSeconds / 60)
  if (elapsedMinutes < 60) return `${elapsedMinutes} minute${elapsedMinutes === 1 ? '' : 's'} ago`
  const elapsedHours = Math.floor(elapsedMinutes / 60)
  if (elapsedHours < 24) return `${elapsedHours} hour${elapsedHours === 1 ? '' : 's'} ago`
  return timestamp.toLocaleDateString()
}

const EXAMPLE_CARDS = [
  {
    icon: '🎫',
    title: 'Investigate a Ticket',
    desc: 'Understand facts, history, and next investigation steps',
    query: 'Help me understand PROJ-1002',
  },
  {
    icon: '🔍',
    title: 'Search Incidents',
    desc: 'Find operational incidents by platform and priority',
    query: 'Find critical Kafka incidents',
  },
  {
    icon: '📊',
    title: 'Find Redis Incidents',
    desc: 'Search production incidents for a specific platform',
    query: 'Find Redis incidents in production',
  },
  {
    icon: '🛠️',
    title: 'Historical Matches',
    desc: 'Find resolved incidents similar to a Jira ticket',
    query: 'Find similar incidents to PROJ-1002',
  },
]

export function ChatMessages() {
  const { messages, isThinking, addExampleQuery } = useChatStore()
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isThinking])

  if (messages.length === 0) {
    return (
      <div className="messages-container">
        <div className="welcome-screen">
          <div className="welcome-icon">
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 2L2 7l10 5 10-5-10-5z" />
              <path d="M2 17l10 5 10-5" />
              <path d="M2 12l10 5 10-5" />
            </svg>
          </div>
          <div>
            <h1 className="welcome-title">Knowledge Agent</h1>
            <p className="welcome-subtitle">
              Your AI-powered interface to operational Jira knowledge, connected through the Model Context Protocol.
              Retrieve tickets, search incidents, and investigate historical resolutions.
            </p>
          </div>
          <div className="example-queries">
            {EXAMPLE_CARDS.map((card) => (
              <button
                key={card.query}
                className="example-query-card"
                onClick={() => addExampleQuery(card.query)}
              >
                <div className="icon">{card.icon}</div>
                <div className="title">{card.title}</div>
                <div className="desc">{card.desc}</div>
              </button>
            ))}
          </div>
        </div>
        <div ref={bottomRef} />
      </div>
    )
  }

  return (
    <div className="messages-container">
      {messages.map((msg) => {
        if (msg.role === 'user') {
          return (
            <div key={msg.id} className="message-group">
              <div className="message-user">
                <div className="bubble">{msg.content}</div>
              </div>
            </div>
          )
        }

        if (msg.status === 'thinking') {
          return (
            <div key={msg.id} className="message-group">
              <div className="message-agent">
                <div className="agent-avatar">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M12 2L2 7l10 5 10-5-10-5z" />
                    <path d="M2 17l10 5 10-5" />
                    <path d="M2 12l10 5 10-5" />
                  </svg>
                </div>
                <div className="thinking-bubble">
                  <div className="thinking-dots">
                    <div className="thinking-dot" />
                    <div className="thinking-dot" />
                    <div className="thinking-dot" />
                  </div>
                  <span className="thinking-text">Calling MCP tools…</span>
                </div>
              </div>
            </div>
          )
        }

        if (msg.status === 'error') {
          return (
            <div key={msg.id} className="message-group">
              <div className="message-agent">
                <div className="agent-avatar">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M12 2L2 7l10 5 10-5-10-5z" />
                    <path d="M2 17l10 5 10-5" />
                    <path d="M2 12l10 5 10-5" />
                  </svg>
                </div>
                <div className="content">
                  <div className="error-message">
                    <span>⚠️</span>
                    <span>{msg.content}</span>
                  </div>
                </div>
              </div>
            </div>
          )
        }

        // Successful agent response
        return (
          <div key={msg.id} className="message-group">
            <div className="message-agent">
              <div className="agent-avatar">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 2L2 7l10 5 10-5-10-5z" />
                  <path d="M2 17l10 5 10-5" />
                  <path d="M2 12l10 5 10-5" />
                </svg>
              </div>
              <div className="content" style={{ flex: 1, minWidth: 0 }}>
                {msg.response && <AgentResponseRenderer response={msg.response} />}
                <div style={{ fontSize: '0.65rem', color: 'var(--color-text-muted)', marginTop: '8px' }}>
                  {formatRelativeTime(msg.timestamp)}
                </div>
              </div>
            </div>
          </div>
        )
      })}
      <div ref={bottomRef} />
    </div>
  )
}
