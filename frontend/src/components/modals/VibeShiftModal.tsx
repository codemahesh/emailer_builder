import React, { useState, useEffect, useRef, useCallback } from 'react'
import { Button } from '../ui/Button'
import { showToast } from '../ui/Toast'
import { api } from '../../lib/api'

// ── Types ─────────────────────────────────────────────────────────────────────

interface VibeShiftPreview {
  will_regenerate: string[]
  will_preserve: {
    locked_sections: number
    manual_overrides: number
    pinned_theme: string | null
  }
  directive: string
}

interface VibeShiftModalProps {
  campaignId: string
  isOpen: boolean
  onClose: () => void
  onConfirm: () => void
}

// ── Helpers ───────────────────────────────────────────────────────────────────

const LAST_DIRECTIVE_KEY = 'vibe_shift_last_directive'

function SkeletonLine({ width = 'w-full' }: { width?: string }) {
  return (
    <div
      className={`h-4 rounded-sm bg-neutral-100 ${width}`}
      style={{
        backgroundImage:
          'linear-gradient(90deg, #EEF1F5 0%, #F8F9FB 50%, #EEF1F5 100%)',
        backgroundSize: '200% 100%',
      }}
    />
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export function VibeShiftModal({
  campaignId,
  isOpen,
  onClose,
  onConfirm,
}: VibeShiftModalProps) {
  const [directive, setDirective] = useState(
    () => localStorage.getItem(LAST_DIRECTIVE_KEY) ?? '',
  )
  const [preview, setPreview] = useState<VibeShiftPreview | null>(null)
  const [isPreviewLoading, setIsPreviewLoading] = useState(false)
  const [isConfirming, setIsConfirming] = useState(false)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const fetchPreview = useCallback(
    async (text: string) => {
      if (!text.trim()) {
        setPreview(null)
        return
      }
      setIsPreviewLoading(true)
      try {
        const response = await api.post<VibeShiftPreview>(
          `/campaigns/${campaignId}/vibe-shift`,
          { directive: text.trim() },
        )
        setPreview(response.data)
      } catch {
        setPreview(null)
      } finally {
        setIsPreviewLoading(false)
      }
    },
    [campaignId],
  )

  // Debounce preview fetch on directive change
  useEffect(() => {
    if (debounceRef.current !== null) {
      clearTimeout(debounceRef.current)
    }
    debounceRef.current = setTimeout(() => {
      fetchPreview(directive)
    }, 500)
    return () => {
      if (debounceRef.current !== null) {
        clearTimeout(debounceRef.current)
      }
    }
  }, [directive, fetchPreview])

  // Focus input on open
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 50)
    }
  }, [isOpen])

  // Esc to close
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown)
    }
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, onClose])

  const handleRegenerate = async () => {
    if (!directive.trim()) return
    setIsConfirming(true)
    localStorage.setItem(LAST_DIRECTIVE_KEY, directive)
    try {
      await api.post(`/campaigns/${campaignId}/vibe-shift/confirm`, {
        directive: directive.trim(),
      })
      onConfirm()
      onClose()
    } catch {
      showToast('Vibe Shift failed — please try again', 'error')
    } finally {
      setIsConfirming(false)
    }
  }

  if (!isOpen) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      role="dialog"
      aria-modal="true"
      aria-labelledby="vibe-shift-title"
    >
      {/* Scrim */}
      <div
        className="absolute inset-0 bg-black/40"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Modal panel */}
      <div
        className={[
          'relative w-full max-w-[480px] mx-4 bg-neutral-0 rounded-lg shadow-elev-modal',
          'transition-all duration-[240ms]',
          isOpen ? 'opacity-100 scale-100' : 'opacity-0 scale-95',
        ].join(' ')}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 pt-6 pb-4 border-b border-neutral-200">
          <div className="flex items-center gap-2">
            <span className="text-[#7B3FE4]" aria-hidden="true">✦</span>
            <h2 id="vibe-shift-title" className="text-heading-2 text-neutral-800">
              Vibe Shift
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-neutral-400 hover:text-neutral-600 transition-colors duration-[160ms] focus-visible:ring-2 focus-visible:ring-brand-primary rounded-sm"
            aria-label="Close Vibe Shift dialog"
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
        <div className="px-6 py-5 flex flex-col gap-5">
          {/* Directive input */}
          <div className="flex flex-col gap-1.5">
            <label
              htmlFor="vibe-directive"
              className="text-small-strong text-neutral-600"
            >
              Describe the vibe you want
            </label>
            <input
              ref={inputRef}
              id="vibe-directive"
              type="text"
              value={directive}
              onChange={(e) => setDirective(e.target.value)}
              placeholder="e.g. make it more urgent"
              className={[
                'w-full h-9 px-3 rounded-md border border-neutral-200 text-body text-neutral-800',
                'bg-neutral-0 placeholder:text-neutral-400',
                'focus:outline-none focus:border-brand-primary focus-visible:ring-2 focus-visible:ring-brand-primary',
                'transition-colors duration-[160ms]',
              ].join(' ')}
            />
          </div>

          {/* Preview area */}
          {(isPreviewLoading || preview) && (
            <div className="grid grid-cols-2 gap-4">
              {/* Will regenerate */}
              <div className="flex flex-col gap-2">
                <p className="text-small-strong text-neutral-600">Will regenerate</p>
                {isPreviewLoading ? (
                  <div className="flex flex-col gap-1.5">
                    <SkeletonLine width="w-full" />
                    <SkeletonLine width="w-3/4" />
                    <SkeletonLine width="w-2/3" />
                  </div>
                ) : preview ? (
                  <ul className="flex flex-col gap-1">
                    {preview.will_regenerate.map((item) => (
                      <li key={item} className="flex items-center gap-1.5 text-small text-neutral-600">
                        <span className="text-[#7B3FE4]" aria-hidden="true">✦</span>
                        {item}
                      </li>
                    ))}
                    {preview.will_regenerate.length === 0 && (
                      <li className="text-small text-neutral-400 italic">Nothing to regenerate</li>
                    )}
                  </ul>
                ) : null}
              </div>

              {/* Will preserve */}
              <div className="flex flex-col gap-2">
                <p className="text-small-strong text-neutral-600">Will preserve</p>
                {isPreviewLoading ? (
                  <div className="flex flex-col gap-1.5">
                    <SkeletonLine width="w-full" />
                    <SkeletonLine width="w-3/4" />
                    <SkeletonLine width="w-2/3" />
                  </div>
                ) : preview ? (
                  <ul className="flex flex-col gap-1">
                    <li className="flex items-center gap-1.5 text-small text-neutral-600">
                      <span aria-hidden="true">🔒</span>
                      {preview.will_preserve.locked_sections} locked section
                      {preview.will_preserve.locked_sections !== 1 ? 's' : ''}
                    </li>
                    <li className="flex items-center gap-1.5 text-small text-neutral-600">
                      <span aria-hidden="true">✋</span>
                      {preview.will_preserve.manual_overrides} manual override
                      {preview.will_preserve.manual_overrides !== 1 ? 's' : ''}
                    </li>
                    {preview.will_preserve.pinned_theme && (
                      <li className="flex items-center gap-1.5 text-small text-neutral-600">
                        <span aria-hidden="true">📌</span>
                        {preview.will_preserve.pinned_theme}
                      </li>
                    )}
                  </ul>
                ) : null}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex gap-3 justify-end px-6 pb-6">
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button
            variant="primary"
            disabled={!directive.trim() || isConfirming}
            isLoading={isConfirming}
            onClick={handleRegenerate}
          >
            Regenerate
          </Button>
        </div>
      </div>
    </div>
  )
}
