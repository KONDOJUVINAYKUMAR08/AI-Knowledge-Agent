import { useState, useRef, useEffect, useCallback } from 'react'
import { useChatStore } from '../store/chatStore'

interface Props {
  disabled?: boolean
}

const EXAMPLE_QUERIES = [
  'Show me PROJ-1001',
  'Find critical bugs',
  'What time is it?',
  'Search in progress tickets',
  'Project overview',
  'List tools',
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
          placeholder="Ask about a Jira ticket, search issues, get project stats… (Enter to send)"
          rows={1}
          disabled={disabled}
        />
        <button
          className="send-button"
          onClick={handleSubmit}
          disabled={!value.trim() || disabled}
          title="Send (Enter)"
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
