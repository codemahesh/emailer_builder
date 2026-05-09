import React, { useEffect, useCallback } from 'react'
import { Button } from '../ui/Button'

// ── Types ─────────────────────────────────────────────────────────────────────

interface ConfirmModalProps {
  isOpen: boolean
  title: string
  message: string
  confirmLabel?: string
  cancelLabel?: string
  isDanger?: boolean
  onConfirm: () => void
  onCancel: () => void
}

// ── Main component ────────────────────────────────────────────────────────────

export function ConfirmModal({
  isOpen,
  title,
  message,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  isDanger = false,
  onConfirm,
  onCancel,
}: ConfirmModalProps) {
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onCancel()
      }
    },
    [onCancel],
  )

  useEffect(() => {
    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown)
    }
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [isOpen, handleKeyDown])

  if (!isOpen) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      role="dialog"
      aria-modal="true"
      aria-labelledby="confirm-modal-title"
    >
      {/* Scrim */}
      <div
        className="absolute inset-0 bg-black/40"
        onClick={onCancel}
        aria-hidden="true"
      />

      {/* Modal panel */}
      <div
        className={[
          'relative w-full max-w-[400px] mx-4 bg-neutral-0 rounded-lg shadow-elev-modal',
          'transition-all duration-[240ms] cubic-bezier(0.2,0.8,0.2,1)',
          isOpen ? 'opacity-100 scale-100' : 'opacity-0 scale-95',
        ].join(' ')}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 pt-6 pb-4">
          <h2
            id="confirm-modal-title"
            className="text-heading-2 text-neutral-800"
          >
            {title}
          </h2>
          <button
            type="button"
            onClick={onCancel}
            className="text-neutral-400 hover:text-neutral-600 transition-colors duration-[160ms] focus-visible:ring-2 focus-visible:ring-brand-primary rounded-sm"
            aria-label="Close dialog"
          >
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
              <path
                d="M15 5L5 15M5 5l10 10"
                stroke="currentColor"
                strokeWidth="1.75"
                strokeLinecap="round"
              />
            </svg>
          </button>
        </div>

        {/* Body */}
        <div className="px-6 pb-6">
          <p className="text-body text-neutral-600">{message}</p>
        </div>

        {/* Footer */}
        <div className="flex gap-3 justify-end px-6 pb-6">
          <Button variant="secondary" onClick={onCancel}>
            {cancelLabel}
          </Button>
          <Button
            variant={isDanger ? 'danger' : 'primary'}
            onClick={onConfirm}
          >
            {confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  )
}
