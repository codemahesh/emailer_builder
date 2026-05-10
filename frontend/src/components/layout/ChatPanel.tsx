import React, { useState, useRef, useEffect, useCallback } from 'react'
import { Button } from '../ui/Button'
import { showToast } from '../ui/Toast'
import { useChat, type ChatCommand, type ChatMessage } from '../../hooks/useChat'

// ── Types ─────────────────────────────────────────────────────────────────────

interface ChatPanelProps {
  campaignId: string
  lockedSectionIds: string[]
  onCommandApply: (commands: ChatCommand[]) => void
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatTime(date: Date): string {
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

const EXAMPLE_CHIPS = ['Reorder by priority', 'Make it more urgent', 'Replace hero with…']

// ── Sub-components ────────────────────────────────────────────────────────────

function ThinkingDots() {
  return (
    <div className="flex items-center gap-1 px-3 py-2" aria-label="AI is thinking">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="w-1.5 h-1.5 rounded-full bg-neutral-400 animate-bounce"
          style={{ animationDelay: `${i * 150}ms` }}
        />
      ))}
    </div>
  )
}

interface UserBubbleProps {
  message: ChatMessage
}

function UserBubble({ message }: UserBubbleProps) {
  return (
    <div className="flex justify-end gap-2">
      <div className="max-w-[80%] flex flex-col gap-1 items-end">
        <div className="bg-brand-primary-soft text-neutral-800 text-body rounded-lg rounded-tr-sm px-3 py-2">
          {message.content}
        </div>
        <span className="text-caption text-neutral-400">{formatTime(message.timestamp)}</span>
      </div>
    </div>
  )
}

interface AssistantBubbleProps {
  message: ChatMessage
  onApplyCommands: (commands: ChatCommand[]) => void
  onDiscardCommands: () => void
}

function AssistantBubble({ message, onApplyCommands, onDiscardCommands }: AssistantBubbleProps) {
  const hasProposal = Boolean(message.commands?.length)
  const hasLockedRefusals = Boolean(message.locked_section_refusals?.length)

  return (
    <div className="flex justify-start gap-2">
      <div className="max-w-[85%] flex flex-col gap-1.5">
        {/* AI header label */}
        <div className="flex items-center gap-1 text-caption text-[#7B3FE4] font-medium">
          <span aria-hidden="true">✦</span>
          <span>Builder</span>
        </div>

        {/* Main content bubble */}
        <div className="bg-neutral-0 border border-neutral-200 rounded-lg rounded-tl-sm px-3 py-2">
          <p className="text-body text-neutral-600 whitespace-pre-wrap">{message.content}</p>
        </div>

        {/* Locked section refusals */}
        {hasLockedRefusals && (
          <div className="bg-warn-50 border border-warn-600 rounded-md px-3 py-2 flex flex-col gap-1">
            <p className="text-small-strong text-warn-600">Cannot modify locked section</p>
            <ul className="flex flex-col gap-0.5">
              {message.locked_section_refusals!.map((sectionId) => (
                <li key={sectionId} className="text-small text-warn-600">
                  Section: {sectionId}
                </li>
              ))}
            </ul>
            <button
              type="button"
              className="text-small-strong text-warn-600 underline hover:no-underline text-left mt-1 focus-visible:ring-2 focus-visible:ring-brand-primary rounded-sm"
            >
              Unlock section to allow edits
            </button>
          </div>
        )}

        {/* Proposal card */}
        {hasProposal && (
          <div className="bg-brand-primary-soft border border-brand-primary rounded-md px-3 py-3 flex flex-col gap-2">
            {message.summary && (
              <p className="text-small-strong text-neutral-800">{message.summary}</p>
            )}
            {message.diff_preview && (
              <pre className="text-caption text-neutral-600 bg-neutral-0 rounded-sm p-2 overflow-x-auto whitespace-pre-wrap font-mono">
                {message.diff_preview}
              </pre>
            )}
            <div className="flex gap-2">
              <Button
                variant="primary"
                size="sm"
                onClick={() => onApplyCommands(message.commands!)}
              >
                Apply
              </Button>
              <Button
                variant="secondary"
                size="sm"
                onClick={onDiscardCommands}
              >
                Discard
              </Button>
            </div>
          </div>
        )}

        <span className="text-caption text-neutral-400">{formatTime(message.timestamp)}</span>
      </div>
    </div>
  )
}

