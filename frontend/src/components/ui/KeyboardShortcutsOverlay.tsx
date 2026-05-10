import React, { useEffect } from 'react'

// ── Types ─────────────────────────────────────────────────────────────────────

interface KeyboardShortcutsOverlayProps {
  isOpen: boolean
  onClose: () => void
}

interface ShortcutEntry {
  keys: string[]
  description: string
}

// ── Shortcut data ─────────────────────────────────────────────────────────────

const SHORTCUTS: ShortcutEntry[] = [
  { keys: ['⌘/Ctrl', 'K'], description: 'Focus chat input' },
  { keys: ['⌘/Ctrl', 'S'], description: 'Force snapshot' },
  { keys: ['⌘/Ctrl', 'E'], description: 'Open Export drawer' },
  { keys: ['⌘/Ctrl', '⇧', 'L'], description: 'Lock/unlock section' },
  { keys: ['D', 'M'], description: 'Toggle Desktop/Mobile viewport' },
  { keys: ['Esc'], description: 'Close drawer/modal' },
  { keys: ['↑', '↓'], description: 'Cycle chat history' },
  { keys: ['⇧', '/'], description: 'Open this overlay' },
]

// ── Key badge ─────────────────────────────────────────────────────────────────

function KeyBadge({ label }: { label: string }) {
  return (
    <kbd className="inline-flex items-center justify-center min-w-[26px] h-6 px-1.5 rounded border border-neutral-200 bg-neutral-50 text-neutral-700 text-caption font-mono shadow-[0_1px_0_0_theme(colors.neutral.200)]">
      {label}
    </kbd>
  )
}

// ── Component ─────────────────────────────────────────────────────────────────

export function KeyboardShortcutsOverlay({ isOpen, onClose }: KeyboardShortcutsOverlayProps) {
  // Close on Escape
  useEffect(() => {
    if (!isOpen) return
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.stopPropagation()
        onClose()
      }
    }
    document.addEventListener('keydown', handleKey)
    return () => document.removeEventListener('keydown', handleKey)
  }, [isOpen, onClose])

  // Trap body scroll when open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = ''
    }
    return () => {
      document.body.style.overflow = ''
    }
  }, [isOpen])

  if (!isOpen) return null

  const handleScrimClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) onClose()
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-neutral-900/70 backdrop-blur-[2px]"
      onClick={handleScrimClick}
      role="dialog"
      aria-modal="true"
      aria-labelledby="shortcuts-overlay-title"
    >
      <div
        className="relative w-full max-w-[480px] bg-neutral-0 rounded-lg shadow-elev-modal flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-neutral-100">
          <h2
            id="shortcuts-overlay-title"
            className="text-heading-3 text-neutral-900"
          >
            Keyboard Shortcuts
          </h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close keyboard shortcuts overlay"
            className="w-8 h-8 flex items-center justify-center rounded-md text-neutral-400 hover:text-neutral-800 hover:bg-neutral-100 transition-colors focus-visible:ring-2 focus-visible:ring-brand-primary focus-visible:ring-offset-1"
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 16 16"
              fill="none"
              aria-hidden="true"
            >
              <path
                d="M12 4L4 12M4 4L12 12"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
              />
            </svg>
          </button>
        </div>

        {/* Shortcut table */}
        <div className="px-6 py-5 flex-1 overflow-y-auto">
          <table className="w-full" role="grid" aria-label="Keyboard shortcuts list">
            <thead className="sr-only">
              <tr>
                <th scope="col">Keys</th>
                <th scope="col">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-100">
              {SHORTCUTS.map((shortcut, index) => (
                <tr key={index} className="flex items-center justify-between py-2.5 gap-4">
                  <td className="flex items-center gap-1 flex-shrink-0">
                    {shortcut.keys.map((key, ki) => (
                      <React.Fragment key={ki}>
                        {ki > 0 && <span className="text-neutral-300 text-caption mx-0.5">+</span>}
                        <KeyBadge label={key} />
                      </React.Fragment>
                    ))}
                  </td>
                  <td className="text-body text-neutral-600 text-right">
                    {shortcut.description}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-neutral-100 flex justify-end">
          <button
            type="button"
            onClick={onClose}
            className="h-9 px-4 rounded-md text-body-strong bg-neutral-0 text-neutral-800 border border-neutral-200 hover:bg-neutral-50 hover:border-neutral-400 transition-colors focus-visible:ring-2 focus-visible:ring-brand-primary focus-visible:ring-offset-1"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}
