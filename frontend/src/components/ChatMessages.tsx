import { useEffect, useRef } from 'react'
import { useChatStore } from '../store/chatStore'
import { AgentResponseRenderer } from './AgentResponseRenderer'
import { formatDistanceToNow } from 'date-fns'

const EXAMPLE_CARDS = [
  {
    icon: '🎫',
    title: 'Fetch a Ticket',
    desc: 'Get full details for a Jira ticket',
    query: 'Show me PROJ-1001',
  },
  {
    icon: '🔍',
    title: 'Search Issues',
    desc: 'Find tickets by status, priority, or keyword',
    query: 'Find all critical bugs',
  },
  {
    icon: '📊',
    title: 'Project Overview',
    desc: 'Get team stats and project summary',
    query: 'Show project overview',
  },
  {
    icon: '🛠️',
    title: 'List Tools',
    desc: 'See all available MCP tools',
    query: 'What tools are available?',
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
              Your AI-powered interface to Jira and Confluence, connected via the Model Context Protocol.
              Ask questions naturally — the agent handles the rest.
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
                  {formatDistanceToNow(msg.timestamp, { addSuffix: true })}
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
