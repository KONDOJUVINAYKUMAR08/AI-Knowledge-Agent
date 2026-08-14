import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'

import { ChatInput } from '../components/ChatInput'
import { ChatMessages } from '../components/ChatMessages'
import { useChatStore } from '../store/chatStore'

describe('operational Jira UI controls', () => {
  afterEach(() => {
    cleanup()
  })

  it('shows only supported operational examples and invokes their queries', () => {
    const addExampleQuery = vi.fn()
    useChatStore.setState({ messages: [], isThinking: false, addExampleQuery })

    render(<ChatMessages />)

    expect(screen.queryByText(/Confluence/i)).toBeNull()
    const expected = [
      ['Investigate a Ticket', 'Help me understand PROJ-1002'],
      ['Search Incidents', 'Find critical Kafka incidents'],
      ['Find Redis Incidents', 'Find Redis incidents in production'],
      ['Historical Matches', 'Find similar incidents to PROJ-1002'],
    ]
    expected.forEach(([label, query]) => {
      fireEvent.click(screen.getByRole('button', { name: new RegExp(label) }))
      expect(addExampleQuery).toHaveBeenCalledWith(query)
    })
  })

  it('submits a supported hint through the real input control', async () => {
    const sendMessage = vi.fn().mockResolvedValue(undefined)
    useChatStore.setState({ sendMessage })
    render(<ChatInput />)

    expect(screen.getByRole('textbox')).toHaveAttribute('maxLength', '2000')
    fireEvent.click(screen.getByRole('button', { name: 'Find critical Kafka incidents' }))
    expect((screen.getByRole('textbox') as HTMLTextAreaElement).value).toBe(
      'Find critical Kafka incidents',
    )
    fireEvent.click(screen.getByTitle('Send (Enter)'))

    expect(sendMessage).toHaveBeenCalledWith('Find critical Kafka incidents')
  })
})
