import { useState, useRef, useEffect, useCallback } from 'react'
import { useChatStore } from '../store/chatStore'

interface Props {
  disabled?: boolean
}

const EXAMPLE_QUERIES = [
  'Help me understand PROJ-1002',
  'Get PROJ-1001',
  'Find critical Kafka incidents',
  'Find Redis incidents in production',
  'Find similar incidents to PROJ-1002',
  'What can you help me with?',
]

export function ChatInput({ disabled = false }: Props) {
  const [value, setValue] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const { sendMessage } = useChatStore()

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`
  }, [value])

  const handleSubmit = useCallback(async () => {
    const query = value.trim()
    if (!query || disabled) return
    setValue('')
    await sendMessage(query)
  }, [value, disabled, sendMessage])

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  const handleHintClick = (hint: string) => {
    setValue(hint)
    textareaRef.current?.focus()
  }

  return (
    <div className="input-area">
      <div className="input-wrapper">
        <textarea
          ref={textareaRef}
          className="query-input"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Investigate a Jira ticket or search operational incidents… (Enter to send)"
          aria-label="Operational Jira query"
          maxLength={2000}
          rows={1}
          disabled={disabled}
        />
        <button
          className="send-button"
          onClick={handleSubmit}
          disabled={!value.trim() || disabled}
          title="Send (Enter)"
          aria-label="Send query"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <line x1="22" y1="2" x2="11" y2="13" />
            <polygon points="22 2 15 22 11 13 2 9 22 2" />
          </svg>
        </button>
      </div>

      <div className="input-hints">
        <span style={{ fontSize: '0.65rem', color: 'var(--color-text-muted)', marginRight: '4px' }}>
          Try:
        </span>
        {EXAMPLE_QUERIES.map((hint) => (
          <button
            key={hint}
            className="hint-chip"
            onClick={() => handleHintClick(hint)}
            disabled={disabled}
          >
            {hint}
          </button>
        ))}
      </div>
    </div>
  )
}