// ── Attachment panel ──────────────────────────────────────────────────────────

interface AttachmentPanelProps {
  onAttach: (value: string) => void
  onClose: () => void
}

function AttachmentPanel({ onAttach, onClose }: AttachmentPanelProps) {
  const [urlValue, setUrlValue] = useState('')
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleUrlSubmit = () => {
    if (urlValue.trim()) {
      onAttach(urlValue.trim())
      onClose()
    }
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      const objectUrl = URL.createObjectURL(file)
      onAttach(objectUrl)
      onClose()
    }
  }

  return (
    <div className="border border-neutral-200 rounded-md p-3 bg-neutral-0 shadow-elev-raised flex flex-col gap-3">
      <p className="text-small-strong text-neutral-600">Attach image</p>
      <div className="flex gap-2">
        <input
          type="url"
          value={urlValue}
          onChange={(e) => setUrlValue(e.target.value)}
          placeholder="Paste image URL…"
          className="flex-1 h-8 px-2 rounded-sm border border-neutral-200 text-small text-neutral-800 placeholder:text-neutral-400 focus:outline-none focus:border-brand-primary focus-visible:ring-2 focus-visible:ring-brand-primary"
          onKeyDown={(e) => {
            if (e.key === 'Enter') handleUrlSubmit()
            if (e.key === 'Escape') onClose()
          }}
        />
        <Button variant="secondary" size="sm" onClick={handleUrlSubmit}>
          Add
        </Button>
      </div>
      <div className="flex items-center gap-2">
        <div className="flex-1 h-px bg-neutral-200" />
        <span className="text-caption text-neutral-400">or</span>
        <div className="flex-1 h-px bg-neutral-200" />
      </div>
      <button
        type="button"
        onClick={() => fileInputRef.current?.click()}
        className="text-small text-brand-primary hover:underline text-left focus-visible:ring-2 focus-visible:ring-brand-primary rounded-sm"
      >
        Upload from device
      </button>
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={handleFileChange}
        aria-label="Upload image file"
      />
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export function ChatPanel({
  campaignId,
  lockedSectionIds,
  onCommandApply,
}: ChatPanelProps) {
  const { messages, isLoading, sendMessage } = useChat(campaignId)
  const [input, setInput] = useState('')
  const [showAttachment, setShowAttachment] = useState(false)
  const [historyIndex, setHistoryIndex] = useState(-1)
  const [savedInput, setSavedInput] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  const userMessages = messages.filter((m) => m.role === 'user')
  const showExampleChips = userMessages.length < 5

  // Scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  // Auto-resize textarea
  useEffect(() => {
    const ta = textareaRef.current
    if (!ta) return
    ta.style.height = 'auto'
    ta.style.height = `${Math.min(ta.scrollHeight, 96)}px` // 4 lines max ~96px
  }, [input])

  const handleSend = useCallback(async () => {
    const text = input.trim()
    if (!text || isLoading) return
    setInput('')
    setHistoryIndex(-1)
    setSavedInput('')
    try {
      await sendMessage(text, lockedSectionIds)
    } catch {
      showToast('Failed to send message', 'error')
    }
  }, [input, isLoading, sendMessage, lockedSectionIds])

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
      return
    }

    // History navigation
    if (e.key === 'ArrowUp') {
      const userMsgs = messages.filter((m) => m.role === 'user')
      if (userMsgs.length === 0) return
      e.preventDefault()
      if (historyIndex === -1) {
        setSavedInput(input)
        setHistoryIndex(userMsgs.length - 1)
        setInput(userMsgs[userMsgs.length - 1].content)
      } else if (historyIndex > 0) {
        setHistoryIndex((i) => i - 1)
        setInput(userMsgs[historyIndex - 1].content)
      }
    }

    if (e.key === 'ArrowDown') {
      if (historyIndex === -1) return
      e.preventDefault()
      const userMsgs = messages.filter((m) => m.role === 'user')
      if (historyIndex === userMsgs.length - 1) {
        setHistoryIndex(-1)
        setInput(savedInput)
      } else {
        setHistoryIndex((i) => i + 1)
        setInput(userMsgs[historyIndex + 1].content)
      }
    }
  }

  const handleExampleChip = (chip: string) => {
    setInput(chip)
    textareaRef.current?.focus()
  }

  const handleAttach = (value: string) => {
    setInput((prev) => (prev ? `${prev} ${value}` : value))
    textareaRef.current?.focus()
  }

  return (
    <div className="flex flex-col h-full">
      {/* Panel header */}
      <div className="flex items-center gap-2 px-4 pt-4 pb-2 border-b border-neutral-200 flex-shrink-0">
        <span className="text-[#7B3FE4]" aria-hidden="true">✦</span>
        <span className="text-small-strong uppercase tracking-wider text-neutral-600">
          AI Chat
        </span>
      </div>

      {/* Messages list */}
      <div className="flex-1 overflow-y-auto px-4 py-3 flex flex-col gap-4">
        {messages.length === 0 && (
          <p className="text-small text-neutral-400 italic text-center mt-4">
            Ask the AI to help you refine this campaign.
          </p>
        )}

        {messages.map((msg) =>
          msg.role === 'user' ? (
            <UserBubble key={msg.id} message={msg} />
          ) : (
            <AssistantBubble
              key={msg.id}
              message={msg}
              onApplyCommands={(commands) => onCommandApply(commands)}
              onDiscardCommands={() => {
                /* discard — no-op for now, proposal just stays visible */
              }}
            />
          ),
        )}

        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-neutral-0 border border-neutral-200 rounded-lg rounded-tl-sm">
              <ThinkingDots />
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Example chips */}
      {showExampleChips && (
        <div className="px-4 pb-2 flex gap-2 flex-wrap flex-shrink-0">
          {EXAMPLE_CHIPS.map((chip) => (
            <button
              key={chip}
              type="button"
              onClick={() => handleExampleChip(chip)}
              className={[
                'text-caption text-neutral-600 bg-neutral-50 border border-neutral-200 rounded-full px-2.5 py-1',
                'hover:bg-brand-primary-soft hover:border-brand-primary hover:text-brand-primary',
                'transition-colors duration-[160ms]',
                'focus-visible:ring-2 focus-visible:ring-brand-primary',
              ].join(' ')}
            >
              {chip}
            </button>
          ))}
        </div>
      )}

      {/* Attachment panel */}
      {showAttachment && (
        <div className="px-4 pb-2 flex-shrink-0">
          <AttachmentPanel
            onAttach={handleAttach}
            onClose={() => setShowAttachment(false)}
          />
        </div>
      )}

      {/* Input area */}
      <div className="px-4 pb-4 flex-shrink-0 border-t border-neutral-200 pt-3">
        <div className="flex items-end gap-2 bg-neutral-0 border border-neutral-200 rounded-md px-3 py-2 focus-within:border-brand-primary transition-colors duration-[160ms]">
          {/* Attachment button */}
          <button
            type="button"
            onClick={() => setShowAttachment((v) => !v)}
            className={[
              'flex-shrink-0 text-neutral-400 hover:text-brand-primary transition-colors duration-[160ms]',
              'focus-visible:ring-2 focus-visible:ring-brand-primary rounded-sm',
              showAttachment ? 'text-brand-primary' : '',
            ].join(' ')}
            aria-label="Attach image"
            aria-pressed={showAttachment}
          >
            📎
          </button>

          {/* Textarea */}
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => {
              setInput(e.target.value)
              setHistoryIndex(-1)
            }}
            onKeyDown={handleKeyDown}
            placeholder="Ask the AI…"
            rows={1}
            className={[
              'flex-1 resize-none overflow-hidden text-body text-neutral-800',
              'placeholder:text-neutral-400 bg-transparent focus:outline-none',
              'max-h-24 min-h-[24px]',
            ].join(' ')}
            aria-label="Chat input"
          />

          {/* Send button */}
          <button
            type="button"
            onClick={handleSend}
            disabled={!input.trim() || isLoading}
            className={[
              'flex-shrink-0 w-7 h-7 rounded-md flex items-center justify-center',
              'transition-colors duration-[160ms]',
              'focus-visible:ring-2 focus-visible:ring-brand-primary',
              input.trim() && !isLoading
                ? 'bg-brand-primary text-neutral-0 hover:bg-brand-primary-hover'
                : 'bg-neutral-100 text-neutral-400 cursor-not-allowed',
            ].join(' ')}
            aria-label="Send message"
          >
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
              <path
                d="M1 7h12M7 1l6 6-6 6"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </button>
        </div>
        <p className="text-caption text-neutral-400 mt-1">
          Enter to send · Shift+Enter for new line
        </p>
      </div>
    </div>
  )
}
