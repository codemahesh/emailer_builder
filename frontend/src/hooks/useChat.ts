import { useState, useCallback } from 'react'
import { api } from '../lib/api'

// ── Types ─────────────────────────────────────────────────────────────────────

export interface ChatCommand {
  action:
    | 'reorder_section'
    | 'swap_products'
    | 'apply_design_token'
    | 'replace_asset'
    | 'apply_theme_by_name'
    | 'apply_template_by_name'
    | 'vibe_shift'
  params: Record<string, unknown>
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  summary?: string
  commands?: ChatCommand[]
  diff_preview?: string
  locked_section_refusals?: string[]
  timestamp: Date
}

interface UseChat {
  messages: ChatMessage[]
  isLoading: boolean
  sendMessage: (text: string, lockedSectionIds: string[]) => Promise<void>
  clearHistory: () => void
}

// ── Hook ──────────────────────────────────────────────────────────────────────

let msgCounter = 0

function generateId(): string {
  return `msg-${++msgCounter}-${Date.now()}`
}

export function useChat(campaignId: string | undefined): UseChat {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isLoading, setIsLoading] = useState(false)

  const sendMessage = useCallback(
    async (text: string, lockedSectionIds: string[]) => {
      if (!campaignId || !text.trim()) return

      const userMsg: ChatMessage = {
        id: generateId(),
        role: 'user',
        content: text.trim(),
        timestamp: new Date(),
      }

      setMessages((prev) => [...prev, userMsg])
      setIsLoading(true)

      try {
        const response = await api.post<{
          content: string
          summary?: string
          commands?: ChatCommand[]
          diff_preview?: string
          locked_section_refusals?: string[]
        }>(`/campaigns/${campaignId}/chat`, {
          message: text.trim(),
          locked_section_ids: lockedSectionIds,
        })

        const assistantMsg: ChatMessage = {
          id: generateId(),
          role: 'assistant',
          content: response.data.content,
          summary: response.data.summary,
          commands: response.data.commands,
          diff_preview: response.data.diff_preview,
          locked_section_refusals: response.data.locked_section_refusals,
          timestamp: new Date(),
        }

        setMessages((prev) => [...prev, assistantMsg])
      } catch {
        const errorMsg: ChatMessage = {
          id: generateId(),
          role: 'assistant',
          content: 'Sorry, something went wrong. Please try again.',
          timestamp: new Date(),
        }
        setMessages((prev) => [...prev, errorMsg])
      } finally {
        setIsLoading(false)
      }
    },
    [campaignId],
  )

  const clearHistory = useCallback(() => {
    setMessages([])
  }, [])

  return { messages, isLoading, sendMessage, clearHistory }
}
